#!/usr/bin/env python3
# micro_seg.py
# Micro-segmentation: zone policies + dynamic OpenFlow ACL enforcement

import requests, logging, json, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("microseg")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [MICROSEG] %(message)s')

CONTROLLER_URL = "http://127.0.0.1:8080"
OVS_MANAGER   = "tcp:127.0.0.1:6640"  # OVS management port

@dataclass
class ZonePolicy:
    src_zone: str
    dst_zone: str
    allowed_ports: List[int]
    protocol: str = "tcp"
    priority: int = 200
    active: bool = True
    description: str = ""

class MicroSegmentationEngine:
    ZONES = {
        'web': '10.0.0.0/24',   # Zone A
        'app': '10.0.1.0/24',   # Zone B
        'db':  '10.0.2.0/24',    # Zone C
    }
    DATAPATH_IDS = {'s1': 1, 's2': 2, 's3': 3, 's4': 4}

    def __init__(self):
        self.policies: List[ZonePolicy] = []
        self.flow_rules_installed = []
        self._load_default_policies()
        logger.info("Micro-Segmentation Engine initialized")

    def _load_default_policies(self):
        "Default Zero-Trust policies — deny all, allow only what is needed"
        self.policies = [
            ZonePolicy('web', 'app', [80, 443, 8080, 8443],
                       description="Web → App: HTTP/HTTPS traffic"),
            ZonePolicy('app', 'web', [80, 443],
                       description="App → Web: responses"),
            ZonePolicy('app', 'db',  [3306, 5432, 6379, 27017],
                       description="App → DB: database protocols"),
            ZonePolicy('db',  'app', [3306, 5432, 6379],
                       description="DB → App: responses"),
            # Web → DB is NOT listed = BLOCKED (lateral movement prevention)
        ]
        logger.info(f"Loaded {len(self.policies)} default policies")

    def enforce_all_policies(self):
        "Push all policies to OVS switches via ovs-ofctl"
        import subprocess
        for switch_name, dpid in self.DATAPATH_IDS.items():
            # First: install default DROP for inter-zone traffic
            self._install_ovs_drop_rule(switch_name, 10.0/8)

        # Then: install ALLOW rules for permitted flows
        for policy in self.policies:
            if not policy.active:
                continue
            src_net = self.ZONES[policy.src_zone]
            dst_net = self.ZONES[policy.dst_zone]
            for port in policy.allowed_ports:
                self._install_ovs_allow_rule('s1', src_net, dst_net, port, policy.priority)
                rule_info = {
                    'src': src_net, 'dst': dst_net,
                    'port': port, 'action': 'ALLOW'
                }
                self.flow_rules_installed.append(rule_info)
                logger.info(f"Flow ALLOW: {src_net} → {dst_net}:{port}")

    def _install_ovs_allow_rule(self, switch, src_net, dst_net, port, priority=200):
        import subprocess
        cmd = [
            'sudo', 'ovs-ofctl', '-O', 'OpenFlow13', 'add-flow', switch,
            f'priority={priority},ip,nw_src={src_net},nw_dst={dst_net},'
            f'tp_dst={port},actions=normal'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ovs-ofctl error: {result.stderr}")

    def _install_ovs_drop_rule(self, switch, subnet):
        import subprocess
        # Block all cross-zone traffic at low priority
        cmd = [
            'sudo', 'ovs-ofctl', '-O', 'OpenFlow13', 'add-flow', switch,
            f'priority=5,ip,actions=drop'
        ]
        subprocess.run(cmd, capture_output=True)

    def quarantine_ip(self, ip: str) -> dict:
        "Immediately isolate a specific host via controller REST API"
        try:
            r = requests.post(f"{CONTROLLER_URL}/sdn/quarantine",
                             json={'ip': ip}, timeout=5)
            logger.warning(f"Quarantined: {ip}")
            return {'status': 'quarantined', 'ip': ip}
        except Exception as e:
            logger.error(f"Quarantine failed: {e}")
            return {'error': str(e)}

    def add_policy(self, src_zone, dst_zone, ports, desc="") -> dict:
        policy = ZonePolicy(src_zone, dst_zone, ports, description=desc)
        self.policies.append(policy)
        # Push to OVS immediately
        src_net = self.ZONES[src_zone]
        dst_net = self.ZONES[dst_zone]
        for port in ports:
            self._install_ovs_allow_rule('s1', src_net, dst_net, port)
        logger.info(f"New policy: {src_zone} → {dst_zone} ports={ports}")
        return {'status': 'added', 'rules': len(ports)}

    def get_flow_dump(self) -> str:
        "Show current flow table on s1"
        import subprocess
        result = subprocess.run(
            ['sudo', 'ovs-ofctl', '-O', 'OpenFlow13', 'dump-flows', 's1'],
            capture_output=True, text=True
        )
        return result.stdout


# ─── Flask REST API ────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
seg_engine = MicroSegmentationEngine()

@app.route('/seg/enforce', methods=['POST'])
def enforce():
    seg_engine.enforce_all_policies()
    return jsonify({'status': 'policies enforced', 'count': len(seg_engine.policies)})

@app.route('/seg/policies', methods=['GET'])
def policies():
    return jsonify([{
        'src_zone': p.src_zone, 'dst_zone': p.dst_zone,
        'ports': p.allowed_ports, 'active': p.active,
        'description': p.description
    } for p in seg_engine.policies])

@app.route('/seg/quarantine', methods=['POST'])
def quarantine():
    data = request.get_json()
    return jsonify(seg_engine.quarantine_ip(data['ip']))

@app.route('/seg/flows', methods=['GET'])
def flows():
    return jsonify({'flows': seg_engine.get_flow_dump()})

@app.route('/seg/add_policy', methods=['POST'])
def add_policy():
    data = request.get_json()
    result = seg_engine.add_policy(
        data['src_zone'], data['dst_zone'], data['ports'],
        data.get('description', '')
    )
    return jsonify(result)

if __name__ == '__main__':
    logger.info("Micro-Segmentation API starting on :5002")
    app.run(host='0.0.0.0', port=5002)
