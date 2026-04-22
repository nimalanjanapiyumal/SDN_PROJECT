from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, arp, ipv4, tcp, udp
from ryu.lib.packet import ether_types
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import WSGIApplication

from sdn_hybrid_lb.utils.config import load_config
from sdn_hybrid_lb.utils.logging import setup_logger
from sdn_hybrid_lb.algorithms.hybrid import HybridLoadBalancer, FlowKey
from sdn_hybrid_lb.controller.flow_manager import FlowManager
from sdn_hybrid_lb.controller.rest_api import LBRestController
from sdn_hybrid_lb.monitoring.prometheus import PrometheusProvider, PrometheusConfig


class HybridLoadBalancerRyuApp(app_manager.RyuApp):
    """Ryu SDN controller app implementing VIP-based hybrid load balancing."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = setup_logger("sdn_hybrid_lb")

        # Load config (env var SDN_HYBRID_LB_CONFIG, else config.yaml)
        self.cfg = load_config()
        self.lb = HybridLoadBalancer(self.cfg)
        self.flow_mgr = FlowManager(self.logger)

        # Datapaths
        self.datapaths: Dict[int, object] = {}

        # L2 learning (for non-VIP traffic)
        self.mac_to_port: Dict[int, Dict[str, int]] = {}

        # Optional Prometheus provider
        self.prom: Optional[PrometheusProvider] = None
        if self.cfg.monitoring.prometheus.enabled:
            self.prom = PrometheusProvider(
                PrometheusConfig(
                    base_url=self.cfg.monitoring.prometheus.base_url,
                    timeout_sec=self.cfg.monitoring.prometheus.timeout_sec,
                    promql=self.cfg.monitoring.prometheus.promql,
                    instances=self.cfg.monitoring.instances,
                )
            )
            self.logger.info("Prometheus provider enabled: %s", self.cfg.monitoring.prometheus.base_url)

        # REST API registration
        wsgi = kwargs.get("wsgi")
        if wsgi:
            wsgi.register(LBRestController, {"app": self})
            self.logger.info("REST API registered on port %s", self.cfg.controller.rest_api_port)

        # Monitoring thread
        self._monitor_thread = hub.spawn(self._monitor)

    # ---------- OpenFlow basics ----------

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
            self.logger.info("Datapath connected: dpid=%s", dp.id)
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(dp.id, None)
            self.logger.info("Datapath disconnected: dpid=%s", dp.id)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features(self, ev):
        dp = ev.msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        # Table-miss flow (send to controller)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.flow_mgr.add_flow(dp, priority=0, match=match, actions=actions)
        self.logger.info("Installed table-miss flow on dpid=%s", dp.id)

    def _request_port_stats(self, dp):
        parser = dp.ofproto_parser
        req = parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY)
        dp.send_msg(req)

    # ---------- Monitoring loop ----------

    def _monitor(self):
        while True:
            try:
                for dp in list(self.datapaths.values()):
                    self._request_port_stats(dp)

                if self.prom:
                    self.prom.update(self.lb.backends)

                # GA periodic optimization
                ran = self.lb.maybe_run_ga()
                if ran:
                    self.logger.info("GA recomputed weights: %s", self.lb.status().get("weights"))

            except Exception as e:
                self.logger.exception("monitor loop error: %s", e)

            hub.sleep(self.cfg.controller.poll_interval_sec)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply(self, ev):
        dp = ev.msg.datapath
        for stat in ev.msg.body:
            # stat.port_no can be OFPP_LOCAL etc; filter physical ports
            if stat.port_no > 0 and stat.port_no < 0xFFFFFF00:
                self.lb.update_port_bytes(dp.id, int(stat.port_no), int(stat.tx_bytes), int(stat.rx_bytes))

    # ---------- Flow removed (optional for accurate active-conn counting) ----------

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _flow_removed(self, ev):
        msg = ev.msg
        m = msg.match
        try:
            ipv4_dst = m.get("ipv4_dst")
            if ipv4_dst != self.lb.vip.ip:
                return  # only count forward VIP flows

            client_ip = m.get("ipv4_src")
            ip_proto = int(m.get("ip_proto"))
            if ip_proto == 6:
                l4_src = int(m.get("tcp_src"))
                l4_dst = int(m.get("tcp_dst"))
            elif ip_proto == 17:
                l4_src = int(m.get("udp_src"))
                l4_dst = int(m.get("udp_dst"))
            else:
                return
            flow: FlowKey = (str(client_ip), l4_src, l4_dst, ip_proto)
            self.lb.notify_flow_removed(flow)
        except Exception:
            # best effort only
            return

    # ---------- Packet-in handler ----------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn source MAC for normal switching
        self.mac_to_port[dpid][eth.src] = in_port

        # Ignore LLDP
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Handle ARP (respond for VIP)
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            if arp_pkt.opcode == arp.ARP_REQUEST and arp_pkt.dst_ip == self.lb.vip.ip:
                # Reply: VIP MAC
                reply = self.flow_mgr.craft_arp_reply(
                    src_mac=self.lb.vip.mac,
                    src_ip=self.lb.vip.ip,
                    dst_mac=arp_pkt.src_mac,
                    dst_ip=arp_pkt.src_ip,
                )
                actions = [parser.OFPActionOutput(in_port)]
                self.flow_mgr.send_packet_out(dp, ofproto.OFPP_CONTROLLER, actions, reply)
                return

            # Otherwise: normal L2 forwarding (flood or learned)
            out_port = self.mac_to_port[dpid].get(eth.dst, ofproto.OFPP_FLOOD)
            actions = [parser.OFPActionOutput(out_port)]
            self.flow_mgr.send_packet_out(dp, in_port, actions, msg.data)
            return

        # Handle IPv4 to VIP
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt and ip_pkt.dst == self.lb.vip.ip:
            ip_proto = ip_pkt.proto

            l4_src = None
            l4_dst = None
            if ip_proto == 6:
                t = pkt.get_protocol(tcp.tcp)
                if not t:
                    return
                l4_src, l4_dst = int(t.src_port), int(t.dst_port)
            elif ip_proto == 17:
                u = pkt.get_protocol(udp.udp)
                if not u:
                    return
                l4_src, l4_dst = int(u.src_port), int(u.dst_port)
            else:
                # Only TCP/UDP handled in this implementation
                return

            flow: FlowKey = (str(ip_pkt.src), l4_src, l4_dst, int(ip_proto))

            backend = self.lb.choose_backend(flow)
            if not backend:
                self.logger.warning("No eligible backend for flow=%s", flow)
                return

            # Install NAT-like VIP rewrite flows
            buffer_id = msg.buffer_id if msg.buffer_id != ofproto.OFP_NO_BUFFER else None
            raw_packet = b"" if buffer_id is not None else msg.data  # if buffered, switch will send
            self.flow_mgr.install_vip_rewrite_flows(
                datapath=dp,
                client_in_port=in_port,
                client_out_port=in_port,
                backend_out_port=backend.port,
                vip_ip=self.lb.vip.ip,
                vip_mac=self.lb.vip.mac,
                backend_ip=backend.ip,
                backend_mac=backend.mac,
                client_ip=str(ip_pkt.src),
                ip_proto=int(ip_proto),
                l4_src=l4_src,
                l4_dst=l4_dst,
                idle_timeout=self.cfg.controller.flow_idle_timeout,
                hard_timeout=self.cfg.controller.flow_hard_timeout,
                buffer_id=buffer_id,
                raw_packet=raw_packet,
            )

            self.logger.info(
                "LB flow installed: client=%s:%s -> VIP:%s proto=%s => %s(%s)",
                ip_pkt.src,
                l4_src,
                l4_dst,
                ip_proto,
                backend.name,
                backend.ip,
            )
            return

        # Default: L2 learning switch behavior for other traffic
        out_port = self.mac_to_port[dpid].get(eth.dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]
        self.flow_mgr.send_packet_out(dp, in_port, actions, msg.data)
