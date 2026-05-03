from __future__ import annotations

import os
import secrets
import time
from typing import Any, Dict, Optional


class OperatorAuthService:
    """Simple in-memory operator login for privileged console actions."""

    def __init__(self) -> None:
        self.username = os.environ.get("OPERATOR_USERNAME", "admin")
        self.password = os.environ.get("OPERATOR_PASSWORD", "admin123")
        self.session_ttl_sec = int(os.environ.get("OPERATOR_SESSION_TTL_SEC", "28800"))
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        if username != self.username or password != self.password:
            return {"authenticated": False, "error": "Invalid operator credentials"}
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

    def logout(self, token: Optional[str]) -> Dict[str, Any]:
        if token and token in self._sessions:
            self._sessions.pop(token, None)
            return {"logged_out": True}
        return {"logged_out": False}

    def status(self, token: Optional[str]) -> Dict[str, Any]:
        session = self.validate(token)
        if not session:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "username": session["username"],
            "expires_at": session["expires_at"],
            "token_type": "Bearer",
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

    def _cleanup(self) -> None:
        now = time.time()
        for token, session in list(self._sessions.items()):
            if float(session.get("expires_at") or 0.0) <= now:
                self._sessions.pop(token, None)
