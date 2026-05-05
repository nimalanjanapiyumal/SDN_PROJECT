"""Mininet topology for the SDN Adaptive Cloud Framework testbed.

Run on the Ubuntu/Mininet host (the controller is expected on 127.0.0.1:6633)::

    sudo python3 -m sdn_adaptive_cloud_framework.topology.mininet_topology \\
        --controller 127.0.0.1 --port 6633

The default layout is a small three-tier cloud:

* 1 core switch (s1)
* 2 distribution switches (s2, s3)
* 6 hosts split across web/app/db/admin/untrusted segments,
  matching the segments used by the micro-segmentation module.
"""
from __future__ import annotations

import argparse
import sys

try:
    from mininet.net import Mininet
    from mininet.node import RemoteController, OVSSwitch
    from mininet.cli import CLI
    from mininet.log import setLogLevel
    from mininet.topo import Topo
    _MININET_AVAILABLE = True
except Exception:  # pragma: no cover - module loadable without Mininet
    Mininet = None  # type: ignore[assignment]
    RemoteController = None  # type: ignore[assignment]
    OVSSwitch = None  # type: ignore[assignment]
    CLI = None  # type: ignore[assignment]
    setLogLevel = lambda *a, **k: None  # type: ignore[assignment]
    Topo = object  # type: ignore[assignment, misc]
    _MININET_AVAILABLE = False


SEGMENT_HOSTS = {
    "web": [("h1", "10.0.1.1/24")],
    "app": [("h2", "10.0.2.1/24"), ("h3", "10.0.2.2/24")],
    "db": [("h4", "10.0.3.1/24")],
    "admin": [("h5", "10.0.4.1/24")],
    "untrusted": [("h6", "10.0.9.1/24")],
}


class AdaptiveCloudTopo(Topo):  # type: ignore[misc]
    """Three-tier cloud topology mirroring the segments used by Module 7."""

    def build(self) -> None:  # pragma: no cover - executed inside Mininet
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")
        self.addLink(s1, s2)
        self.addLink(s1, s3)

        host_id = 0
        for segment, members in SEGMENT_HOSTS.items():
            for name, ip in members:
                host = self.addHost(name, ip=ip)
                attach = s2 if host_id % 2 == 0 else s3
                self.addLink(host, attach)
                host_id += 1


def run(controller_ip: str = "127.0.0.1", controller_port: int = 6633) -> None:  # pragma: no cover
    if not _MININET_AVAILABLE:
        print("Mininet is not installed in this environment.", file=sys.stderr)
        sys.exit(1)
    setLogLevel("info")
    topo = AdaptiveCloudTopo()
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=lambda name: RemoteController(name, ip=controller_ip, port=controller_port),
        autoSetMacs=True,
    )
    net.start()
    print("Adaptive Cloud topology running. CTRL-D in CLI to stop.")
    CLI(net)
    net.stop()


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(description="Adaptive Cloud Mininet topology")
    parser.add_argument("--controller", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6633)
    args = parser.parse_args()
    run(args.controller, args.port)


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["AdaptiveCloudTopo", "SEGMENT_HOSTS", "run"]
