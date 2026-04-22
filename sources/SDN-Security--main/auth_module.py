#!/usr/bin/env python3
# auth_module.py
# Continuous Authentication: session monitoring + anomaly scoring
# Communicates with Ryu controller via REST to quarantine anomalous hosts

import time, json, threading, requests, logging, hashlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Optional
import jwt   # pip install pyjwt

logging.basicConfig(level=logging.INFO, format='%(asctime)s [AUTH] %(message)s')
logger = logging.getLogger("auth")

CONTROLLER_URL = "http://127.0.0.1:8080"
SECRET_KEY = "sdn_security_key_2025"   # In production: use environment variable
ANOMALY_THRESHOLD = 75               # Score 0-100; above this = suspicious
QUARANTINE_THRESHOLD = 90            # Score above this = quarantine

@dataclass
class SessionProfile:
    user_id: str
    ip_address: str
    token: str
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    request_times: deque = field(default_factory=lambda: deque(maxlen=50))
    request_rates: deque = field(default_factory=lambda: deque(maxlen=20))
    failed_attempts: int = 0
    bytes_sent: int = 0
    anomaly_score: float = 0.0
    status: str = "active"   # active | suspicious | quarantined

class ContinuousAuthEngine:
    def __init__(self):
        self.sessions: Dict[str, SessionProfile] = {}
        self.lock = threading.Lock()
        self._start_monitor()
        logger.info("Continuous Authentication Engine started")

    # ─── Session Management ────────────────────────────────────
    def create_session(self, user_id: str, ip: str, password: str) -> Optional[str]:
        "Authenticate user and create JWT session token"
        # Simulate password check (replace with real user store)
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        expected = hashlib.sha256(b"admin123").hexdigest()  # Demo only
        if pw_hash != expected:
            logger.warning(f"Failed login for {user_id} from {ip}")
            return None

        payload = {
            'sub': user_id, 'ip': ip,
            'iat': time.time(), 'exp': time.time() + 3600
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        with self.lock:
            self.sessions[token] = SessionProfile(
                user_id=user_id, ip_address=ip, token=token
            )
        logger.info(f"Session created: {user_id} from {ip}")
        return token

    def verify_request(self, token: str, ip: str,
                        bytes_sent: int = 0) -> dict:
        "Continuously verify each request — the core of continuous auth"
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return {'allowed': False, 'reason': 'token_expired'}
        except jwt.InvalidTokenError:
            return {'allowed': False, 'reason': 'invalid_token'}

        with self.lock:
            session = self.sessions.get(token)
            if not session:
                return {'allowed': False, 'reason': 'session_not_found'}

            # Check IP doesn't change mid-session (session hijack detection)
            if session.ip_address != ip:
                logger.warning(f"IP change detected for {session.user_id}: "
                               f"{session.ip_address} → {ip} (possible hijack)")
                session.anomaly_score = min(100, session.anomaly_score + 40)
                self._update_score(session)
                return {'allowed': False, 'reason': 'ip_mismatch'}

            # Update session activity
            now = time.time()
            session.last_seen = now
            session.request_times.append(now)
            session.bytes_sent += bytes_sent

            # Calculate anomaly score
            score = self._calculate_anomaly_score(session)
            session.anomaly_score = score

            self._update_score(session)

        result = {
            'allowed': session.status != 'quarantined',
            'user_id': payload['sub'],
            'anomaly_score': score,
            'status': session.status
        }
        return result

    def _calculate_anomaly_score(self, session: SessionProfile) -> float:
        "Multi-factor anomaly scoring (0-100)"
        score = 0.0
        now = time.time()

        # Factor 1: Request rate (last 10 seconds)
        recent = [t for t in session.request_times if now - t < 10]
        rate = len(recent)
        if rate > 30: score += 40
        elif rate > 15: score += 20
        elif rate > 8: score += 10

        # Factor 2: Session age (very long sessions are suspicious)
        age_hours = (now - session.created_at) / 3600
        if age_hours > 8: score += 15
        elif age_hours > 4: score += 5

        # Factor 3: Data exfiltration (bytes sent)
        mb_sent = session.bytes_sent / (1024 * 1024)
        if mb_sent > 100: score += 30
        elif mb_sent > 50: score += 15

        # Factor 4: Failed authentication attempts
        score += min(30, session.failed_attempts * 10)

        # Factor 5: Off-hours activity (22:00 - 06:00)
        hour = time.localtime(now).tm_hour
        if hour >= 22 or hour < 6:
            score += 10

        return min(100.0, score)

    def _update_score(self, session: SessionProfile):
        "Take action based on anomaly score"
        if session.anomaly_score >= QUARANTINE_THRESHOLD and session.status != 'quarantined':
            session.status = 'quarantined'
            logger.critical(f"QUARANTINE: {session.user_id} @ {session.ip_address} "
                           f"(score={session.anomaly_score:.1f})")
            # Tell Ryu controller to quarantine this IP
            self._notify_controller('quarantine', session.ip_address)
        elif session.anomaly_score >= ANOMALY_THRESHOLD and session.status == 'active':
            session.status = 'suspicious'
            logger.warning(f"SUSPICIOUS: {session.user_id} @ {session.ip_address} "
                          f"(score={session.anomaly_score:.1f})")

    def _notify_controller(self, action: str, ip: str):
        "Send command to Ryu controller via REST API"
        try:
            url = f"{CONTROLLER_URL}/sdn/{action}"
            requests.post(url, json={'ip': ip}, timeout=3)
            logger.info(f"Controller notified: {action} {ip}")
        except Exception as e:
            logger.error(f"Failed to notify controller: {e}")

    # ─── Background Monitor ────────────────────────────────────
    def _start_monitor(self):
        "Background thread: cleans expired sessions every 60s"
        def monitor():
            while True:
                time.sleep(60)
                now = time.time()
                with self.lock:
                    expired = [t for t, s in self.sessions.items()
                               if now - s.last_seen > 3600]
                    for t in expired:
                        logger.info(f"Session expired: {self.sessions[t].user_id}")
                        del self.sessions[t]
        threading.Thread(target=monitor, daemon=True).start()

    def get_all_sessions(self) -> list:
        with self.lock:
            return [{
                'user_id': s.user_id, 'ip': s.ip_address,
                'score': s.anomaly_score, 'status': s.status,
                'age_min': round((time.time() - s.created_at) / 60, 1)
            } for s in self.sessions.values()]


# ─── Flask REST Server for Auth Module ─────────────────────────
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
auth_engine = ContinuousAuthEngine()

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    token = auth_engine.create_session(
        data['user_id'], data['ip'], data.get('password', '')
    )
    if token:
        return jsonify({'token': token, 'status': 'authenticated'})
    return jsonify({'error': 'invalid credentials'}), 401

@app.route('/auth/verify', methods=['POST'])
def verify():
    data = request.get_json()
    result = auth_engine.verify_request(
        data['token'], data['ip'], data.get('bytes_sent', 0)
    )
    return jsonify(result)

@app.route('/auth/sessions', methods=['GET'])
def sessions():
    return jsonify(auth_engine.get_all_sessions())

if __name__ == '__main__':
    logger.info("Auth Module API starting on :5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
