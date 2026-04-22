
from __future__ import annotations

import argparse
import shlex
import time
from typing import Iterable, List

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.topo import Topo


class AdaptiveCloudTopo(Topo):
    def build(self) -> None:
        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", protocols="OpenFlow13")
        s4 = self.addSwitch("s4", protocols="OpenFlow13")

        h1 = self.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = self.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
        h3 = self.addHost("h3", ip="10.0.0.3/24", mac="00:00:00:00:00:03")
        h4 = self.addHost("h4", ip="10.0.0.4/24", mac="00:00:00:00:00:04")

        # Host-facing links.
        self.addLink(h1, s1, cls=TCLink, bw=100, delay="1ms")
        self.addLink(h2, s1, cls=TCLink, bw=100, delay="1ms")
        self.addLink(h3, s1, cls=TCLink, bw=100, delay="1ms")
        self.addLink(h4, s4, cls=TCLink, bw=100, delay="1ms")

        # Redundant SDN fabric.
        self.addLink(s1, s2, cls=TCLink, bw=20, delay="5ms")
        self.addLink(s2, s4, cls=TCLink, bw=20, delay="5ms")
        self.addLink(s1, s3, cls=TCLink, bw=20, delay="5ms")
        self.addLink(s3, s4, cls=TCLink, bw=20, delay="5ms")
        self.addLink(s2, s3, cls=TCLink, bw=15, delay="3ms")


def _start_background(host, label: str, command: str) -> None:
    logfile = f"/tmp/{host.name}_{label}.log"
    safe = shlex.quote(command)
    info(f"*** {host.name}: starting {label}\n")
    host.cmd(f"nohup bash -lc {safe} >{logfile} 2>&1 &")


def _cleanup_host_processes(net: Mininet) -> None:
    for host in net.hosts:
        host.cmd("pkill -9 -f 'python3 -m http.server' || true")
        host.cmd("pkill -9 -f 'iperf3 -s' || true")
        host.cmd("pkill -9 -f 'iperf3 -c' || true")
        host.cmd("pkill -9 -f 'socket.SOCK_DGRAM' || true")
        host.cmd("pkill -9 -f '/dev/tcp/10.0.0.4' || true")


def _start_services(net: Mininet) -> None:
    h4 = net.get("h4")
    _start_background(h4, "http", "python3 -m http.server 8000")
    _start_background(h4, "iperf", "iperf3 -s")


def _warmup(net: Mininet) -> None:
    h1, h4 = net.get("h1", "h4")
    info("*** Warming up ARP/ICMP state\n")
    h1.cmd("ping -c 2 10.0.0.4 >/dev/null 2>&1")
    net.ping([h1, h4], timeout="1")


def _start_normal(net: Mininet, duration: int) -> None:
    h1, h2 = net.get("h1", "h2")
    _start_background(h1, "normal_iperf", f"iperf3 -c 10.0.0.4 -t {duration} -b 6M")
    _start_background(
        h2,
        "normal_http",
        f"while true; do curl -s http://10.0.0.4:8000 >/dev/null; sleep 1; done",
    )


def _start_congestion(net: Mininet, duration: int) -> None:
    h1, h2 = net.get("h1", "h2")
    _start_background(h1, "congestion_h1", f"iperf3 -c 10.0.0.4 -u -b 18M -t {duration}")
    _start_background(h2, "congestion_h2", f"iperf3 -c 10.0.0.4 -u -b 18M -t {duration}")


def _start_ddos(net: Mininet, duration: int) -> None:
    h3 = net.get("h3")
    attack_script = f"""
python3 - <<'PY'
import os
import random
import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
payload = os.urandom(1200)
end = time.time() + {duration}
while time.time() < end:
    sock.sendto(payload, ('10.0.0.4', random.randint(1024, 65535)))
PY
"""
    _start_background(h3, "ddos", attack_script)


def _start_port_scan(net: Mininet, duration: int) -> None:
    h3 = net.get("h3")
    scan_script = f"""
python3 - <<'PY'
import socket
import time

end = time.time() + {duration}
ports = list(range(1, 4096))
idx = 0
while time.time() < end:
    port = ports[idx % len(ports)]
    idx += 1
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.02)
    try:
        s.connect(('10.0.0.4', port))
    except Exception:
        pass
    finally:
        s.close()
PY
"""
    _start_background(h3, "portscan", scan_script)


def start_scenario(net: Mininet, scenario: str, duration: int) -> None:
    scenario = scenario.lower()
    if scenario == "idle":
        info("*** Idle scenario selected; only services are running\n")
        return
    if scenario == "normal":
        _start_normal(net, duration)
        return
    if scenario == "congestion":
        _start_congestion(net, duration)
        return
    if scenario == "ddos":
        _start_ddos(net, duration)
        return
    if scenario == "port_scan":
        _start_port_scan(net, duration)
        return
    if scenario == "mixed":
        _start_normal(net, duration)
        _start_background(
            net.get("h2"),
            "staged_congestion",
            f"sleep 10 && iperf3 -c 10.0.0.4 -u -b 18M -t {max(duration - 10, 10)}",
        )
        _start_background(
            net.get("h3"),
            "staged_scan",
            f"sleep 20 && python3 - <<'PY'\n"
            f"import socket,time\n"
            f"end=time.time()+{max(duration - 20, 10)}\n"
            f"ports=list(range(1,2048))\n"
            f"i=0\n"
            f"while time.time()<end:\n"
            f"    port=ports[i%len(ports)]\n"
            f"    i+=1\n"
            f"    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)\n"
            f"    s.settimeout(0.02)\n"
            f"    try:\n"
            f"        s.connect(('10.0.0.4', port))\n"
            f"    except Exception:\n"
            f"        pass\n"
            f"    finally:\n"
            f"        s.close()\n"
            f"PY",
        )
        _start_background(
            net.get("h3"),
            "staged_ddos",
            f"sleep 35 && python3 - <<'PY'\n"
            f"import os,random,socket,time\n"
            f"sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\n"
            f"payload=os.urandom(1200)\n"
            f"end=time.time()+{max(duration - 35, 10)}\n"
            f"while time.time()<end:\n"
            f"    sock.sendto(payload,('10.0.0.4', random.randint(1024,65535)))\n"
            f"PY",
        )
        return
    raise ValueError(f"Unknown scenario: {scenario}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adaptive cloud SDN Mininet topology")
    parser.add_argument("--controller-ip", default="127.0.0.1", help="Ryu controller IP.")
    parser.add_argument("--controller-port", type=int, default=6653, help="OpenFlow controller port.")
    parser.add_argument(
        "--scenario",
        default="mixed",
        choices=["idle", "normal", "congestion", "ddos", "port_scan", "mixed"],
        help="Traffic scenario to launch.",
    )
    parser.add_argument("--duration", type=int, default=90, help="Traffic duration in seconds.")
    parser.add_argument("--cli", action="store_true", help="Drop into Mininet CLI after startup.")
    parser.add_argument("--foreground", action="store_true", help="Keep running until duration expires.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    topo = AdaptiveCloudTopo()
    net = Mininet(
        topo=topo,
        controller=None,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink,
        switch=OVSKernelSwitch,
    )
    controller = RemoteController("c0", ip=args.controller_ip, port=args.controller_port)
    net.addController(controller)

    try:
        info("*** Starting Mininet topology\n")
        net.start()
        time.sleep(4)
        _cleanup_host_processes(net)
        _start_services(net)
        time.sleep(2)
        _warmup(net)
        start_scenario(net, args.scenario, args.duration)
        info(f"*** Scenario '{args.scenario}' launched for {args.duration} seconds\n")

        if args.cli:
            CLI(net)
        elif args.foreground:
            time.sleep(args.duration)
        else:
            time.sleep(args.duration)
    finally:
        info("*** Cleaning up host background processes\n")
        try:
            _cleanup_host_processes(net)
        except Exception:
            pass
        info("*** Stopping Mininet\n")
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    main()
