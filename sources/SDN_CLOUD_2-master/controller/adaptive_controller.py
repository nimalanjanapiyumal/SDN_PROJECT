
from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import networkx as nx
import psutil
from prometheus_client import Counter, Gauge, start_http_server

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, DEAD_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import arp, ethernet, ether_types, ipv4, packet, tcp, udp
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event
from ryu.topology.api import get_link, get_switch

BASE_PATH = "/api/v1"
LOGGER = logging.getLogger("adaptive-controller")

LINK_CAPACITY_BPS = 20_000_000.0
METRICS_PORT = int(os.environ.get("SDN_CONTROLLER_METRICS_PORT", "9101"))
REST_PORT = int(os.environ.get("SDN_CONTROLLER_API_PORT", "8080"))


def dpid_str(value: int | str) -> str:
    if isinstance(value, str):
        return value
    return f"{value:016x}"


class AdaptiveController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.datapaths: Dict[str, Any] = {}
        self.mac_to_port: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.ip_to_mac: Dict[str, str] = {}
        self.host_location: Dict[str, Tuple[str, int]] = {}
        self.switch_graph = nx.DiGraph()
        self.packet_in_events: deque[float] = deque(maxlen=5000)
        self.lock = Lock()

        self.flow_counter_snapshots: Dict[str, Dict[str, float]] = {}
        self.port_counter_snapshots: Dict[Tuple[str, int], Dict[str, float]] = {}
        self.latest_flow_summary: Dict[str, Dict[str, float]] = {}
        self.latest_port_utilization: Dict[Tuple[str, int], float] = {}
        self.latest_talkers_by_dpid: Dict[str, List[Dict[str, Any]]] = {}
        self.top_talkers: List[Dict[str, Any]] = []
        self.summary: Dict[str, float] = {
            "active_flows": 0.0,
            "packet_rate_per_sec": 0.0,
            "byte_rate_per_sec": 0.0,
            "max_link_utilization_ratio": 0.0,
            "controller_cpu_percent": 0.0,
            "controller_memory_percent": 0.0,
            "packet_in_rate_per_sec": 0.0,
            "last_mitigation_latency_ms": 0.0,
        }

        self.path_overrides: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.mitigations: Dict[str, Dict[str, Any]] = {}

        start_http_server(METRICS_PORT, addr="0.0.0.0")
        self.metric_active_flows = Gauge(
            "cloud_sdn_active_flows",
            "Number of active SDN flows excluding the table-miss flow.",
            ["dpid"],
        )
        self.metric_total_packets = Gauge(
            "cloud_sdn_total_packets",
            "Observed packets from flow statistics.",
            ["dpid"],
        )
        self.metric_total_bytes = Gauge(
            "cloud_sdn_total_bytes",
            "Observed bytes from flow statistics.",
            ["dpid"],
        )
        self.metric_packet_rate = Gauge(
            "cloud_sdn_packet_rate_per_sec",
            "Packet rate inferred from flow stats.",
            ["dpid"],
        )
        self.metric_byte_rate = Gauge(
            "cloud_sdn_byte_rate_per_sec",
            "Byte rate inferred from flow stats.",
            ["dpid"],
        )
        self.metric_packet_in_rate = Gauge(
            "cloud_sdn_packet_in_rate_per_sec",
            "Packet-in rate observed by the controller.",
        )
        self.metric_link_utilization = Gauge(
            "cloud_sdn_link_utilization_ratio",
            "Estimated link utilization ratio from port stats.",
            ["dpid", "port"],
        )
        self.metric_controller_cpu = Gauge(
            "cloud_sdn_controller_cpu_percent",
            "Controller CPU utilization.",
        )
        self.metric_controller_memory = Gauge(
            "cloud_sdn_controller_memory_percent",
            "Controller memory utilization.",
        )
        self.metric_last_mitigation_latency = Gauge(
            "cloud_sdn_last_mitigation_latency_ms",
            "Latency of the last applied mitigation.",
        )
        self.metric_mitigations_total = Counter(
            "cloud_sdn_mitigations_total",
            "Number of mitigations applied by the controller.",
            ["action"],
        )

        self._start_rest_server()
        self.monitor_thread = hub.spawn(self._monitor)
        self.expiry_thread = hub.spawn(self._expiry_loop)

    # -------------------------------------------------------------------------
    # Ryu lifecycle and topology discovery
    # -------------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev: ofp_event.EventOFPStateChange) -> None:
        datapath = ev.datapath
        dpid = dpid_str(datapath.id)
        if ev.state == MAIN_DISPATCHER:
            if dpid not in self.datapaths:
                LOGGER.info("Register datapath %s", dpid)
                self.datapaths[dpid] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if dpid in self.datapaths:
                LOGGER.info("Unregister datapath %s", dpid)
                del self.datapaths[dpid]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev: ofp_event.EventOFPSwitchFeatures) -> None:
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        LOGGER.info("Switch connected: %s", dpid_str(datapath.id))
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(datapath.ofproto.OFPP_CONTROLLER, datapath.ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, priority=0, match=match, actions=actions)

    @set_ev_cls(event.EventSwitchEnter)
    def on_switch_enter(self, _ev: event.EventSwitchEnter) -> None:
        self._refresh_topology()

    @set_ev_cls(event.EventSwitchLeave)
    def on_switch_leave(self, _ev: event.EventSwitchLeave) -> None:
        self._refresh_topology()

    @set_ev_cls(event.EventLinkAdd)
    def on_link_add(self, _ev: event.EventLinkAdd) -> None:
        self._refresh_topology()

    @set_ev_cls(event.EventLinkDelete)
    def on_link_delete(self, _ev: event.EventLinkDelete) -> None:
        self._refresh_topology()

    def _refresh_topology(self) -> None:
        try:
            switches = get_switch(self, None)
            links = get_link(self, None)
        except Exception as exc:
            LOGGER.warning("Topology refresh failed: %s", exc)
            return

        graph = nx.DiGraph()
        for sw in switches:
            graph.add_node(dpid_str(sw.dp.id))
        for link in links:
            src = dpid_str(link.src.dpid)
            dst = dpid_str(link.dst.dpid)
            graph.add_edge(src, dst, port=link.src.port_no)
        with self.lock:
            self.switch_graph = graph

    # -------------------------------------------------------------------------
    # Packet processing and path installation
    # -------------------------------------------------------------------------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev: ofp_event.EventOFPPacketIn) -> None:
        msg = ev.msg
        datapath = msg.datapath
        dpid = dpid_str(datapath.id)
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        self.packet_in_events.append(time.time())

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst_mac = eth.dst
        src_mac = eth.src
        in_port = msg.match["in_port"]

        self.mac_to_port[dpid][src_mac] = in_port
        self.host_location[src_mac] = (dpid, in_port)

        info = self._extract_packet_info(pkt, src_mac=src_mac, dst_mac=dst_mac, in_port=in_port)
        if info.get("src_ip"):
            self.ip_to_mac[info["src_ip"]] = src_mac
        if info.get("dst_ip") and dst_mac != "ff:ff:ff:ff:ff:ff":
            self.ip_to_mac.setdefault(info["dst_ip"], dst_mac)

        out_port = ofproto.OFPP_FLOOD
        if dst_mac in self.host_location:
            path = self._select_path(
                src_mac=src_mac,
                dst_mac=dst_mac,
                src_ip=info.get("src_ip"),
                dst_ip=info.get("dst_ip"),
            )
            if path:
                out_port = self._path_next_hop_port(path, current_switch=dpid)
                if out_port is not None:
                    self._install_path(path, info, priority=10, idle_timeout=30, hard_timeout=0, broad=False)

        actions = [parser.OFPActionOutput(out_port)]
        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    def _extract_packet_info(
        self,
        pkt: packet.Packet,
        src_mac: str,
        dst_mac: str,
        in_port: int,
    ) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "src_mac": src_mac,
            "dst_mac": dst_mac,
            "in_port": in_port,
            "eth_type": None,
            "src_ip": None,
            "dst_ip": None,
            "ip_proto": None,
            "transport_src": None,
            "transport_dst": None,
        }

        eth = pkt.get_protocol(ethernet.ethernet)
        if eth:
            info["eth_type"] = eth.ethertype

        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            info["eth_type"] = ether_types.ETH_TYPE_ARP
            info["src_ip"] = arp_pkt.src_ip
            info["dst_ip"] = arp_pkt.dst_ip

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            info["eth_type"] = ether_types.ETH_TYPE_IP
            info["src_ip"] = ip_pkt.src
            info["dst_ip"] = ip_pkt.dst
            info["ip_proto"] = ip_pkt.proto

            tcp_pkt = pkt.get_protocol(tcp.tcp)
            udp_pkt = pkt.get_protocol(udp.udp)
            if tcp_pkt:
                info["transport_src"] = tcp_pkt.src_port
                info["transport_dst"] = tcp_pkt.dst_port
            elif udp_pkt:
                info["transport_src"] = udp_pkt.src_port
                info["transport_dst"] = udp_pkt.dst_port

        return info

    def _combined_graph(self) -> nx.DiGraph:
        with self.lock:
            graph = self.switch_graph.copy()
            for mac, (dpid, port) in self.host_location.items():
                graph.add_node(mac)
                graph.add_edge(mac, dpid, port=port)
                graph.add_edge(dpid, mac, port=port)
        return graph

    def _all_host_paths(self, src_mac: str, dst_mac: str) -> List[List[str]]:
        graph = self._combined_graph()
        if not graph.has_node(src_mac) or not graph.has_node(dst_mac):
            return []
        try:
            paths = list(nx.all_simple_paths(graph, src_mac, dst_mac, cutoff=8))
        except nx.NetworkXNoPath:
            return []
        paths = sorted(paths, key=lambda p: (len(p), p))
        return paths

    def _select_path(
        self,
        src_mac: str,
        dst_mac: str,
        src_ip: Optional[str],
        dst_ip: Optional[str],
    ) -> Optional[List[str]]:
        paths = self._all_host_paths(src_mac, dst_mac)
        if not paths:
            return None
        if src_ip and dst_ip:
            override = self.path_overrides.get((src_ip, dst_ip))
            if override and override.get("expires_at", 0.0) > time.time():
                index = int(override.get("selected_index", 0))
                if 0 <= index < len(paths):
                    return paths[index]
        return paths[0]

    def _path_next_hop_port(self, path: List[str], current_switch: str) -> Optional[int]:
        graph = self._combined_graph()
        if current_switch not in path:
            return None
        idx = path.index(current_switch)
        if idx >= len(path) - 1:
            return None
        next_node = path[idx + 1]
        if not graph.has_edge(current_switch, next_node):
            return None
        return int(graph[current_switch][next_node]["port"])

    def _path_in_port(self, path: List[str], current_switch: str) -> Optional[int]:
        graph = self._combined_graph()
        if current_switch not in path:
            return None
        idx = path.index(current_switch)
        if idx == 0:
            return None
        prev_node = path[idx - 1]
        if not graph.has_edge(current_switch, prev_node):
            return None
        return int(graph[current_switch][prev_node]["port"])

    def _build_match(self, datapath: Any, info: Dict[str, Any], in_port: Optional[int], broad: bool) -> Any:
        parser = datapath.ofproto_parser
        eth_type = info.get("eth_type")
        src_ip = info.get("src_ip")
        dst_ip = info.get("dst_ip")
        ip_proto = info.get("ip_proto")
        transport_src = info.get("transport_src")
        transport_dst = info.get("transport_dst")

        kwargs: Dict[str, Any] = {}
        if in_port is not None and not broad:
            kwargs["in_port"] = int(in_port)

        if eth_type == ether_types.ETH_TYPE_IP and src_ip and dst_ip:
            kwargs.update(
                {
                    "eth_type": ether_types.ETH_TYPE_IP,
                    "ipv4_src": src_ip,
                    "ipv4_dst": dst_ip,
                }
            )
            if not broad and ip_proto is not None:
                kwargs["ip_proto"] = ip_proto
                if ip_proto == 6 and transport_src is not None and transport_dst is not None:
                    kwargs["tcp_src"] = int(transport_src)
                    kwargs["tcp_dst"] = int(transport_dst)
                elif ip_proto == 17 and transport_src is not None and transport_dst is not None:
                    kwargs["udp_src"] = int(transport_src)
                    kwargs["udp_dst"] = int(transport_dst)
        elif eth_type == ether_types.ETH_TYPE_ARP and info.get("src_ip") and info.get("dst_ip"):
            kwargs.update(
                {
                    "eth_type": ether_types.ETH_TYPE_ARP,
                    "arp_spa": info["src_ip"],
                    "arp_tpa": info["dst_ip"],
                }
            )
        else:
            kwargs.update(
                {
                    "eth_src": info["src_mac"],
                    "eth_dst": info["dst_mac"],
                }
            )
        return parser.OFPMatch(**kwargs)

    def _install_path(
        self,
        path: List[str],
        info: Dict[str, Any],
        priority: int,
        idle_timeout: int,
        hard_timeout: int,
        broad: bool,
    ) -> None:
        switch_nodes = [node for node in path if node in self.datapaths]
        for switch_id in switch_nodes:
            datapath = self.datapaths.get(switch_id)
            if datapath is None:
                continue
            in_port = self._path_in_port(path, switch_id)
            out_port = self._path_next_hop_port(path, switch_id)
            if out_port is None:
                continue
            match = self._build_match(datapath, info, in_port=in_port, broad=broad)
            parser = datapath.ofproto_parser
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(
                datapath,
                priority=priority,
                match=match,
                actions=actions,
                idle_timeout=idle_timeout,
                hard_timeout=hard_timeout,
            )

    # -------------------------------------------------------------------------
    # Flow helpers
    # -------------------------------------------------------------------------

    def add_flow(
        self,
        datapath: Any,
        priority: int,
        match: Any,
        actions: List[Any],
        idle_timeout: int = 0,
        hard_timeout: int = 0,
    ) -> None:
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        instructions: List[Any] = []
        if actions:
            instructions.append(parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions))
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        datapath.send_msg(mod)

    def delete_flows(self, match_kwargs: Dict[str, Any]) -> None:
        for datapath in self.datapaths.values():
            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto
            match = parser.OFPMatch(**match_kwargs)
            mod = parser.OFPFlowMod(
                datapath=datapath,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                match=match,
            )
            datapath.send_msg(mod)

    # -------------------------------------------------------------------------
    # Monitoring loops and statistics
    # -------------------------------------------------------------------------

    def _monitor(self) -> None:
        while True:
            try:
                self._collect_system_metrics()
                self._collect_packet_in_rate()
                for datapath in list(self.datapaths.values()):
                    self._request_stats(datapath)
            except Exception as exc:  # pragma: no cover - runtime protection
                LOGGER.exception("Monitor loop failed: %s", exc)
            hub.sleep(5)

    def _expiry_loop(self) -> None:
        while True:
            try:
                expired_keys = [
                    key for key, value in list(self.mitigations.items()) if value.get("expires_at", 0.0) <= time.time()
                ]
                for key in expired_keys:
                    LOGGER.info("Expiring mitigation %s", key)
                    self._remove_mitigation(key)
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("Expiry loop failed: %s", exc)
            hub.sleep(2)

    def _collect_system_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        self.summary["controller_cpu_percent"] = float(cpu)
        self.summary["controller_memory_percent"] = float(mem)
        self.metric_controller_cpu.set(cpu)
        self.metric_controller_memory.set(mem)

    def _collect_packet_in_rate(self) -> None:
        now = time.time()
        while self.packet_in_events and now - self.packet_in_events[0] > 5:
            self.packet_in_events.popleft()
        rate = len(self.packet_in_events) / 5.0
        self.summary["packet_in_rate_per_sec"] = float(rate)
        self.metric_packet_in_rate.set(rate)

    def _request_stats(self, datapath: Any) -> None:
        parser = datapath.ofproto_parser
        datapath.send_msg(parser.OFPFlowStatsRequest(datapath))
        datapath.send_msg(parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY))

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev: ofp_event.EventOFPFlowStatsReply) -> None:
        body = ev.msg.body
        dpid = dpid_str(ev.msg.datapath.id)
        now = time.time()

        total_packets = 0.0
        total_bytes = 0.0
        active_flows = 0
        talkers: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for stat in body:
            match = stat.match
            if stat.priority == 0:
                continue
            if match.get("eth_type") == ether_types.ETH_TYPE_LLDP:
                continue

            active_flows += 1
            total_packets += float(stat.packet_count)
            total_bytes += float(stat.byte_count)

            src_ip = match.get("ipv4_src")
            dst_ip = match.get("ipv4_dst")
            if src_ip and dst_ip:
                key = (src_ip, dst_ip)
                current = talkers.setdefault(
                    key,
                    {
                        "src_ip": src_ip,
                        "dst_ip": dst_ip,
                        "bytes": 0.0,
                        "packets": 0.0,
                        "dpid": dpid,
                    },
                )
                current["bytes"] = max(float(stat.byte_count), current["bytes"])
                current["packets"] = max(float(stat.packet_count), current["packets"])

        previous = self.flow_counter_snapshots.get(dpid, {"bytes": 0.0, "packets": 0.0, "timestamp": now})
        delta_time = max(now - float(previous["timestamp"]), 1e-6)
        byte_rate = max((total_bytes - float(previous["bytes"])) / delta_time, 0.0)
        packet_rate = max((total_packets - float(previous["packets"])) / delta_time, 0.0)
        self.flow_counter_snapshots[dpid] = {"bytes": total_bytes, "packets": total_packets, "timestamp": now}

        self.latest_flow_summary[dpid] = {
            "active_flows": float(active_flows),
            "total_packets": float(total_packets),
            "total_bytes": float(total_bytes),
            "packet_rate_per_sec": float(packet_rate),
            "byte_rate_per_sec": float(byte_rate),
        }

        self.metric_active_flows.labels(dpid=dpid).set(active_flows)
        self.metric_total_packets.labels(dpid=dpid).set(total_packets)
        self.metric_total_bytes.labels(dpid=dpid).set(total_bytes)
        self.metric_packet_rate.labels(dpid=dpid).set(packet_rate)
        self.metric_byte_rate.labels(dpid=dpid).set(byte_rate)

        self.latest_talkers_by_dpid[dpid] = list(talkers.values())
        self._recompute_top_talkers()
        self._recompute_summary()

    def _recompute_top_talkers(self) -> None:
        merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for talkers in self.latest_talkers_by_dpid.values():
            for talker in talkers:
                key = (talker.get("src_ip"), talker.get("dst_ip"))
                existing = merged.get(key)
                if existing:
                    existing["bytes"] = max(float(existing["bytes"]), float(talker["bytes"]))
                    existing["packets"] = max(float(existing["packets"]), float(talker["packets"]))
                else:
                    merged[key] = dict(talker)

        self.top_talkers = sorted(
            merged.values(),
            key=lambda item: float(item.get("bytes", 0.0)),
            reverse=True,
        )[:10]

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev: ofp_event.EventOFPPortStatsReply) -> None:
        dpid = dpid_str(ev.msg.datapath.id)
        now = time.time()

        for stat in ev.msg.body:
            port_no = int(stat.port_no)
            if port_no >= 0xFFFFFF00:
                continue
            key = (dpid, port_no)
            total = float(stat.rx_bytes + stat.tx_bytes)
            previous = self.port_counter_snapshots.get(key, {"bytes": total, "timestamp": now})
            delta_time = max(now - float(previous["timestamp"]), 1e-6)
            byte_rate = max((total - float(previous["bytes"])) / delta_time, 0.0)
            utilization = min((byte_rate * 8.0) / LINK_CAPACITY_BPS, 1.5)
            self.port_counter_snapshots[key] = {"bytes": total, "timestamp": now}
            self.latest_port_utilization[key] = utilization
            self.metric_link_utilization.labels(dpid=dpid, port=str(port_no)).set(utilization)

        self._recompute_summary()

    def _recompute_summary(self) -> None:
        active_flows = sum(v.get("active_flows", 0.0) for v in self.latest_flow_summary.values())
        packet_rate = sum(v.get("packet_rate_per_sec", 0.0) for v in self.latest_flow_summary.values())
        byte_rate = sum(v.get("byte_rate_per_sec", 0.0) for v in self.latest_flow_summary.values())
        max_link_util = max(self.latest_port_utilization.values(), default=0.0)

        self.summary["active_flows"] = float(active_flows)
        self.summary["packet_rate_per_sec"] = float(packet_rate)
        self.summary["byte_rate_per_sec"] = float(byte_rate)
        self.summary["max_link_utilization_ratio"] = float(max_link_util)

    # -------------------------------------------------------------------------
    # Policy API and mitigation handling
    # -------------------------------------------------------------------------

    def apply_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action = str(payload.get("type", "")).lower()
        started = time.time()
        if action == "block":
            result = self._apply_block(payload)
        elif action == "reroute":
            result = self._apply_reroute(payload)
        elif action == "clear":
            result = self._clear_policy(payload)
        else:
            raise ValueError(f"Unsupported policy action: {action}")

        latency_ms = (time.time() - started) * 1000.0
        self.summary["last_mitigation_latency_ms"] = float(latency_ms)
        self.metric_last_mitigation_latency.set(latency_ms)
        if action in {"block", "reroute", "clear"} and result.get("status") == "ok":
            self.metric_mitigations_total.labels(action=action).inc()
        result["latency_ms"] = latency_ms
        return result

    def _apply_block(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        src_ip = payload.get("src_ip")
        if not src_ip:
            raise ValueError("block policy requires src_ip")
        duration = int(payload.get("duration", 60))
        reason = str(payload.get("reason", "security block"))

        for datapath in self.datapaths.values():
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip)
            self.add_flow(datapath, priority=300, match=match, actions=[], hard_timeout=duration)

        key = f"block:{src_ip}"
        self.mitigations[key] = {
            "type": "block",
            "src_ip": src_ip,
            "dst_ip": None,
            "reason": reason,
            "installed_at": time.time(),
            "expires_at": time.time() + duration,
            "payload": payload,
        }
        # Clear any reroute overrides associated with the blocked source.
        for override_key in list(self.path_overrides):
            if override_key[0] == src_ip:
                self.path_overrides.pop(override_key, None)

        return {"status": "ok", "action": "block", "src_ip": src_ip, "duration": duration}

    def _apply_reroute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        src_ip = payload.get("src_ip")
        dst_ip = payload.get("dst_ip")
        if not src_ip or not dst_ip:
            raise ValueError("reroute policy requires src_ip and dst_ip")
        src_mac = self.ip_to_mac.get(src_ip)
        dst_mac = self.ip_to_mac.get(dst_ip)
        if not src_mac or not dst_mac:
            return {
                "status": "error",
                "action": "reroute",
                "message": "Unable to resolve host MAC addresses yet. Generate traffic first.",
            }

        all_paths = self._all_host_paths(src_mac, dst_mac)
        if len(all_paths) < 2:
            return {
                "status": "error",
                "action": "reroute",
                "message": "No alternate path available in current topology view.",
            }

        selected_index = 1
        selected_path = all_paths[selected_index]
        duration = int(payload.get("duration", 60))
        reason = str(payload.get("reason", "reroute"))

        info = {
            "src_mac": src_mac,
            "dst_mac": dst_mac,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "eth_type": ether_types.ETH_TYPE_IP,
            "ip_proto": None,
            "transport_src": None,
            "transport_dst": None,
        }
        self._install_path(
            selected_path,
            info=info,
            priority=200,
            idle_timeout=duration,
            hard_timeout=duration,
            broad=True,
        )
        self.path_overrides[(src_ip, dst_ip)] = {
            "selected_index": selected_index,
            "expires_at": time.time() + duration,
            "reason": reason,
        }
        key = f"reroute:{src_ip}:{dst_ip}"
        self.mitigations[key] = {
            "type": "reroute",
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "reason": reason,
            "installed_at": time.time(),
            "expires_at": time.time() + duration,
            "payload": payload,
            "path": selected_path,
        }
        return {
            "status": "ok",
            "action": "reroute",
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "selected_path": selected_path,
            "duration": duration,
        }

    def _clear_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        src_ip = payload.get("src_ip")
        dst_ip = payload.get("dst_ip")
        removed = 0
        for key, mitigation in list(self.mitigations.items()):
            if src_ip and mitigation.get("src_ip") != src_ip:
                continue
            if dst_ip and mitigation.get("dst_ip") != dst_ip:
                continue
            self._remove_mitigation(key)
            removed += 1
        return {"status": "ok", "action": "clear", "removed": removed}

    def _remove_mitigation(self, key: str) -> None:
        record = self.mitigations.pop(key, None)
        if not record:
            return
        action = record.get("type")
        if action == "block" and record.get("src_ip"):
            self.delete_flows(
                {
                    "eth_type": ether_types.ETH_TYPE_IP,
                    "ipv4_src": record["src_ip"],
                }
            )
        elif action == "reroute" and record.get("src_ip") and record.get("dst_ip"):
            self.path_overrides.pop((record["src_ip"], record["dst_ip"]), None)
            self.delete_flows(
                {
                    "eth_type": ether_types.ETH_TYPE_IP,
                    "ipv4_src": record["src_ip"],
                    "ipv4_dst": record["dst_ip"],
                }
            )

    # -------------------------------------------------------------------------
    # State export
    # -------------------------------------------------------------------------

    def build_state(self) -> Dict[str, Any]:
        known_hosts = []
        for ip, mac in sorted(self.ip_to_mac.items()):
            dpid, port = self.host_location.get(mac, ("unknown", -1))
            known_hosts.append({"ip": ip, "mac": mac, "dpid": dpid, "port": port})

        paths = []
        ips = sorted(self.ip_to_mac.keys())
        for src_ip in ips:
            for dst_ip in ips:
                if src_ip == dst_ip:
                    continue
                src_mac = self.ip_to_mac.get(src_ip)
                dst_mac = self.ip_to_mac.get(dst_ip)
                if not src_mac or not dst_mac:
                    continue
                all_paths = self._all_host_paths(src_mac, dst_mac)
                if all_paths:
                    paths.append(
                        {
                            "src_ip": src_ip,
                            "dst_ip": dst_ip,
                            "paths": all_paths[:2],
                        }
                    )

        return {
            "timestamp": time.time(),
            "summary": dict(self.summary),
            "top_talkers": self.top_talkers,
            "mitigations": list(self.mitigations.values()),
            "known_hosts": known_hosts,
            "paths": paths,
            "datapaths": sorted(self.datapaths.keys()),
        }


    def _start_rest_server(self) -> None:
        controller = self

        class RequestHandler(BaseHTTPRequestHandler):
            def _send_json(self, status: int, payload: Dict[str, Any] | List[Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == f"{BASE_PATH}/state":
                    self._send_json(200, controller.build_state())
                    return
                if parsed.path == f"{BASE_PATH}/mitigations":
                    self._send_json(200, list(controller.mitigations.values()))
                    return
                self._send_json(404, {"status": "error", "message": "Not found"})

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != f"{BASE_PATH}/policy/enforce":
                    self._send_json(404, {"status": "error", "message": "Not found"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length) if length > 0 else b"{}"
                    payload = json.loads(raw.decode("utf-8") or "{}")
                    result = controller.apply_policy(payload)
                    self._send_json(200, result)
                except Exception as exc:
                    self._send_json(400, {"status": "error", "message": str(exc)})

            def log_message(self, fmt: str, *args: Any) -> None:
                LOGGER.debug("REST %s - " + fmt, self.address_string(), *args)

        self._rest_server = ThreadingHTTPServer(("0.0.0.0", REST_PORT), RequestHandler)
        self._rest_server.daemon_threads = True
        self._rest_thread = Thread(target=self._rest_server.serve_forever, daemon=True)
        self._rest_thread.start()

