from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import time


@dataclass
class ExecutionAdapter:
    mode: str = 'record'

    def apply(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'applied': True,
            'mode': self.mode,
            'decision_type': decision.get('decision_type'),
            'timestamp': time.time(),
        }
