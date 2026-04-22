from __future__ import annotations

from typing import Dict, Any


class SecurityService:
    def build_action(self, action: str, subject: str, reason: str | None = None, severity: int = 3) -> Dict[str, Any]:
        return {
            'source': 'security',
            'action': action,
            'subject': subject,
            'reason': reason or action,
            'severity': severity,
        }
