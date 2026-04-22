from __future__ import annotations

from typing import Dict, Any, Optional
import time

from adaptive_cloud_platform.state import IntegratedState
from adaptive_cloud_platform.adapters.execution_adapter import ExecutionAdapter


class OrchestratorService:
    def __init__(self, state: IntegratedState, adapter: ExecutionAdapter) -> None:
        self.state = state
        self.adapter = adapter

    def record_intent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data['source'] = data.get('source', 'manual')
        data['ts'] = time.time()
        self.state.intents.append(data)
        return data

    def record_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data['ts'] = time.time()
        self.state.contexts.append(data)
        return data

    def record_resource_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data['ts'] = time.time()
        self.state.resource_plans.append(data)
        return data

    def record_security_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        data['ts'] = time.time()
        self.state.security_actions.append(data)
        return data

    def decide(self) -> Optional[Dict[str, Any]]:
        candidates: list[tuple[int, Dict[str, Any]]] = []
        if self.state.security_actions:
            sec = self.state.security_actions[-1]
            severity = int(sec.get('severity', 3) or 3)
            candidates.append((100 + severity, {
                'decision_type': sec.get('action', 'security'),
                'source': 'security',
                'payload': sec,
            }))
        if self.state.intents:
            intent = self.state.intents[-1]
            priority = int(intent.get('priority', 1) or 1)
            candidates.append((80 + priority, {
                'decision_type': intent.get('type', 'intent'),
                'source': 'manual',
                'payload': intent,
            }))
        if self.state.contexts:
            ctx = self.state.contexts[-1]
            recommendation = ctx.get('recommendation')
            confidence = float(ctx.get('confidence', 0.0) or 0.0)
            if recommendation:
                candidates.append((60 + int(confidence * 10), {
                    'decision_type': recommendation,
                    'source': 'ml',
                    'payload': ctx,
                }))
        if self.state.resource_plans:
            plan = self.state.resource_plans[-1]
            candidates.append((50, {
                'decision_type': 'apply_resource_plan',
                'source': 'optimizer',
                'payload': plan,
            }))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        decision = candidates[0][1]
        decision['score'] = candidates[0][0]
        decision['executed_at'] = time.time()
        decision['execution'] = self.adapter.apply(decision)
        self.state.decisions.append(decision)
        key = f"{decision['source']}::{decision['decision_type']}"
        self.state.active_policies[key] = decision
        return decision
