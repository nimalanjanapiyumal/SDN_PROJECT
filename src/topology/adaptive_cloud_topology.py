
from __future__ import annotations

import argparse
import json
import os
import shlex
import threading
import time
import urllib.error
import urllib.request
from typing import Iterable, List

from mininet.cli import CLI
from mininet.link import Link, TCLink
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.topo import Topo

API_URL = os.environ.get("ADAPTIVE_API_URL", "http://127.0.0.1:8080").rstrip("/")


class AdaptiveCloudTopo(Topo):
    def build(self, link_mode: str = "basic") -> None:
        link_cls = TCLink if str(link_mode).lower() == "shaped" else Link
        link_kwargs = (lambda bw, delay: {"cls": link_cls, "bw": bw, "delay": delay}) if link_cls is TCLink else (lambda bw, delay: {"cls": link_cls})

        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", protocols="OpenFlow13")
        s4 = self.addSwitch("s4", protocols="OpenFlow13")

        h1 = self.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = self.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
        h3 = self.addHost("h3", ip="10.0.0.3/24", mac="00:00:00:00:00:03")
        h4 = self.addHost("h4", ip="10.0.0.4/24", mac="00:00:00:00:00:04")

        # Host-facing links.
        self.addLink(h1, s1, **link_kwargs(100, "1ms"))
        self.addLink(h2, s1, **link_kwargs(100, "1ms"))
        self.addLink(h3, s1, **link_kwargs(100, "1ms"))
        self.addLink(h4, s4, **link_kwargs(100, "1ms"))

        # Linear SDN fabric to prevent broadcast storms.
        self.addLink(s1, s2, **link_kwargs(20, "5ms"))
        self.addLink(s2, s3, **link_kwargs(15, "3ms"))
        self.addLink(s3, s4, **link_kwargs(20, "5ms"))
        # Redundant links disabled to prevent loops with basic learning switch
        # self.addLink(s2, s4, **link_kwargs(20, "5ms"))
        # self.addLink(s1, s3, **link_kwargs(20, "5ms"))


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


def _post_json(path: str, payload: dict) -> None:
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2.5):
            return
    except urllib.error.URLError:
        return
    except Exception:
        return


def _notify_runtime(event_type: str, message: str, metadata: dict | None = None, severity: str = "info") -> None:
    _post_json(
        "/api/v1/sdn/events",
        {
            "event_type": event_type,
            "source": "mininet",
            "severity": severity,
            "message": message,
            "metadata": metadata or {},
        },
    )


def _notify_security_alert(src_ip: str, threat_type: str, signature: str, severity: int = 1) -> None:
    _post_json(
        "/api/v1/component-4/cti/alert",
        {
            "src_ip": src_ip,
            "signature": signature,
            "severity": severity,
            "threat_type": threat_type,
        },
    )


def _schedule_callback(delay_sec: int, callback) -> None:
    timer = threading.Timer(delay_sec, callback)
    timer.daemon = True
    timer.start()


def _publish_topology_snapshot() -> None:
    _notify_runtime(
        "topology_snapshot",
        "Mininet topology is live and synchronized with the GUI.",
        metadata={
            "switches": [
                {"name": "s1", "role": "edge", "state": "live"},
                {"name": "s2", "role": "fabric", "state": "live"},
                {"name": "s3", "role": "fabric", "state": "live"},
                {"name": "s4", "role": "edge", "state": "live"},
            ],
            "hosts": [
                {"name": "h1", "ip": "10.0.0.1", "role": "traffic source", "switch": "s1"},
                {"name": "h2", "ip": "10.0.0.2", "role": "traffic source", "switch": "s1"},
                {"name": "h3", "ip": "10.0.0.3", "role": "scanner / attack", "switch": "s1"},
                {"name": "h4", "ip": "10.0.0.4", "role": "service sink", "switch": "s4"},
            ],
            "services": [
                {"name": "service-sink", "ip": "10.0.0.4", "state": "live", "note": "http + iperf3"},
            ],
            "links": [
                {"from": "ryu", "to": "s1", "kind": "control"},
                {"from": "ryu", "to": "s2", "kind": "control"},
                {"from": "ryu", "to": "s3", "kind": "control"},
                {"from": "ryu", "to": "s4", "kind": "control"},
                {"from": "s1", "to": "s2", "kind": "fabric"},
                {"from": "s2", "to": "s3", "kind": "fabric"},
                {"from": "s3", "to": "s4", "kind": "fabric"},
            ],
        },
    )


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
    _notify_runtime("traffic_started", "Normal application traffic is running across the Mininet lab.", {"scenario": "normal"})
    _start_background(h1, "normal_iperf", f"iperf3 -c 10.0.0.4 -t {duration} -b 6M")
    _start_background(
        h2,
        "normal_http",
        f"while true; do curl -s http://10.0.0.4:8000 >/dev/null; sleep 1; done",
    )


def _start_congestion(net: Mininet, duration: int) -> None:
    h1, h2 = net.get("h1", "h2")
    _notify_runtime("traffic_started", "Congestion scenario launched inside Mininet.", {"scenario": "congestion"}, severity="warning")
    _start_background(h1, "congestion_h1", f"iperf3 -c 10.0.0.4 -u -b 18M -t {duration}")
    _start_background(h2, "congestion_h2", f"iperf3 -c 10.0.0.4 -u -b 18M -t {duration}")


def _start_ddos(net: Mininet, duration: int) -> None:
    h3 = net.get("h3")
    _notify_runtime("attack_started", "DDoS traffic started from h3 toward the service sink.", {"scenario": "ddos", "attack_type": "DDoS", "src_ip": "10.0.0.3", "dst_ip": "10.0.0.4"}, severity="critical")
    _notify_security_alert("10.0.0.3", "DDoS", "Mininet DDoS traffic detected", severity=1)
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
    _notify_runtime("attack_started", "Port scanning started from h3 toward the service sink.", {"scenario": "port_scan", "attack_type": "Port Scan", "src_ip": "10.0.0.3", "dst_ip": "10.0.0.4"}, severity="warning")
    _notify_security_alert("10.0.0.3", "Port Scan", "Mininet port scan detected", severity=2)
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
        _notify_runtime("traffic_started", "Idle service-only Mininet scenario is active.", {"scenario": "idle"})
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
        _notify_runtime("traffic_started", "Mixed Mininet scenario started. Congestion and attacks will be staged.", {"scenario": "mixed"}, severity="warning")
        _start_background(
            net.get("h2"),
            "staged_congestion",
            f"sleep 10 && iperf3 -c 10.0.0.4 -u -b 18M -t {max(duration - 10, 10)}",
        )
        _schedule_callback(10, lambda: _notify_runtime("traffic_started", "Staged congestion phase is now active.", {"scenario": "mixed", "phase": "congestion"}, severity="warning"))
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
        _schedule_callback(20, lambda: (
            _notify_runtime("attack_started", "Staged port scan phase is now active.", {"scenario": "mixed", "phase": "port_scan", "attack_type": "Port Scan", "src_ip": "10.0.0.3", "dst_ip": "10.0.0.4"}, severity="warning"),
            _notify_security_alert("10.0.0.3", "Port Scan", "Mixed scenario port scan detected", severity=2)
        ))
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
        _schedule_callback(35, lambda: (
            _notify_runtime("attack_started", "Staged DDoS phase is now active.", {"scenario": "mixed", "phase": "ddos", "attack_type": "DDoS", "src_ip": "10.0.0.3", "dst_ip": "10.0.0.4"}, severity="critical"),
            _notify_security_alert("10.0.0.3", "DDoS", "Mixed scenario DDoS detected", severity=1)
        ))
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
    parser.add_argument("--link-mode", choices=["basic", "shaped"], default="basic", help="Use basic links for stable demos or TCLink shaping for bandwidth/delay emulation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    topo = AdaptiveCloudTopo(link_mode=args.link_mode)
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
        _publish_topology_snapshot()
        time.sleep(4)
        _cleanup_host_processes(net)
        _start_services(net)
        time.sleep(2)
        _warmup(net)
        start_scenario(net, args.scenario, args.duration)
        info(f"*** Scenario '{args.scenario}' launched for {args.duration} seconds\n")

        if args.cli:
            info("*** Example CLI command: h1 iperf3 -c 10.0.0.4 -t 5\n")
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
