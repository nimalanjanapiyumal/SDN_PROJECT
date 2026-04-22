#!/usr/bin/env python3
# cti_module.py
# Dynamic Threat Intelligence: STIX/TAXII feeds → SDN flow rules
# Reads Suricata eve.json alerts and blocks IoCs in real-time

import json, time, logging, threading, requests, os
from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("cti")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [CTI] %(message)s')

CONTROLLER_URL  = "http://127.0.0.1:8080"
SURICATA_LOG    = "/var/log/suricata/eve.json"
ALERT_LOG       = "logs/cti_alerts.log"

@dataclass
class ThreatIndicator:
    ioc_type: str          # 'ip', 'domain', 'hash'
    value: str             # The actual IoC value
    threat_type: str       # DDoS, C2, Scanner, etc.
    severity: str          # low, medium, high, critical
    source: str = "suricata"
    blocked: bool = False
    first_seen: float = field(default_factory=time.time)
    hit_count: int = 0

class CTIEngine:
    def __init__(self):
        self.indicators: dict[str, ThreatIndicator] = {}
        self.blocked_ips: set = set()
        self.alert_stats = defaultdict(int)
        self.mitigation_latencies = []

        # Load static IoC list (simulate STIX/TAXII)
        self._load_static_iocs()

        # Start Suricata alert monitor
        self._start_suricata_monitor()
        logger.info("CTI Engine initialized")

    def _load_static_iocs(self):
        "Load known-bad IPs — in real deployment these come from TAXII server"
        known_iocs = [
            ("185.220.101.47", "C2 Server",     "critical"),
            ("91.108.4.1",    "DDoS Source",   "high"),
            ("45.155.205.4",  "Port Scanner",  "medium"),
            ("192.0.2.100",   "Malware Host",  "high"),
            ("10.10.10.88",   "Insider Threat","medium"),
        ]
        for ip, threat_type, severity in known_iocs:
            ioc = ThreatIndicator(
                ioc_type="ip", value=ip,
                threat_type=threat_type, severity=severity,
                source="static_feed"
            )
            self.indicators[ip] = ioc
        logger.info(f"Loaded {len(known_iocs)} static IoCs")

    def fetch_taxii_feed(self) -> dict:
        "Simulate TAXII 2.1 feed fetch (replace URL with real TAXII server)"
        # Real TAXII usage with taxii2-client library:
        # from taxii2client.v21 import Server
        # server = Server('https://cti.example.com/taxii/', ...
        # For demo: simulate with static data
        simulated_stix = {
            "type": "bundle",
            "id": "bundle--demo",
            "objects": [
                {"type": "indicator",
                 "pattern": "[ipv4-addr:value = '198.51.100.1']",
                 "name": "Malicious IP from TAXII"},
                {"type": "indicator",
                 "pattern": "[ipv4-addr:value = '203.0.113.5']",
                 "name": "Known DDoS botnet"},
            ]
        }
        new_iocs = []
        for obj in simulated_stix["objects"]:
            if obj.get("type") == "indicator":
                # Extract IP from STIX pattern
                pattern = obj.get("pattern", "")
                if "ipv4-addr:value" in pattern:
                    ip = pattern.split("'")[1]
                    ioc = ThreatIndicator(
                        ioc_type="ip", value=ip,
                        threat_type=obj.get("name", "Unknown"),
                        severity="high", source="taxii_feed"
                    )
                    self.indicators[ip] = ioc
                    new_iocs.append(ip)

        logger.info(f"TAXII fetch: {len(new_iocs)} new IoCs added")
        return {"new_iocs": len(new_iocs), "total": len(self.indicators)}

    def block_ioc(self, ip: str, reason: str = "") -> float:
        "Block an IoC and measure mitigation latency"
        start = time.time()
        try:
            r = requests.post(
                f"{CONTROLLER_URL}/sdn/block",
                json={'ip': ip, 'timeout': 3600},
                timeout=5
            )
            latency_ms = (time.time() - start) * 1000
            self.mitigation_latencies.append(latency_ms)
            self.blocked_ips.add(ip)

            if ip in self.indicators:
                self.indicators[ip].blocked = True

            logger.info(f"Blocked {ip} ({reason}) in {latency_ms:.1f}ms")
            self.alert_stats['blocked'] += 1
            return latency_ms
        except Exception as e:
            logger.error(f"Failed to block {ip}: {e}")
            return -1

    def _start_suricata_monitor(self):
        "Watch Suricata eve.json for alerts and auto-block IoCs"
        def monitor():
            if not os.path.exists(SURICATA_LOG):
                logger.warning(f"Suricata log not found: {SURICATA_LOG}")
                return

            logger.info(f"Monitoring Suricata alerts: {SURICATA_LOG}")
            with open(SURICATA_LOG, 'r') as f:
                f.seek(0, 2)    # Seek to end of file (tail -f behavior)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    try:
                        event = json.loads(line.strip())
                        if event.get('event_type') == 'alert':
                            self._handle_alert(event)
                    except: pass

        threading.Thread(target=monitor, daemon=True).start()

    def _handle_alert(self, event: dict):
        "Process Suricata alert → block if IoC or high severity"
        alert = event.get('alert', {})
        src_ip = event.get('src_ip', '')
        sig_msg = alert.get('signature', '')
        severity = alert.get('severity', 3)

        self.alert_stats['total'] += 1
        logger.info(f"Suricata alert: {sig_msg} from {src_ip}")

        # Auto-block known IoCs
        if src_ip in self.indicators and not self.indicators[src_ip].blocked:
            self.block_ioc(src_ip, reason="IoC match")
            return

        # Auto-block severity 1 (critical) alerts
        if severity == 1 and src_ip not in self.blocked_ips:
            self.block_ioc(src_ip, reason=sig_msg)

    def get_stats(self) -> dict:
        avg_latency = (sum(self.mitigation_latencies) / len(self.mitigation_latencies)
                       if self.mitigation_latencies else 0)
        return {
            'total_iocs': len(self.indicators),
            'blocked_ips': len(self.blocked_ips),
            'alert_stats': dict(self.alert_stats),
            'avg_latency_ms': round(avg_latency, 2),
            'indicators': [{
                'ip': v.value, 'type': v.threat_type,
                'severity': v.severity, 'blocked': v.blocked
            } for v in self.indicators.values()]
        }


# ─── Flask API ─────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
cti_engine = CTIEngine()

@app.route('/cti/stats',        methods=['GET'])
def stats():     return jsonify(cti_engine.get_stats())

@app.route('/cti/fetch',        methods=['POST'])
def fetch():     return jsonify(cti_engine.fetch_taxii_feed())

@app.route('/cti/block',        methods=['POST'])
def block():
    data = request.get_json()
    lat = cti_engine.block_ioc(data['ip'], data.get('reason', ''))
    return jsonify({'latency_ms': lat, 'ip': data['ip']})

if __name__ == '__main__':
    logger.info("CTI Module API starting on :5003")
    app.run(host='0.0.0.0', port=5003)
