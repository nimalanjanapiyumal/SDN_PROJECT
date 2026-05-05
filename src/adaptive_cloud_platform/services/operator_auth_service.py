from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from io import BytesIO
from typing import Any, Dict, Optional
from urllib.parse import quote

try:
    import qrcode
    import qrcode.image.svg
except Exception:  # pragma: no cover - graceful fallback if optional dep is unavailable
    qrcode = None


class OperatorAuthService:
    """Operator login with password + QR-backed TOTP verification."""

    def __init__(self) -> None:
        self.username = os.environ.get("OPERATOR_USERNAME", "admin")
        self.password = os.environ.get("OPERATOR_PASSWORD", "admin123")
        self.session_ttl_sec = int(os.environ.get("OPERATOR_SESSION_TTL_SEC", "28800"))
        self.pending_ttl_sec = int(os.environ.get("OPERATOR_OTP_CHALLENGE_TTL_SEC", "300"))
        self.otp_required = os.environ.get("OPERATOR_OTP_REQUIRED", "true").strip().lower() not in {"0", "false", "no"}
        self.otp_digits = int(os.environ.get("OPERATOR_OTP_DIGITS", "6"))
        self.otp_period_sec = int(os.environ.get("OPERATOR_OTP_PERIOD_SEC", "30"))
        self.otp_issuer = os.environ.get("OPERATOR_OTP_ISSUER", "Adaptive SDN Console")
        self.otp_secret = os.environ.get("OPERATOR_OTP_SECRET", self._generate_totp_secret())
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._pending_challenges: Dict[str, Dict[str, Any]] = {}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        if username != self.username or password != self.password:
            return {"authenticated": False, "error": "Invalid operator credentials"}
        self._cleanup()
        if not self.otp_required:
            return self._issue_session(username)

        challenge_id = secrets.token_urlsafe(16)
        issued_at = time.time()
        expires_at = issued_at + self.pending_ttl_sec
        challenge = {
            "challenge_id": challenge_id,
            "username": username,
            "issued_at": issued_at,
            "expires_at": expires_at,
        }
        self._pending_challenges[challenge_id] = challenge
        return {
            "authenticated": False,
            "credentials_verified": True,
            "otp_required": True,
            "challenge_id": challenge_id,
            "expires_at": expires_at,
            "issuer": self.otp_issuer,
            "account_name": username,
            "manual_entry_key": self._formatted_secret(),
            "otpauth_uri": self._otpauth_uri(username),
            "qr_code_data_uri": self._qr_code_data_uri(username),
            "token_type": "Bearer",
        }

    def verify_otp(self, challenge_id: str, otp_code: str) -> Dict[str, Any]:
        self._cleanup()
        challenge = self._pending_challenges.get(challenge_id)
        if not challenge:
            return {
                "authenticated": False,
                "otp_required": True,
                "error": "OTP challenge expired or not found",
            }
        normalized = "".join(ch for ch in str(otp_code or "") if ch.isdigit())
        if not normalized or not self._verify_totp(normalized):
            return {
                "authenticated": False,
                "otp_required": True,
                "error": "Invalid one-time password",
                "challenge_id": challenge_id,
                "expires_at": challenge["expires_at"],
            }

        username = str(challenge.get("username") or self.username)
        self._pending_challenges.pop(challenge_id, None)
        session = self._issue_session(username)
        session["otp_verified"] = True
        return session

    def logout(self, token: Optional[str]) -> Dict[str, Any]:
        if token and token in self._sessions:
            self._sessions.pop(token, None)
            return {"logged_out": True}
        return {"logged_out": False}

    def status(self, token: Optional[str]) -> Dict[str, Any]:
        session = self.validate(token)
        if not session:
            return {"authenticated": False, "otp_required": self.otp_required}
        return {
            "authenticated": True,
            "username": session["username"],
            "expires_at": session["expires_at"],
            "token_type": "Bearer",
            "otp_required": self.otp_required,
        }

    def validate(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        self._cleanup()
        session = self._sessions.get(token)
        if not session:
            return None
        if float(session.get("expires_at") or 0.0) <= time.time():
            self._sessions.pop(token, None)
            return None
        return session

    def require(self, token: Optional[str]) -> bool:
        return self.validate(token) is not None

    def current_otp_code_for_testing(self) -> str:
        return self._totp_at(time.time())

    def _issue_session(self, username: str) -> Dict[str, Any]:
        token = secrets.token_urlsafe(24)
        issued_at = time.time()
        expires_at = issued_at + self.session_ttl_sec
        session = {
            "username": username,
            "token": token,
            "issued_at": issued_at,
            "expires_at": expires_at,
        }
        self._sessions[token] = session
        self._cleanup()
        return {
            "authenticated": True,
            "token_type": "Bearer",
            "auth_header": f"Bearer {token}",
            "session_ttl_sec": self.session_ttl_sec,
            **session,
        }

    def _cleanup(self) -> None:
        now = time.time()
        for token, session in list(self._sessions.items()):
            if float(session.get("expires_at") or 0.0) <= now:
                self._sessions.pop(token, None)
        for challenge_id, challenge in list(self._pending_challenges.items()):
            if float(challenge.get("expires_at") or 0.0) <= now:
                self._pending_challenges.pop(challenge_id, None)

    def _generate_totp_secret(self) -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    def _formatted_secret(self) -> str:
        secret = self.otp_secret.replace(" ", "")
        return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))

    def _otpauth_uri(self, username: str) -> str:
        account = quote(username)
        issuer = quote(self.otp_issuer)
        return (
            f"otpauth://totp/{issuer}:{account}"
            f"?secret={self.otp_secret}&issuer={issuer}"
            f"&digits={self.otp_digits}&period={self.otp_period_sec}"
        )

    def _qr_code_data_uri(self, username: str) -> str:
        uri = self._otpauth_uri(username)
        if qrcode is None:
            return ""
        qr = qrcode.QRCode(border=1, box_size=8)
        qr.add_data(uri)
        qr.make(fit=True)
        image = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        buffer = BytesIO()
        image.save(buffer)
        payload = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{payload}"

    def _verify_totp(self, otp_code: str) -> bool:
        now = time.time()
        valid_codes = {
            self._totp_at(now - self.otp_period_sec),
            self._totp_at(now),
            self._totp_at(now + self.otp_period_sec),
        }
        return otp_code in valid_codes

    def _totp_at(self, ts: float) -> str:
        key = base64.b32decode(self.otp_secret.upper() + "=" * ((8 - len(self.otp_secret) % 8) % 8))
        counter = int(ts // self.otp_period_sec)
        payload = struct.pack(">Q", counter)
        digest = hmac.new(key, payload, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** self.otp_digits)
        return str(code_int).zfill(self.otp_digits)
