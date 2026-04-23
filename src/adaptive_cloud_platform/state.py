from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
import time


@dataclass
class IntegratedState:
    intents: List[Dict[str, Any]] = field(default_factory=list)
    contexts: List[Dict[str, Any]] = field(default_factory=list)
    resource_plans: List[Dict[str, Any]] = field(default_factory=list)
    security_actions: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    active_policies: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    hosts: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        '10.0.0.1': {'switch': 's4', 'tier': 'web', 'role': 'web-1'},
        '10.0.0.2': {'switch': 's4', 'tier': 'web', 'role': 'web-2'},
        '10.0.0.3': {'switch': 's4', 'tier': 'web', 'role': 'web-3'},
        '10.0.0.7': {'switch': 's5', 'tier': 'app', 'role': 'app-1'},
        '10.0.0.8': {'switch': 's5', 'tier': 'app', 'role': 'app-2'},
        '10.0.0.12': {'switch': 's6', 'tier': 'db', 'role': 'db-1'},
        '10.0.0.13': {'switch': 's6', 'tier': 'db', 'role': 'db-2'},
    })
    created_at: float = field(default_factory=time.time)

    def snapshot(self) -> Dict[str, Any]:
        return {
            'intents': self.intents[-20:],
            'contexts': self.contexts[-20:],
            'resource_plans': self.resource_plans[-10:],
            'security_actions': self.security_actions[-20:],
            'decisions': self.decisions[-20:],
            'active_policies': self.active_policies,
            'hosts': self.hosts,
            'created_at': self.created_at,
        }
