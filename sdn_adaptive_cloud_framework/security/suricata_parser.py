"""Parse Suricata eve.json alerts into controller intents (Module 7.4)."""
from __future__ import annotations

import json
from typing import Dict, Iterable, Iterator, List, Optional


def parse_eve_line(line: str) -> Optional[Dict]:
    line = line.strip()
    if not line:
        return None
    try:
        evt = json.loads(line)
    except json.JSONDecodeError:
        return None
    if evt.get("event_type") != "alert":
        return None
    return evt


def alert_to_intent(evt: Dict) -> Optional[Dict]:
    """Convert a Suricata alert event into a security/block intent."""
    src_ip = evt.get("src_ip")
    if not src_ip:
        return None
    alert = evt.get("alert", {})
    severity = alert.get("severity", 3)  # 1=highest in Suricata convention
    priority = 240 if severity == 1 else 200 if severity == 2 else 180
    return {
        "intent_type": "security",
        "action": "block",
        "src_ip": src_ip,
        "dst_ip": evt.get("dest_ip"),
        "priority": priority,
        "description": f"Suricata: {alert.get('signature', 'alert')} (sev={severity})",
    }


def stream_alerts(lines: Iterable[str]) -> Iterator[Dict]:
    for line in lines:
        evt = parse_eve_line(line)
        if evt is None:
            continue
        intent = alert_to_intent(evt)
        if intent is not None:
            yield intent


def parse_file(path: str) -> List[Dict]:
    with open(path, "r") as f:
        return list(stream_alerts(f))


__all__ = ["parse_eve_line", "alert_to_intent", "stream_alerts", "parse_file"]
