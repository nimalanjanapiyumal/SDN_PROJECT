#!/usr/bin/env python3
# sdn_controller.py
# Main Ryu SDN Controller — integrates all security modules
# H D P Chathuranga — IT22902566

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp, arp
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
import json, logging, time, threading
from collections import defaultdict

# Configure logging
logging.basicConfig(
    filename='logs/controller.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class SDNSecurityController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SecurityRESTAPI, {'controller': self})

        self.mac_to_port = {}           # MAC learning table
        self.blocked_ips = set()         # CTI blocked IPs
        self.quarantine_hosts = set()    # Auth quarantine list
        self.zone_policies = {}          # Micro-seg policies
        self.flow_stats = defaultdict(int)
        self.datapaths = {}              # Connected switches

        # Zone definitions matching our topology
        self.zones = {
            'web':  {'subnet': '10.0.0.0/24', 'switch': 's2'},
            'app':  {'subnet': '10.0.1.0/24', 'switch': 's3'},
            'db':   {'subnet': '10.0.2.0/24', 'switch': 's4'},
        }

        # Allowed inter-zone flows
        self.allowed_flows = [
            ('web', 'app', [80, 443, 8080]),   # Web → App: HTTP/HTTPS
            ('app', 'db',  [3306, 5432, 6379]),  # App → DB: MySQL/Postgres/Redis
        ]
        # Web → DB DIRECT is BLOCKED (lateral movement prevention)

        self.logger.info("[FRAMEWORK] SDN Security Controller started")
        logger.info("SDN Security Controller v1.0 initialized")

    # ─── Switch Connect ───────────────────────────────────────────
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow: send unknown packets to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                           ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, 0, match, actions)
        self.logger.info(f"[CONTROLLER] Switch s{datapath.id} connected")
        logger.info(f"Switch {datapath.id} connected, table-miss installed")

    # ─── Packet In Handler ────────────────────────────────────────
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if eth is None:
            return

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        # ── Security Check 1: Blocked IPs (CTI) ──
        if ip_pkt and ip_pkt.src in self.blocked_ips:
            self._drop_packet(datapath, parser, in_port, ip_pkt.src)
            logger.warning(f"[CTI] Blocked IoC traffic from {ip_pkt.src}")
            return

        # ── Security Check 2: Quarantined hosts (Auth) ──
        if ip_pkt and ip_pkt.src in self.quarantine_hosts:
            self._drop_packet(datapath, parser, in_port, ip_pkt.src)
            logger.warning(f"[AUTH] Dropped quarantine traffic from {ip_pkt.src}")
            return

        # ── Security Check 3: Micro-segmentation zone enforcement ──
        if ip_pkt and not self._check_zone_policy(ip_pkt.src, ip_pkt.dst, pkt):
            self._drop_packet(datapath, parser, in_port, ip_pkt.src, dst=ip_pkt.dst)
            logger.warning(f"[MICROSEG] Blocked lateral: {ip_pkt.src} → {ip_pkt.dst}")
            return

        # ── Normal forwarding (MAC learning) ──
        dst_mac = eth.dst
        out_port = self.mac_to_port[dpid].get(dst_mac, ofproto.OFPP_FLOOD)

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac, eth_src=eth.src)
            self._add_flow(datapath, 10, match, actions)

        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=data
        )
        datapath.send_msg(out)

    # ─── Zone Policy Check ────────────────────────────────────────
    def _check_zone_policy(self, src_ip, dst_ip, pkt):
        "Return True if flow is allowed, False if it should be blocked"
        src_zone = self._get_zone(src_ip)
        dst_zone = self._get_zone(dst_ip)

        if src_zone is None or dst_zone is None:
            return True   # Not our subnets, allow
        if src_zone == dst_zone:
            return True   # Same zone, always allow

        # Check allowed inter-zone policies
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)
        dst_port = (tcp_pkt.dst_port if tcp_pkt else
                    udp_pkt.dst_port if udp_pkt else None)

        for (src_z, dst_z, ports) in self.allowed_flows:
            if src_zone == src_z and dst_zone == dst_z:
                if dst_port is None or dst_port in ports:
                    return True

        return False   # Block: no matching policy

    def _get_zone(self, ip):
        import ipaddress
        try:
            addr = ipaddress.ip_address(ip)
            for zone, info in self.zones.items():
                if addr in ipaddress.ip_network(info['subnet'], strict=False):
                    return zone
        except: pass
        return None

    # ─── Flow Rule Helpers ────────────────────────────────────────
    def _add_flow(self, datapath, priority, match, actions, timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match,
            instructions=inst, hard_timeout=timeout,
            idle_timeout=0 if timeout==0 else timeout
        )
        datapath.send_msg(mod)
        self.flow_stats['installed'] += 1

    def _drop_packet(self, datapath, parser, in_port, src_ip, dst=None, timeout=300):
        "Install a high-priority DROP rule for this IP"
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip)
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, priority=500, match=match,
            instructions=[], hard_timeout=timeout
        )
        datapath.send_msg(mod)

    # ─── Public API Methods (called by REST API) ──────────────────
    def block_ip(self, ip, timeout=3600):
        "Block an IP across all switches (CTI)"
        self.blocked_ips.add(ip)
        for dp in self.datapaths.values():
            self._drop_packet(dp, dp.ofproto_parser, 0, ip, timeout=timeout)
        logger.info(f"[CTI] Blocked IP: {ip} for {timeout}s")
        return True

    def quarantine_host(self, ip):
        "Isolate a host completely (Auth anomaly)"
        self.quarantine_hosts.add(ip)
        for dp in self.datapaths.values():
            self._drop_packet(dp, dp.ofproto_parser, 0, ip, timeout=0)
        logger.warning(f"[AUTH] Quarantined host: {ip}")
        return True

    def release_host(self, ip):
        "Remove quarantine"
        self.quarantine_hosts.discard(ip)
        self.blocked_ips.discard(ip)
        logger.info(f"[AUTH] Released host: {ip}")
        return True

    def get_stats(self):
        return {
            'blocked_ips': list(self.blocked_ips),
            'quarantined': list(self.quarantine_hosts),
            'flow_stats': dict(self.flow_stats),
            'switches': list(self.datapaths.keys()),
            'zones': self.zones,
            'timestamp': time.time()
        }


# ─── REST API ─────────────────────────────────────────────────
class SecurityRESTAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.controller = data['controller']

    @route('sdn', '/sdn/stats', methods=['GET'])
    def get_stats(self, req, **kwargs):
        stats = self.controller.get_stats()
        return self._json_response(stats)

    @route('sdn', '/sdn/block', methods=['POST'])
    def block_ip(self, req, **kwargs):
        body = json.loads(req.body)
        ip = body.get('ip')
        timeout = body.get('timeout', 3600)
        result = self.controller.block_ip(ip, timeout)
        return self._json_response({'status': 'blocked', 'ip': ip})

    @route('sdn', '/sdn/quarantine', methods=['POST'])
    def quarantine(self, req, **kwargs):
        body = json.loads(req.body)
        ip = body.get('ip')
        self.controller.quarantine_host(ip)
        return self._json_response({'status': 'quarantined', 'ip': ip})

    @route('sdn', '/sdn/release', methods=['POST'])
    def release(self, req, **kwargs):
        body = json.loads(req.body)
        ip = body.get('ip')
        self.controller.release_host(ip)
        return self._json_response({'status': 'released', 'ip': ip})

    @route('sdn', '/sdn/zones', methods=['GET'])
    def get_zones(self, req, **kwargs):
        return self._json_response(self.controller.zones)

    def _json_response(self, data):
        from webob import Response
        res = Response(content_type='application/json')
        res.body = json.dumps(data).encode()
        return res
