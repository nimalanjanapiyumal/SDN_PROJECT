"""Ryu SDN Controller application (Module 1).

This is the entry point invoked by ``ryu-manager``. It wires up:

* Switch handshake & default table-miss flow.
* PacketIn handler that learns hosts and installs basic L2 forwarding rules.
* Topology event listeners that keep ``TopologyManager`` in sync.
* A ``FlowManager`` registration so the REST API can install flow-mods.

The companion REST API (``api/app.py``) imports the same shared state from
``controller_state`` and translates external HTTP requests into flow-mods on
the live datapaths managed here.

Run inside the Mininet/Ryu host with::

    ryu-manager --observe-links sdn_adaptive_cloud_framework.controller.ryu_controller

Tip: pair this with ``api/app.py`` running in another shell so external
clients can submit intents while the controller is forwarding packets.
"""
from __future__ import annotations

# pragma: no cover  (this module only fully executes inside ryu-manager)

import logging
from typing import Any, Dict, Optional

try:
    from ryu.base import app_manager
    from ryu.controller import ofp_event
    from ryu.controller.handler import (
        CONFIG_DISPATCHER,
        MAIN_DISPATCHER,
        DEAD_DISPATCHER,
        set_ev_cls,
    )
    from ryu.lib.packet import packet, ethernet, ipv4, arp
    from ryu.ofproto import ofproto_v1_3
    from ryu.topology import event as topo_event
    _RYU_AVAILABLE = True
except Exception:  # pragma: no cover - module loadable without Ryu
    app_manager = None  # type: ignore[assignment]
    _RYU_AVAILABLE = False

from .controller_state import get_state

LOG = logging.getLogger("sdn_framework.ryu_controller")


if _RYU_AVAILABLE:

    class AdaptiveCloudController(app_manager.RyuApp):
        """Main Ryu app for the Adaptive Cloud SDN framework."""

        OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.state = get_state()
            self.mac_to_port: Dict[int, Dict[str, int]] = {}
            LOG.info("AdaptiveCloudController initialised")

        # ---- switch lifecycle --------------------------------------------------
        @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
        def _switch_features_handler(self, ev: Any) -> None:
            datapath = ev.msg.datapath
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser

            self.state.flow_manager.register_datapath(datapath)
            self.state.topology.add_switch(int(datapath.id))

            # Table-miss: send unmatched packets to the controller.
            match = parser.OFPMatch()
            actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(
                datapath=datapath, priority=0, match=match, instructions=inst
            )
            datapath.send_msg(mod)
            LOG.info("Switch %s connected; table-miss installed", datapath.id)

        @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
        def _state_change_handler(self, ev: Any) -> None:
            datapath = ev.datapath
            if ev.state == DEAD_DISPATCHER and datapath is not None:
                self.state.flow_manager.unregister_datapath(int(datapath.id))
                self.state.topology.remove_switch(int(datapath.id))
                LOG.info("Switch %s disconnected", datapath.id)

        # ---- packet-in / forwarding -------------------------------------------
        @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
        def _packet_in_handler(self, ev: Any) -> None:
            msg = ev.msg
            datapath = msg.datapath
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            in_port = msg.match["in_port"]
            dpid = int(datapath.id)

            pkt = packet.Packet(msg.data)
            eth = pkt.get_protocol(ethernet.ethernet)
            if eth is None:
                return

            src_ip: Optional[str] = None
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt is not None:
                src_ip = ip_pkt.src
            else:
                arp_pkt = pkt.get_protocol(arp.arp)
                if arp_pkt is not None:
                    src_ip = arp_pkt.src_ip

            self.state.hosts.upsert(eth.src, dpid=dpid, port=in_port, ip=src_ip)
            self.mac_to_port.setdefault(dpid, {})[eth.src] = in_port

            out_port = self.mac_to_port[dpid].get(eth.dst, ofproto.OFPP_FLOOD)
            actions = [parser.OFPActionOutput(out_port)]

            # Install reactive forwarding rule when destination is known.
            if out_port != ofproto.OFPP_FLOOD:
                match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src)
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(
                    datapath=datapath,
                    priority=10,
                    match=match,
                    instructions=inst,
                    idle_timeout=30,
                    hard_timeout=120,
                )
                datapath.send_msg(mod)

            data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=data,
            )
            datapath.send_msg(out)

        # ---- topology events --------------------------------------------------
        @set_ev_cls(topo_event.EventLinkAdd)
        def _link_add(self, ev: Any) -> None:
            link = ev.link
            self.state.topology.add_link(
                int(link.src.dpid), int(link.src.port_no),
                int(link.dst.dpid), int(link.dst.port_no),
            )

        @set_ev_cls(topo_event.EventLinkDelete)
        def _link_del(self, ev: Any) -> None:
            link = ev.link
            self.state.topology.remove_link(
                int(link.src.dpid), int(link.src.port_no),
                int(link.dst.dpid), int(link.dst.port_no),
            )

        @set_ev_cls(topo_event.EventSwitchEnter)
        def _switch_enter(self, ev: Any) -> None:
            sw = ev.switch
            self.state.topology.add_switch(
                int(sw.dp.id), {int(p.port_no) for p in sw.ports}
            )

        @set_ev_cls(topo_event.EventSwitchLeave)
        def _switch_leave(self, ev: Any) -> None:
            self.state.topology.remove_switch(int(ev.switch.dp.id))

else:  # pragma: no cover

    class AdaptiveCloudController:  # type: ignore[no-redef]
        """Stand-in used when Ryu isn't installed.

        Importing this module without Ryu lets the REST API and unit tests
        load it without crashing. Real datapath handling only happens inside
        ``ryu-manager``.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError(
                "Ryu is not installed in this environment. Run this controller "
                "from a Ryu/Mininet host using `ryu-manager`."
            )


__all__ = ["AdaptiveCloudController"]
