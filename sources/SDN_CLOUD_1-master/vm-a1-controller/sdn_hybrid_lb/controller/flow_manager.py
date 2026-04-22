from __future__ import annotations

from typing import Optional, Dict, Any

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, arp
from ryu.lib.packet import ether_types


class FlowManager:
    """OpenFlow rule helper for VIP rewriting load balancer."""

    def __init__(self, logger) -> None:
        self.logger = logger

    def add_flow(
        self,
        datapath,
        priority: int,
        match,
        actions,
        idle_timeout: int = 0,
        hard_timeout: int = 0,
        buffer_id: Optional[int] = None,
        send_flow_removed: bool = False,
    ) -> None:
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flags = 0
        if send_flow_removed:
            flags |= ofproto.OFPFF_SEND_FLOW_REM

        if buffer_id is None:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=priority,
                match=match,
                instructions=inst,
                idle_timeout=idle_timeout,
                hard_timeout=hard_timeout,
                flags=flags,
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=priority,
                match=match,
                instructions=inst,
                idle_timeout=idle_timeout,
                hard_timeout=hard_timeout,
                buffer_id=buffer_id,
                flags=flags,
            )
        datapath.send_msg(mod)

    def send_packet_out(self, datapath, in_port: int, actions, data: bytes) -> None:
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    # ---------- VIP / Backend flow install ----------

    def install_vip_rewrite_flows(
        self,
        datapath,
        client_in_port: int,
        client_out_port: int,
        backend_out_port: int,
        vip_ip: str,
        vip_mac: str,
        backend_ip: str,
        backend_mac: str,
        client_ip: str,
        ip_proto: int,
        l4_src: int,
        l4_dst: int,
        idle_timeout: int,
        hard_timeout: int,
        buffer_id: Optional[int],
        raw_packet: bytes,
    ) -> None:
        """Install forward + reverse flows for one 5-tuple.

        Forward:  client -> VIP   becomes client -> backend
        Reverse:  backend -> client becomes VIP -> client
        """
        parser = datapath.ofproto_parser

        # Forward match
        match_fwd_kwargs: Dict[str, Any] = dict(
            in_port=client_in_port,
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=client_ip,
            ipv4_dst=vip_ip,
            ip_proto=ip_proto,
        )
        if ip_proto == 6:  # TCP
            match_fwd_kwargs.update(tcp_src=l4_src, tcp_dst=l4_dst)
        elif ip_proto == 17:  # UDP
            match_fwd_kwargs.update(udp_src=l4_src, udp_dst=l4_dst)
        match_fwd = parser.OFPMatch(**match_fwd_kwargs)

        actions_fwd = [
            parser.OFPActionSetField(ipv4_dst=backend_ip),
            parser.OFPActionSetField(eth_dst=backend_mac),
            parser.OFPActionOutput(backend_out_port),
        ]

        # Reverse match
        match_rev_kwargs: Dict[str, Any] = dict(
            in_port=backend_out_port,
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_src=backend_ip,
            ipv4_dst=client_ip,
            ip_proto=ip_proto,
        )
        if ip_proto == 6:
            match_rev_kwargs.update(tcp_src=l4_dst, tcp_dst=l4_src)
        elif ip_proto == 17:
            match_rev_kwargs.update(udp_src=l4_dst, udp_dst=l4_src)
        match_rev = parser.OFPMatch(**match_rev_kwargs)

        actions_rev = [
            parser.OFPActionSetField(ipv4_src=vip_ip),
            parser.OFPActionSetField(eth_src=vip_mac),
            parser.OFPActionOutput(client_out_port),
        ]

        # Install
        self.add_flow(
            datapath,
            priority=200,
            match=match_fwd,
            actions=actions_fwd,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            buffer_id=buffer_id,
            send_flow_removed=True,
        )
        self.add_flow(
            datapath,
            priority=200,
            match=match_rev,
            actions=actions_rev,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            buffer_id=None,
            send_flow_removed=True,
        )

        # Send first packet out (if needed)
        if raw_packet:
            self.send_packet_out(datapath, client_in_port, actions_fwd, raw_packet)

    # ---------- ARP handling ----------

    def craft_arp_reply(self, src_mac: str, src_ip: str, dst_mac: str, dst_ip: str) -> bytes:
        pkt = packet.Packet()
        pkt.add_protocol(
            ethernet.ethernet(
                ethertype=ether_types.ETH_TYPE_ARP,
                dst=dst_mac,
                src=src_mac,
            )
        )
        pkt.add_protocol(
            arp.arp(
                opcode=arp.ARP_REPLY,
                src_mac=src_mac,
                src_ip=src_ip,
                dst_mac=dst_mac,
                dst_ip=dst_ip,
            )
        )
        pkt.serialize()
        return pkt.data
