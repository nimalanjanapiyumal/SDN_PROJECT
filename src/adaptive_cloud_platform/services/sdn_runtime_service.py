from __future__ import annotations

import os
import platform
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


class SdnRuntimeService:
    """Runtime helper for Linux-based Ryu/Mininet/Grafana/Prometheus operations."""

    def __init__(self, repo_root: str | Path, api_url: str, metrics_port: int = 9108) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.api_url = api_url.rstrip("/")
        self.metrics_port = int(metrics_port)
        self.logs_dir = self.repo_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.lab_log_path = self.logs_dir / "sdn_lab.log"
        self.ryu_log_path = self.logs_dir / "ryu_integrated.log"
        self.lab_process: Optional[subprocess.Popen[str]] = None
        self.lab_started_at: Optional[float] = None
        self.lab_last_command: Optional[str] = None
        self.lab_last_error: Optional[str] = None
        self.lab_last_result: Optional[Dict[str, Any]] = None
        self.monitoring_last_command: Optional[str] = None
        self.monitoring_last_result: Optional[Dict[str, Any]] = None

    def status(
        self,
        component_one: Optional[Dict[str, Any]] = None,
        component_two: Optional[Dict[str, Any]] = None,
        component_three: Optional[Dict[str, Any]] = None,
        component_four: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        env = self._environment()
        commands = self.command_catalog()
        monitoring = self._monitoring_status(env)
        openflow = self._openflow_status(component_one, component_three, component_four)
        topology = self._topology_status(component_one, component_four, openflow, env, monitoring)
        lab = self._lab_status(env, commands)
        return {
            "environment": env,
            "lab": lab,
            "monitoring": monitoring,
            "openflow": openflow,
            "topology": topology,
            "commands": commands,
            "views": monitoring["views"],
        }

    def start_lab(
        self,
        scenario: str = "mixed",
        duration_sec: int = 90,
        interactive: bool = False,
        link_mode: str = "basic",
        start_monitoring: bool = False,
    ) -> Dict[str, Any]:
        env = self._environment()
        command = self._lab_command(scenario, duration_sec, interactive, link_mode)
        self.lab_last_command = command

        if start_monitoring:
            self.monitoring_last_result = self.start_monitoring()

        if not env["linux_runtime"]:
            self.lab_last_error = "Linux runtime required for Mininet and Ryu execution."
            self.lab_last_result = {
                "launched": False,
                "status": "manual_required",
                "reason": self.lab_last_error,
                "command": command,
            }
            return self.lab_last_result

        if not env["tool_paths"].get("ryu-manager") or not env["tool_paths"].get("mn"):
            self.lab_last_error = "Missing ryu-manager or mn on the current Linux runtime."
            self.lab_last_result = {
                "launched": False,
                "status": "dependency_missing",
                "reason": self.lab_last_error,
                "command": command,
            }
            return self.lab_last_result

        if self.lab_process and self.lab_process.poll() is None:
            return {
                "launched": False,
                "status": "already_running",
                "pid": self.lab_process.pid,
                "command": self.lab_last_command,
            }

        with self.lab_log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting SDN lab: {command}\n")

        log_handle = self.lab_log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(
            ["bash", str(self.repo_root / "scripts" / "run_integrated_sdn_lab.sh"), scenario, str(duration_sec), "cli" if interactive else "headless", link_mode],
            cwd=str(self.repo_root),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
            env=self._process_env(),
        )
        self.lab_process = process
        self.lab_started_at = time.time()
        time.sleep(1.0)
        if process.poll() is not None:
            self.lab_last_error = self._read_tail(self.lab_log_path)
            self.lab_last_result = {
                "launched": False,
                "status": "exited_early",
                "exit_code": process.returncode,
                "command": command,
                "log_tail": self.lab_last_error,
            }
            return self.lab_last_result

        self.lab_last_error = None
        self.lab_last_result = {
            "launched": True,
            "status": "running",
            "pid": process.pid,
            "command": command,
            "started_at": self.lab_started_at,
        }
        return self.lab_last_result

    def stop_lab(self) -> Dict[str, Any]:
        process = self.lab_process
        if process is None or process.poll() is not None:
            self.lab_process = None
            return {"stopped": False, "status": "not_running"}

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                process.kill()
        self.lab_process = None
        self.lab_last_result = {"stopped": True, "status": "stopped", "stopped_at": time.time()}
        return self.lab_last_result

    def start_monitoring(self) -> Dict[str, Any]:
        command = "docker compose up -d prometheus grafana"
        self.monitoring_last_command = command
        env = self._environment()
        if not env["tool_paths"].get("docker"):
            self.monitoring_last_result = {
                "started": False,
                "status": "manual_required",
                "reason": "docker is not available on this runtime",
                "command": command,
            }
            return self.monitoring_last_result

        result = subprocess.run(
            ["docker", "compose", "up", "-d", "prometheus", "grafana"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.monitoring_last_result = {
            "started": result.returncode == 0,
            "status": "running" if result.returncode == 0 else "failed",
            "command": command,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }
        return self.monitoring_last_result

    def stop_monitoring(self) -> Dict[str, Any]:
        command = "docker compose stop prometheus grafana"
        self.monitoring_last_command = command
        env = self._environment()
        if not env["tool_paths"].get("docker"):
            return {
                "stopped": False,
                "status": "manual_required",
                "reason": "docker is not available on this runtime",
                "command": command,
            }

        result = subprocess.run(
            ["docker", "compose", "stop", "prometheus", "grafana"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=90,
        )
        return {
            "stopped": result.returncode == 0,
            "status": "stopped" if result.returncode == 0 else "failed",
            "command": command,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }

    def shutdown(self) -> None:
        if self.lab_process and self.lab_process.poll() is None:
            self.stop_lab()

    def command_catalog(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Start SDN Lab",
                "category": "sdn",
                "command": self._lab_command("mixed", 90, False, "basic"),
                "description": "Headless Mininet + Ryu run for the integrated controller and optimizer.",
            },
            {
                "name": "Start SDN Lab (CLI)",
                "category": "sdn",
                "command": self._lab_command("mixed", 90, True, "basic"),
                "description": "Interactive Mininet CLI with the integrated Ryu controller attached.",
            },
            {
                "name": "Validate OpenFlow",
                "category": "sdn",
                "command": "ovs-ofctl -O OpenFlow13 dump-flows s1",
                "description": "Inspect live OpenFlow rules on the first switch.",
            },
            {
                "name": "Start Monitoring",
                "category": "monitoring",
                "command": "docker compose up -d prometheus grafana",
                "description": "Boot Prometheus and Grafana for the integrated dashboard stack.",
            },
            {
                "name": "Stop Monitoring",
                "category": "monitoring",
                "command": "docker compose stop prometheus grafana",
                "description": "Stop the monitoring services without destroying configuration.",
            },
            {
                "name": "Inspect Controller Log",
                "category": "debug",
                "command": f"tail -n 80 {self.ryu_log_path}",
                "description": "Read the most recent integrated Ryu controller messages.",
            },
            {
                "name": "Inspect Lab Log",
                "category": "debug",
                "command": f"tail -n 80 {self.lab_log_path}",
                "description": "Read the most recent Mininet and scenario launcher log lines.",
            },
        ]

    def _environment(self) -> Dict[str, Any]:
        system_name = platform.system()
        release = platform.release()
        tool_names = ["bash", "docker", "ryu-manager", "mn", "ovs-ofctl", "ovs-vsctl", "iperf3", "suricata"]
        tool_paths = {name: shutil.which(name) for name in tool_names}
        return {
            "platform": system_name,
            "release": release,
            "linux_runtime": system_name.lower() == "linux",
            "wsl_runtime": "microsoft" in release.lower(),
            "tool_paths": tool_paths,
            "repo_root": str(self.repo_root),
            "logs_dir": str(self.logs_dir),
        }

    def _monitoring_status(self, env: Dict[str, Any]) -> Dict[str, Any]:
        api_probe = self._probe_http(f"{self.api_url}/healthz")
        metrics_probe = self._probe_http(f"http://127.0.0.1:{self.metrics_port}/metrics")
        prometheus_probe = self._probe_http("http://127.0.0.1:9090/-/ready")
        grafana_probe = self._probe_http("http://127.0.0.1:3000/api/health")
        return {
            "docker_available": bool(env["tool_paths"].get("docker")),
            "metrics_exporter": metrics_probe,
            "api": api_probe,
            "prometheus": prometheus_probe,
            "grafana": grafana_probe,
            "views": [
                {
                    "name": "Prometheus",
                    "url": "http://127.0.0.1:9090/",
                    "reachable": bool(prometheus_probe.get("reachable")),
                    "status": "live" if prometheus_probe.get("reachable") else "unavailable",
                },
                {
                    "name": "Grafana",
                    "url": "http://127.0.0.1:3000/",
                    "reachable": bool(grafana_probe.get("reachable")),
                    "status": "live" if grafana_probe.get("reachable") else "unavailable",
                },
                {
                    "name": "Metrics Exporter",
                    "url": f"http://127.0.0.1:{self.metrics_port}/metrics",
                    "reachable": bool(metrics_probe.get("reachable")),
                    "status": "live" if metrics_probe.get("reachable") else "unavailable",
                },
                {
                    "name": "API Docs",
                    "url": f"{self.api_url}/docs",
                    "reachable": bool(api_probe.get("reachable")),
                    "status": "live" if api_probe.get("reachable") else "unavailable",
                },
            ],
        }

    def _lab_status(self, env: Dict[str, Any], commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        process = self.lab_process
        running = bool(process and process.poll() is None)
        controller_probe = self._probe_tcp("127.0.0.1", 6653)
        return {
            "running": running,
            "interactive": False,
            "started_at": self.lab_started_at,
            "uptime_sec": round(time.time() - self.lab_started_at, 1) if running and self.lab_started_at else None,
            "pid": process.pid if running and process else None,
            "exit_code": None if running or process is None else process.returncode,
            "controller_probe": controller_probe,
            "supported": env["linux_runtime"] and bool(env["tool_paths"].get("ryu-manager")) and bool(env["tool_paths"].get("mn")),
            "last_command": self.lab_last_command or commands[0]["command"],
            "last_error": self.lab_last_error,
            "last_result": self.lab_last_result,
            "lab_log_path": str(self.lab_log_path),
            "ryu_log_path": str(self.ryu_log_path),
            "lab_log_tail": self._read_tail(self.lab_log_path),
            "ryu_log_tail": self._read_tail(self.ryu_log_path),
        }

    def _openflow_status(
        self,
        component_one: Optional[Dict[str, Any]],
        component_three: Optional[Dict[str, Any]],
        component_four: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        c1_rules = list((component_one or {}).get("flow_rules") or [])[-12:]
        c3_rules = list((component_three or {}).get("recent_rules") or [])[-12:]
        c4_rules = list((component_four or {}).get("active_rules") or [])[-12:]
        flow_entries: List[Dict[str, Any]] = []
        switch_counts: Dict[str, int] = {}

        for flow in c1_rules:
            switch_name = self._normalize_switch(flow.get("dpid"))
            switch_counts[switch_name] = switch_counts.get(switch_name, 0) + 1
            flow_entries.append({
                "id": flow.get("id"),
                "component": "component-1",
                "switch": switch_name,
                "action": flow.get("algorithm") or "forward",
                "summary": f"{flow.get('client_ip')}:{flow.get('client_port')} -> {flow.get('backend_ip')}:{flow.get('vip_port')}",
                "priority": flow.get("priority"),
            })

        for rule in c3_rules:
            switch_name = self._normalize_switch(rule.get("switch"))
            switch_counts[switch_name] = switch_counts.get(switch_name, 0) + 1
            flow_entries.append({
                "id": rule.get("id"),
                "component": "component-3",
                "switch": switch_name,
                "action": rule.get("semantic_action") or rule.get("action") or "intent_rule",
                "summary": self._match_summary(rule.get("match") or {}),
                "priority": rule.get("priority"),
            })

        for rule in c4_rules:
            switch_name = self._normalize_switch(rule.get("dpid") or rule.get("switch") or "fabric")
            switch_counts[switch_name] = switch_counts.get(switch_name, 0) + 1
            flow_entries.append({
                "id": rule.get("id"),
                "component": "component-4",
                "switch": switch_name,
                "action": rule.get("action") or "security_rule",
                "summary": self._match_summary(rule.get("match") or {}) or str(rule.get("subject") or "policy subject"),
                "priority": rule.get("priority"),
            })

        return {
            "total_rules": len(flow_entries),
            "component_counts": {
                "component_1": len(c1_rules),
                "component_3": len(c3_rules),
                "component_4": len(c4_rules),
            },
            "switch_counts": switch_counts,
            "rules": flow_entries[-24:],
        }

    def _topology_status(
        self,
        component_one: Optional[Dict[str, Any]],
        component_four: Optional[Dict[str, Any]],
        openflow: Dict[str, Any],
        env: Dict[str, Any],
        monitoring: Dict[str, Any],
    ) -> Dict[str, Any]:
        backends = list((component_one or {}).get("backends") or [])
        security_rules = list((component_four or {}).get("active_rules") or [])
        blocked_subjects = {str(rule.get("subject") or "") for rule in security_rules if str(rule.get("action") or "").lower() in {"block", "quarantine", "temporary_block"}}
        controller_live = bool(self._probe_tcp("127.0.0.1", 6653).get("reachable"))
        switch_counts = openflow.get("switch_counts") or {}

        services = [
            {
                "name": backend.get("name"),
                "ip": backend.get("ip"),
                "state": "isolated" if str(backend.get("ip") or "") in blocked_subjects or backend.get("optimizer_status") == "offline" else "live",
                "note": backend.get("security_reason") or backend.get("optimizer_status") or "available",
            }
            for backend in backends
        ]

        hosts = [
            {"name": "client-1", "ip": "10.0.0.1", "role": "traffic source", "switch": "s1"},
            {"name": "client-2", "ip": "10.0.0.2", "role": "traffic source", "switch": "s1"},
            {"name": "client-3", "ip": "10.0.0.3", "role": "scanner / load", "switch": "s1"},
            {"name": "service-sink", "ip": "10.0.0.4", "role": "Mininet app target", "switch": "s4"},
        ]

        return {
            "controller": {
                "name": "Ryu Integrated Controller",
                "state": "live" if controller_live else "offline",
                "port": 6653,
                "rules": openflow.get("total_rules", 0),
            },
            "switches": [
                {"name": "s1", "role": "edge", "rules": switch_counts.get("s1", 0), "state": "live" if controller_live else "idle"},
                {"name": "s2", "role": "fabric", "rules": switch_counts.get("s2", 0), "state": "live" if controller_live else "idle"},
                {"name": "s3", "role": "fabric", "rules": switch_counts.get("s3", 0), "state": "live" if controller_live else "idle"},
                {"name": "s4", "role": "edge", "rules": switch_counts.get("s4", 0), "state": "live" if controller_live else "idle"},
            ],
            "hosts": hosts,
            "services": services,
            "links": [
                {"from": "ryu", "to": "s1", "kind": "control"},
                {"from": "ryu", "to": "s2", "kind": "control"},
                {"from": "ryu", "to": "s3", "kind": "control"},
                {"from": "ryu", "to": "s4", "kind": "control"},
                {"from": "s1", "to": "s2", "kind": "fabric"},
                {"from": "s1", "to": "s3", "kind": "fabric"},
                {"from": "s2", "to": "s4", "kind": "fabric"},
                {"from": "s3", "to": "s4", "kind": "fabric"},
            ],
            "monitoring_nodes": [
                {
                    "name": "Prometheus",
                    "state": "live" if monitoring["prometheus"].get("reachable") else "offline",
                    "url": "http://127.0.0.1:9090/",
                },
                {
                    "name": "Grafana",
                    "state": "live" if monitoring["grafana"].get("reachable") else "offline",
                    "url": "http://127.0.0.1:3000/",
                },
            ],
            "linux_mode": env["linux_runtime"],
        }

    def _lab_command(self, scenario: str, duration_sec: int, interactive: bool, link_mode: str) -> str:
        mode = "cli" if interactive else "headless"
        return f"bash scripts/run_integrated_sdn_lab.sh {scenario} {duration_sec} {mode} {link_mode}"

    def _normalize_switch(self, value: Any) -> str:
        if value is None:
            return "fabric"
        text = str(value).strip().lower()
        if text.startswith("s"):
            return text
        if text.isdigit():
            return f"s{text}"
        return text or "fabric"

    def _match_summary(self, match: Dict[str, Any]) -> str:
        if not match:
            return "match any"
        parts: List[str] = []
        if match.get("ipv4_src"):
            parts.append(f"src {match['ipv4_src']}")
        if match.get("ipv4_dst"):
            parts.append(f"dst {match['ipv4_dst']}")
        if match.get("tcp_dst"):
            parts.append(f"tcp/{match['tcp_dst']}")
        if match.get("udp_dst"):
            parts.append(f"udp/{match['udp_dst']}")
        if match.get("allowed_destinations"):
            parts.append("allow " + ", ".join(str(item) for item in match["allowed_destinations"]))
        return " | ".join(parts) if parts else "OpenFlow match"

    def _probe_http(self, url: str, timeout: float = 0.6) -> Dict[str, Any]:
        started = time.time()
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return {
                    "url": url,
                    "reachable": True,
                    "status": int(response.status),
                    "latency_ms": round((time.time() - started) * 1000.0, 2),
                }
        except Exception as exc:
            return {
                "url": url,
                "reachable": False,
                "error": str(exc),
                "latency_ms": round((time.time() - started) * 1000.0, 2),
            }

    def _probe_tcp(self, host: str, port: int, timeout: float = 0.4) -> Dict[str, Any]:
        started = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, int(port)))
            return {
                "host": host,
                "port": int(port),
                "reachable": True,
                "latency_ms": round((time.time() - started) * 1000.0, 2),
            }
        except Exception as exc:
            return {
                "host": host,
                "port": int(port),
                "reachable": False,
                "error": str(exc),
                "latency_ms": round((time.time() - started) * 1000.0, 2),
            }
        finally:
            sock.close()

    def _process_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{self.repo_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        env["ADAPTIVE_API_URL"] = self.api_url
        env["ADAPTIVE_RYU_LOG"] = str(self.ryu_log_path)
        return env

    def _read_tail(self, path: Path, max_chars: int = 2400) -> str:
        if not path.exists():
            return ""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
        return content[-max_chars:]
