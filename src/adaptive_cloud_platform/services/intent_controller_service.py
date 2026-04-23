from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Optional, Tuple
import importlib.util
import shutil
import time

from adaptive_cloud_platform.state import IntegratedState


class IntentControllerService:
    """Component 3 context-aware intent translation and OpenFlow rule simulation."""

    INTENT_PATTERNS: Dict[str, Tuple[str, ...]] = {
        "security": (
            "block",
            "deny",
            "drop",
            "suspicious",
            "attack",
            "ddos",
            "malware",
            "quarantine",
            "threat",
            "blacklist",
        ),
        "load_balance": (
            "balance",
            "load",
            "distribute",
            "reroute",
            "allocate",
            "optimize",
            "resource",
            "server",
            "scale",
        ),
        "qos": (
            "prioritize",
            "priority",
            "qos",
            "video",
            "stream",
            "voice",
            "latency",
            "bandwidth",
            "queue",
        ),
        "monitor": (
            "monitor",
            "observe",
            "watch",
            "alert",
            "metric",
            "telemetry",
            "visualize",
            "inspect",
        ),
    }

    TYPE_ALIASES = {
        "block": "security",
        "deny": "security",
        "quarantine": "security",
        "rate_limit": "security",
        "load-balancing": "load_balance",
        "load_distribution": "load_balance",
        "resource_allocation": "load_balance",
        "traffic_engineering": "load_balance",
        "priority": "qos",
        "video_prioritization": "qos",
        "quality_of_service": "qos",
        "observe": "monitor",
    }

    LEVEL_SCORES = {
        "none": 0.0,
        "low": 0.2,
        "normal": 0.25,
        "medium": 0.55,
        "elevated": 0.65,
        "high": 0.85,
        "severe": 1.0,
        "critical": 1.0,
        "overloaded": 0.95,
    }

    def __init__(self, state: IntegratedState) -> None:
        self.state = state
        self.context_state: Dict[str, Any] = {
            "source": "component-3-default",
            "threat": "low",
            "congestion": "low",
            "load": "normal",
            "latency_ms": 35.0,
            "bandwidth_utilization": 0.25,
            "resource_utilization": 0.32,
            "time_context": "business_hours",
            "policy_context": "standard",
            "updated_at": time.time(),
        }
        self.intents: List[Dict[str, Any]] = []
        self.rules: List[Dict[str, Any]] = []
        self.context_updates: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.translation_latencies_ms: List[float] = []
        self.adaptation_latencies_ms: List[float] = []
        self.classification_samples = 0
        self.classification_correct = 0
        self._intent_sequence = 0
        self._rule_sequence = 0

    def submit_intent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        started_at = time.perf_counter()
        self._intent_sequence += 1
        raw_text = str(payload.get("intent") or payload.get("type") or "generic intent")
        requested_type = str(payload.get("type") or "generic").lower()
        intent_type, confidence, matched_terms = self.classify_intent(raw_text, requested_type)
        priority = self._clamp_int(payload.get("priority", 1), 1, 10)
        dfps = self.calculate_dfps(priority, self.context_state)
        intent_id = f"c3-intent-{self._intent_sequence:05d}"
        normalized = {
            "id": intent_id,
            "type": intent_type,
            "intent": raw_text,
            "priority": priority,
            "src_ip": payload.get("src_ip"),
            "dst_ip": payload.get("dst_ip"),
            "proto": self._normalize_proto(payload.get("proto")),
            "dst_port": payload.get("dst_port"),
            "metadata": {
                **(payload.get("metadata") or {}),
                "component": "component-3",
                "classification_confidence": confidence,
                "matched_terms": matched_terms,
                "dfps": dfps,
            },
            "context_score": self.context_score(self.context_state),
            "dfps": dfps,
            "source": payload.get("source", "component-3-intent-controller"),
            "ts": time.time(),
        }

        expected = payload.get("expected_type") or (payload.get("metadata") or {}).get("expected_type")
        if expected:
            self.classification_samples += 1
            expected_type = self.TYPE_ALIASES.get(str(expected).lower(), str(expected).lower())
            if expected_type == intent_type:
                self.classification_correct += 1

        rules = self._generate_rules(normalized, reason="intent_submission")
        latency_ms = (time.perf_counter() - started_at) * 1000.0
        normalized["translation_latency_ms"] = round(latency_ms, 3)
        self.translation_latencies_ms.append(latency_ms)
        self.translation_latencies_ms = self.translation_latencies_ms[-200:]
        self.intents.append(normalized)
        self.intents = self.intents[-200:]
        event = self._record_event("intent_translated", {"intent": normalized, "rules": rules})
        return {
            "accepted": True,
            "intent": normalized,
            "classification": {
                "type": intent_type,
                "confidence": confidence,
                "matched_terms": matched_terms,
                "method": "keyword_pattern_matching_with_type_aliases",
            },
            "rules": rules,
            "dfps": dfps,
            "benchmark": {
                "translation_latency_ms": round(latency_ms, 3),
                "rule_generation_time_ms": round(latency_ms, 3),
                "context_score": normalized["context_score"],
            },
            "event": event,
        }

    def update_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        started_at = time.perf_counter()
        normalized = self._normalize_context(payload)
        self.context_state.update(normalized)
        self.context_state["updated_at"] = time.time()
        adaptations: List[Dict[str, Any]] = []
        for intent in self.intents[-20:]:
            rules = self._generate_rules(intent, reason="context_reoptimization")
            adaptations.append({
                "intent_id": intent["id"],
                "intent_type": intent["type"],
                "rules": rules,
                "dfps": self.calculate_dfps(int(intent.get("priority", 1)), self.context_state),
            })
        latency_ms = (time.perf_counter() - started_at) * 1000.0
        self.adaptation_latencies_ms.append(latency_ms)
        self.adaptation_latencies_ms = self.adaptation_latencies_ms[-200:]
        update = {
            "context": dict(self.context_state),
            "adapted_intents": len(adaptations),
            "adapted_rules": sum(len(item["rules"]) for item in adaptations),
            "adaptations": adaptations[-12:],
            "adaptation_latency_ms": round(latency_ms, 3),
            "ts": time.time(),
        }
        self.context_updates.append(update)
        self.context_updates = self.context_updates[-100:]
        event = self._record_event("context_adapted", update)
        return {"accepted": True, **update, "event": event}

    def classify_intent(self, text: str, requested_type: str = "generic") -> Tuple[str, float, List[str]]:
        direct = self.TYPE_ALIASES.get(requested_type, requested_type)
        if direct in self.INTENT_PATTERNS:
            return direct, 0.92, [requested_type]

        lower_text = text.lower()
        scores: Dict[str, List[str]] = {}
        for intent_type, keywords in self.INTENT_PATTERNS.items():
            matches = [keyword for keyword in keywords if keyword in lower_text]
            if matches:
                scores[intent_type] = matches
        if not scores:
            return "generic", 0.48, []
        intent_type, matches = max(scores.items(), key=lambda item: (len(item[1]), len(" ".join(item[1]))))
        confidence = min(0.96, 0.58 + len(matches) * 0.1)
        return intent_type, round(confidence, 3), matches

    def calculate_dfps(self, priority: int, context: Optional[Dict[str, Any]] = None) -> float:
        ctx = context or self.context_state
        priority_score = max(0.0, min(1.0, float(priority) / 10.0))
        context_score = self.context_score(ctx)
        age_score = 1.0
        return round((0.5 * priority_score + 0.3 * context_score + 0.2 * age_score) * 100.0, 2)

    def context_score(self, context: Optional[Dict[str, Any]] = None) -> float:
        ctx = context or self.context_state
        threat = self._level_value(ctx.get("threat"), default=0.2)
        congestion = self._level_value(ctx.get("congestion"), default=0.2)
        load = self._level_value(ctx.get("load"), default=0.25)
        latency = min(1.0, max(0.0, float(ctx.get("latency_ms") or 0.0) / 250.0))
        bandwidth = self._ratio_value(ctx.get("bandwidth_utilization"))
        resource = self._ratio_value(ctx.get("resource_utilization"))
        policy = 0.75 if str(ctx.get("policy_context", "")).lower() in {"strict", "sla", "security"} else 0.3
        temporal = 0.7 if str(ctx.get("time_context", "")).lower() in {"peak_hours", "business_hours"} else 0.3
        score = (
            0.22 * threat
            + 0.24 * congestion
            + 0.18 * load
            + 0.12 * latency
            + 0.10 * bandwidth
            + 0.08 * resource
            + 0.03 * policy
            + 0.03 * temporal
        )
        return round(max(0.0, min(1.0, score)), 4)

    def status(self) -> Dict[str, Any]:
        return {
            "component": {
                "number": 3,
                "name": "Context-Aware Intent-Based Flow Programming Framework",
                "features": [
                    "natural-language and API-based intent submission",
                    "keyword/NLP-style intent classification and validation",
                    "DFPS priority scoring using priority and real-time context",
                    "OpenFlow-compatible rule generation for security, QoS, load balancing, and monitoring",
                    "continuous re-optimization when Component 2 context changes",
                    "team integration APIs for intent, context, hosts, rules, and metrics",
                ],
            },
            "context": dict(self.context_state),
            "metrics": {
                "intents_received": len(self.intents),
                "rules_generated": len(self.rules),
                "active_rules": len(self.active_rules()),
                "context_updates": len(self.context_updates),
                "avg_translation_latency_ms": round(mean(self.translation_latencies_ms), 3) if self.translation_latencies_ms else None,
                "avg_adaptation_latency_ms": round(mean(self.adaptation_latencies_ms), 3) if self.adaptation_latencies_ms else None,
                "classification_accuracy_percent": round((self.classification_correct / self.classification_samples) * 100.0, 2) if self.classification_samples else None,
                "context_score": self.context_score(self.context_state),
            },
            "latest_intent": self.intents[-1] if self.intents else None,
            "latest_rule": self.rules[-1] if self.rules else None,
            "latest_context_update": self.context_updates[-1] if self.context_updates else None,
            "recent_intents": self.intents[-20:],
            "recent_rules": self.rules[-30:],
            "events": self.events[-30:],
            "hosts": self.hosts(),
            "platform": self.platform_status(),
        }

    def rules_status(self) -> Dict[str, Any]:
        return {
            "rules": self.rules[-100:],
            "active_rules": self.active_rules(),
            "total_rules_generated": len(self.rules),
            "context": dict(self.context_state),
        }

    def active_rules(self) -> List[Dict[str, Any]]:
        latest_by_key: Dict[str, Dict[str, Any]] = {}
        for rule in self.rules:
            key = f"{rule.get('intent_id')}::{rule.get('semantic_action')}::{rule.get('switch')}"
            latest_by_key[key] = rule
        return list(latest_by_key.values())[-50:]

    def hosts(self) -> Dict[str, Any]:
        return {
            "total_hosts": len(self.state.hosts),
            "tiers": self._tier_counts(),
            "hosts": self.state.hosts,
        }

    def platform_status(self) -> Dict[str, Any]:
        return {
            "integrated_backend_mode": "fastapi_context_aware_intent_simulator",
            "real_openflow_push_from_integrated_api": False,
            "controller_support": {
                "ryu": importlib.util.find_spec("ryu") is not None,
                "mininet": importlib.util.find_spec("mininet") is not None,
                "networkx": importlib.util.find_spec("networkx") is not None,
                "sklearn": importlib.util.find_spec("sklearn") is not None,
            },
            "local_tools": {
                "ryu_manager": shutil.which("ryu-manager"),
                "mininet_mn": shutil.which("mn"),
                "ovs_vsctl": shutil.which("ovs-vsctl"),
                "openstack": shutil.which("openstack"),
            },
            "source_integrations": {
                "component_3_ryu_controller": "sources/SDN-main/adaptive_sdn/adaptive_sdn/controller/main_controller.py",
                "component_3_intent_engine": "sources/SDN-main/adaptive_sdn/adaptive_sdn/intent/intent_engine.py",
                "team_compat_intent_api": "/api/intent/submit",
                "team_compat_context_api": "/api/context/update",
                "team_compat_hosts_api": "/api/network/hosts",
            },
            "note": "The active Windows FastAPI runtime records OpenFlow-compatible rules. Run the preserved Ryu/Mininet source on Linux/Ubuntu to push real OFPFlowMod messages.",
        }

    def scenario(self, name: str) -> Dict[str, Any]:
        scenarios = {
            "video": {
                "intent_payload": {
                    "intent": "Prioritize video streaming during peak hours",
                    "priority": 8,
                    "src_ip": "10.0.0.1",
                    "dst_ip": "10.0.0.7",
                    "proto": "tcp",
                    "dst_port": 443,
                    "expected_type": "qos",
                },
                "context_payload": {
                    "threat": "low",
                    "congestion": "medium",
                    "load": "medium",
                    "latency_ms": 95,
                    "bandwidth_utilization": 0.62,
                    "resource_utilization": 0.58,
                    "time_context": "peak_hours",
                    "policy_context": "sla",
                },
            },
            "security": {
                "intent_payload": {
                    "intent": "Block suspicious traffic from 10.0.0.50",
                    "priority": 10,
                    "src_ip": "10.0.0.50",
                    "dst_ip": "10.0.0.12",
                    "proto": "tcp",
                    "dst_port": 22,
                    "expected_type": "security",
                },
                "context_payload": {
                    "threat": "high",
                    "congestion": "low",
                    "load": "normal",
                    "latency_ms": 44,
                    "bandwidth_utilization": 0.34,
                    "resource_utilization": 0.36,
                    "time_context": "business_hours",
                    "policy_context": "security",
                },
            },
            "load": {
                "intent_payload": {
                    "intent": "Balance traffic across available servers",
                    "priority": 7,
                    "src_ip": "10.0.0.3",
                    "dst_ip": "10.0.0.7",
                    "proto": "tcp",
                    "dst_port": 8000,
                    "expected_type": "load_balance",
                },
                "context_payload": {
                    "threat": "low",
                    "congestion": "high",
                    "load": "overloaded",
                    "latency_ms": 180,
                    "bandwidth_utilization": 0.88,
                    "resource_utilization": 0.82,
                    "time_context": "peak_hours",
                    "policy_context": "sla",
                },
            },
            "multi": {
                "intent_payload": {
                    "intent": "Prioritize video but block suspicious high rate sources and balance overloaded servers",
                    "priority": 9,
                    "src_ip": "10.0.0.2",
                    "dst_ip": "10.0.0.8",
                    "proto": "udp",
                    "dst_port": 5004,
                    "expected_type": "security",
                },
                "context_payload": {
                    "threat": "elevated",
                    "congestion": "high",
                    "load": "high",
                    "latency_ms": 145,
                    "bandwidth_utilization": 0.79,
                    "resource_utilization": 0.72,
                    "time_context": "peak_hours",
                    "policy_context": "strict",
                },
            },
        }
        selected = scenarios.get(name, scenarios["video"])
        preview_type, confidence, matched_terms = self.classify_intent(
            selected["intent_payload"]["intent"],
            str(selected["intent_payload"].get("type", "generic")),
        )
        preview_context = {**self.context_state, **selected["context_payload"]}
        return {
            "scenario": name,
            **selected,
            "preview": {
                "classification": {
                    "type": preview_type,
                    "confidence": confidence,
                    "matched_terms": matched_terms,
                },
                "context_score": self.context_score(preview_context),
                "dfps": self.calculate_dfps(int(selected["intent_payload"].get("priority", 1)), preview_context),
            },
        }

    def benchmark(self, scenario_name: str = "video", iterations: int = 10) -> Dict[str, Any]:
        iterations = self._clamp_int(iterations, 1, 100)
        scenario = self.scenario(scenario_name)
        before_intents = len(self.intents)
        before_rules = len(self.rules)
        latencies: List[float] = []
        for index in range(iterations):
            payload = dict(scenario["intent_payload"])
            payload["src_ip"] = payload.get("src_ip") or f"10.0.0.{(index % 3) + 1}"
            result = self.submit_intent(payload)
            latencies.append(float(result["benchmark"]["translation_latency_ms"]))
        return {
            "scenario": scenario_name,
            "iterations": iterations,
            "avg_translation_latency_ms": round(mean(latencies), 3) if latencies else 0.0,
            "min_translation_latency_ms": round(min(latencies), 3) if latencies else 0.0,
            "max_translation_latency_ms": round(max(latencies), 3) if latencies else 0.0,
            "intents_added": len(self.intents) - before_intents,
            "rules_added": len(self.rules) - before_rules,
            "classification_accuracy_percent": self.status()["metrics"]["classification_accuracy_percent"],
        }

    def _generate_rules(self, intent: Dict[str, Any], reason: str) -> List[Dict[str, Any]]:
        semantic_type = str(intent.get("type") or "generic")
        dfps = self.calculate_dfps(int(intent.get("priority", 1)), self.context_state)
        src_ip = intent.get("src_ip")
        dst_ip = intent.get("dst_ip")
        proto = self._normalize_proto(intent.get("proto"))
        dst_port = intent.get("dst_port")
        switch = self._target_switch(src_ip, dst_ip, semantic_type)
        context = dict(self.context_state)

        if semantic_type == "security":
            priority = 32000 + int(dfps)
            match = self._match(src_ip=src_ip, dst_ip=dst_ip, proto=proto, dst_port=dst_port)
            actions = [{"type": "DROP"}]
            semantic_action = "drop_suspicious_source"
        elif semantic_type == "qos":
            priority = 22000 + int(dfps)
            match = self._match(src_ip=src_ip, dst_ip=dst_ip, proto=proto, dst_port=dst_port or 443)
            actions = [
                {"type": "SET_QUEUE", "queue_id": 2},
                {"type": "SET_FIELD", "field": "ip_dscp", "value": 46},
                {"type": "OUTPUT", "port": "NORMAL"},
            ]
            semantic_action = "prioritize_latency_sensitive_flow"
        elif semantic_type == "load_balance":
            priority = 18000 + int(dfps)
            match = self._match(src_ip=src_ip, dst_ip=dst_ip, proto=proto, dst_port=dst_port or 8000)
            actions = [
                {"type": "GROUP", "group_id": "component_1_adaptive_backends"},
                {"type": "OUTPUT", "port": "NORMAL"},
            ]
            semantic_action = "balance_across_component_1_backends"
        elif semantic_type == "monitor":
            priority = 12000 + int(dfps)
            match = self._match(src_ip=src_ip, dst_ip=dst_ip, proto=proto, dst_port=dst_port)
            actions = [
                {"type": "COPY_TO_CONTROLLER", "max_len": 256},
                {"type": "OUTPUT", "port": "NORMAL"},
            ]
            semantic_action = "mirror_for_monitoring"
        else:
            priority = 9000 + int(dfps)
            match = self._match(src_ip=src_ip, dst_ip=dst_ip, proto=proto, dst_port=dst_port)
            actions = [{"type": "OUTPUT", "port": "NORMAL"}]
            semantic_action = "default_forward"

        rule = self._rule(
            intent_id=str(intent["id"]),
            intent_type=semantic_type,
            switch=switch,
            priority=priority,
            match=match,
            actions=actions,
            semantic_action=semantic_action,
            dfps=dfps,
            context=context,
            reason=reason,
        )
        self.rules.append(rule)
        self.rules = self.rules[-400:]
        return [rule]

    def _rule(
        self,
        intent_id: str,
        intent_type: str,
        switch: str,
        priority: int,
        match: Dict[str, Any],
        actions: List[Dict[str, Any]],
        semantic_action: str,
        dfps: float,
        context: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        self._rule_sequence += 1
        return {
            "id": f"c3-rule-{self._rule_sequence:05d}",
            "intent_id": intent_id,
            "intent_type": intent_type,
            "switch": switch,
            "table_id": 0,
            "priority": priority,
            "match": match,
            "actions": actions,
            "semantic_action": semantic_action,
            "dfps": dfps,
            "context_score": self.context_score(context),
            "context_snapshot": context,
            "idle_timeout_sec": 30,
            "hard_timeout_sec": 300,
            "openflow_compatible": True,
            "install_mode": "record_only_fastapi_runtime",
            "reason": reason,
            "generated_at": time.time(),
        }

    def _match(
        self,
        src_ip: Optional[str],
        dst_ip: Optional[str],
        proto: Optional[str],
        dst_port: Optional[int],
    ) -> Dict[str, Any]:
        match: Dict[str, Any] = {"eth_type": 0x0800}
        if src_ip:
            match["ipv4_src"] = src_ip
        if dst_ip:
            match["ipv4_dst"] = dst_ip
        if proto:
            match["ip_proto"] = 6 if proto == "tcp" else 17 if proto == "udp" else proto
        if dst_port and proto == "tcp":
            match["tcp_dst"] = int(dst_port)
        if dst_port and proto == "udp":
            match["udp_dst"] = int(dst_port)
        return match

    def _normalize_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {"source": payload.get("source", "component-3-context")}
        for key in ("threat", "congestion", "load", "time_context", "policy_context"):
            if payload.get(key) is not None:
                normalized[key] = str(payload[key]).lower()
        numeric_mappings = {
            "latency_ms": "latency_ms",
            "bandwidth_utilization": "bandwidth_utilization",
            "max_link_utilization_ratio": "bandwidth_utilization",
            "resource_utilization": "resource_utilization",
            "controller_cpu_percent": "resource_utilization",
        }
        for source_key, target_key in numeric_mappings.items():
            if payload.get(source_key) is None:
                continue
            value = float(payload[source_key])
            if source_key == "controller_cpu_percent":
                value = value / 100.0
            normalized[target_key] = max(0.0, min(1.0, value)) if target_key.endswith("utilization") else max(0.0, value)

        label = str(payload.get("label") or "").lower()
        recommendation = str(payload.get("recommendation") or "").lower()
        if label in {"ddos", "port_scan"} or recommendation in {"block_highest_risk_source", "rate_limit_scanner"}:
            normalized["threat"] = "high"
            normalized["policy_context"] = "security"
        if label == "congestion" or recommendation == "reroute_top_talker":
            normalized["congestion"] = normalized.get("congestion", "high")
            normalized["load"] = normalized.get("load", "high")
        return normalized

    def _target_switch(self, src_ip: Optional[str], dst_ip: Optional[str], intent_type: str) -> str:
        for ip in (dst_ip, src_ip):
            if ip and ip in self.state.hosts:
                return str(self.state.hosts[ip].get("switch", "s1"))
        if intent_type == "load_balance":
            return "s2"
        if intent_type == "security":
            return "s1"
        return "s3"

    def _tier_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for host in self.state.hosts.values():
            tier = str(host.get("tier", "unknown"))
            counts[tier] = counts.get(tier, 0) + 1
        return counts

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = {"type": event_type, "payload": payload, "ts": time.time()}
        self.events.append(event)
        self.events = self.events[-160:]
        return event

    def _normalize_proto(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).lower()
        if text in {"6", "tcp"}:
            return "tcp"
        if text in {"17", "udp"}:
            return "udp"
        return text

    def _level_value(self, value: Any, default: float) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return max(0.0, min(1.0, float(value)))
        return self.LEVEL_SCORES.get(str(value).lower(), default)

    def _ratio_value(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            return self._level_value(value, 0.0)
        return max(0.0, min(1.0, float(value)))

    def _clamp_int(self, value: Any, low: int, high: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = low
        return max(low, min(high, number))
