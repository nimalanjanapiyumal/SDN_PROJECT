"""
Stable PP2 Controller for Member 1
- Ryu SDN controller
- REST APIs
- DFPS priority handling
- Switch-specific rule installation
- No PacketIn traffic processing (for stability)
"""

import time
import threading
import queue
from flask import Flask, request, jsonify
from flask_cors import CORS

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (
    MAIN_DISPATCHER,
    DEAD_DISPATCHER,
    CONFIG_DISPATCHER,
    set_ev_cls
)
from ryu.ofproto import ofproto_v1_3


# =========================================================
# GLOBAL STATE
# =========================================================
intent_queue = queue.Queue()
context_lock = threading.Lock()

context_state = {
    "load": "normal",
    "congestion": "low",
    "threat": "low",
    "latency_ms": 0
}

# Static host inventory based on your known topology
host_table = {
    "10.0.0.1":  {"switch": "s4", "tier": "web"},
    "10.0.0.2":  {"switch": "s4", "tier": "web"},
    "10.0.0.3":  {"switch": "s4", "tier": "web"},
    "10.0.0.4":  {"switch": "s4", "tier": "web"},
    "10.0.0.5":  {"switch": "s4", "tier": "web"},
    "10.0.0.6":  {"switch": "s4", "tier": "web"},
    "10.0.0.7":  {"switch": "s5", "tier": "app"},
    "10.0.0.8":  {"switch": "s5", "tier": "app"},
    "10.0.0.9":  {"switch": "s5", "tier": "app"},
    "10.0.0.10": {"switch": "s5", "tier": "app"},
    "10.0.0.11": {"switch": "s5", "tier": "app"},
    "10.0.0.12": {"switch": "s6", "tier": "db"},
    "10.0.0.13": {"switch": "s6", "tier": "db"},
    "10.0.0.14": {"switch": "s6", "tier": "db"},
    "10.0.0.15": {"switch": "s6", "tier": "db"}
}

metrics = {
    "flows_installed": 0,
    "intents_received": 0,
    "intents_executed": 0,
    "last_dfps": 0
}


# =========================================================
# DFPS ENGINE
# =========================================================
def context_score(ctx):
    score = 1

    threat = str(ctx.get("threat", "low")).lower()
    load = str(ctx.get("load", "normal")).lower()
    congestion = str(ctx.get("congestion", "low")).lower()
    latency = float(ctx.get("latency_ms", 0) or 0)

    if threat == "high":
        score += 2
    elif threat == "medium":
        score += 1

    if load == "high":
        score += 1
    if congestion == "high":
        score += 1
    if latency >= 100:
        score += 1

    return score


def calculate_dfps(intent, ctx):
    alpha, beta, gamma = 0.5, 0.3, 0.2

    pi = int(intent.get("priority", 1))
    pc = context_score(ctx)

    age = time.time() - intent["ts"]
    if age < 5:
        t = 1.0
    elif age < 30:
        t = 0.6
    else:
        t = 0.3

    return round(alpha * pi + beta * pc + gamma * t, 3)


# =========================================================
# FLASK API
# =========================================================
def start_flask_app(ryu_app):
    app = Flask("intent_controller_api")
    CORS(app)

    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok"})

    @app.route('/api/intent/submit', methods=['POST'])
    def submit_intent():
        data = request.get_json(force=True)

        intent = {
            "text": data.get("intent", ""),
            "type": data.get("type", "generic"),
            "priority": int(data.get("priority", 1)),
            "src_ip": data.get("src_ip"),
            "dst_ip": data.get("dst_ip"),
            "proto": data.get("proto"),
            "dst_port": data.get("dst_port"),
            "ts": time.time()
        }

        intent_queue.put(intent)
        metrics["intents_received"] += 1
        ryu_app.logger.info("Intent received: %s", intent)

        return jsonify({"status": "OK", "intent": intent})

    @app.route('/api/context/update', methods=['POST'])
    def update_context():
        data = request.get_json(force=True)

        with context_lock:
            context_state.update(data)
            ctx_copy = dict(context_state)

        ryu_app.logger.info("Context updated: %s", data)
        return jsonify({"status": "updated", "context": ctx_copy})

    @app.route('/api/metrics/get', methods=['GET'])
    def get_metrics():
        with context_lock:
            ctx = dict(context_state)

        return jsonify({
            "metrics": metrics,
            "context": ctx
        })

    @app.route('/api/network/hosts', methods=['GET'])
    def get_hosts():
        return jsonify({
            "total_hosts": len(host_table),
            "hosts": host_table
        })

    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        ryu_app.logger.exception("Flask API crashed: %s", e)


# =========================================================
# RYU CONTROLLER
# =========================================================
class IntentRyuController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.datapaths = {}

        threading.Thread(
            target=start_flask_app,
            args=(self,),
            daemon=True
        ).start()

        threading.Thread(
            target=self._optimization_loop,
            daemon=True
        ).start()

        self.logger.info("Stable PP2 controller started")

    # -----------------------------------------------------
    # SWITCH CONNECTION HANDLING
    # -----------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
            self.logger.info("Datapath connected: %s", dp.id)
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(dp.id, None)
            self.logger.info("Datapath disconnected: %s", dp.id)

    # -----------------------------------------------------
    # TABLE MISS FLOW
    # -----------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
            )
        ]

        self.add_flow(dp, 0, match, actions)
        self.logger.info("Table-miss flow installed on switch s%s", dp.id)

    # -----------------------------------------------------
    # DISABLED PACKET-IN FOR STABILITY
    # -----------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        return

    # -----------------------------------------------------
    # FLOW INSTALL
    # -----------------------------------------------------
    def add_flow(self, datapath, priority, match, actions,
                 idle_timeout=60, hard_timeout=0):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        inst = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        )

        datapath.send_msg(mod)
        metrics["flows_installed"] += 1

    # -----------------------------------------------------
    # TARGET SWITCH DECISION
    # -----------------------------------------------------
    def get_target_switch_for_ip(self, ip):
        if not ip:
            return None
        try:
            last_octet = int(ip.split('.')[-1])
        except Exception:
            return None

        if 1 <= last_octet <= 6:
            return 4
        elif 7 <= last_octet <= 11:
            return 5
        elif 12 <= last_octet <= 15:
            return 6
        return None

    # -----------------------------------------------------
    # INTENT TEMPLATES
    # -----------------------------------------------------
    def _handle_intent(self, intent):
        itype = intent["type"]

        if itype == "security" and intent.get("src_ip"):
            self._install_security_rule(intent)

        elif itype == "load" and intent.get("dst_ip"):
            self._install_load_rule(intent)

        elif itype == "qos" and intent.get("dst_ip"):
            self._install_qos_rule(intent)

        elif itype == "monitor":
            self.logger.info("Monitoring intent accepted: %s", intent)

    def _install_security_rule(self, intent):
        src_ip = intent["src_ip"]
        proto = intent.get("proto")

        target_dpid = self.get_target_switch_for_ip(src_ip)
        if target_dpid is None:
            self.logger.warning("No target switch found for %s", src_ip)
            return

        dp = self.datapaths.get(target_dpid)
        if dp is None:
            self.logger.warning("Target switch s%s not connected", target_dpid)
            return

        parser = dp.ofproto_parser

        match_fields = {
            "eth_type": 0x0800,
            "ipv4_src": src_ip
        }

        if proto == "icmp":
            match_fields["ip_proto"] = 1
        elif proto == "tcp":
            match_fields["ip_proto"] = 6
        elif proto == "udp":
            match_fields["ip_proto"] = 17

        match = parser.OFPMatch(**match_fields)
        actions = []  # DROP

        self.add_flow(dp, 100, match, actions)
        self.logger.info(
            "Security rule installed for %s on switch s%s",
            src_ip, target_dpid
        )

    def _install_load_rule(self, intent):
        dst_ip = intent["dst_ip"]

        target_dpid = self.get_target_switch_for_ip(dst_ip)
        if target_dpid is None:
            self.logger.warning("No target switch found for %s", dst_ip)
            return

        dp = self.datapaths.get(target_dpid)
        if dp is None:
            self.logger.warning("Target switch s%s not connected", target_dpid)
            return

        parser = dp.ofproto_parser
        match = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_dst=dst_ip
        )
        actions = [parser.OFPActionOutput(dp.ofproto.OFPP_FLOOD)]

        self.add_flow(dp, 50, match, actions)
        self.logger.info(
            "Load rule installed for %s on switch s%s",
            dst_ip, target_dpid
        )

    def _install_qos_rule(self, intent):
        dst_ip = intent["dst_ip"]

        target_dpid = self.get_target_switch_for_ip(dst_ip)
        if target_dpid is None:
            self.logger.warning("No target switch found for %s", dst_ip)
            return

        dp = self.datapaths.get(target_dpid)
        if dp is None:
            self.logger.warning("Target switch s%s not connected", target_dpid)
            return

        parser = dp.ofproto_parser
        match = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_dst=dst_ip
        )
        actions = [parser.OFPActionOutput(dp.ofproto.OFPP_FLOOD)]

        self.add_flow(dp, 70, match, actions)
        self.logger.info(
            "QoS rule installed for %s on switch s%s",
            dst_ip, target_dpid
        )

    # -----------------------------------------------------
    # DFPS OPTIMIZATION LOOP
    # -----------------------------------------------------
    def _optimization_loop(self):
        self.logger.info("DFPS Optimization loop running")

        while True:
            intents = []

            while not intent_queue.empty():
                intents.append(intent_queue.get())

            if intents:
                with context_lock:
                    ctx = dict(context_state)

                for i in intents:
                    i["dfps"] = calculate_dfps(i, ctx)

                intents.sort(key=lambda x: x["dfps"], reverse=True)

                for intent in intents:
                    metrics["last_dfps"] = intent["dfps"]
                    metrics["intents_executed"] += 1

                    self.logger.info(
                        "Executing intent DFPS=%s %s",
                        intent["dfps"], intent
                    )

                    self._handle_intent(intent)

            time.sleep(2)
