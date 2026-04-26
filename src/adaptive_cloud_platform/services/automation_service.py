from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Optional

from adaptive_cloud_platform.models import IntegratedAutomationRequest, IntegratedRunRequest


class SystemAutomationService:
    def __init__(
        self,
        run_callback: Callable[[IntegratedRunRequest, str], dict],
        context_callback: Callable[[], dict],
        on_cycle: Optional[Callable[[dict, dict], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        self.run_callback = run_callback
        self.context_callback = context_callback
        self.on_cycle = on_cycle
        self.on_error = on_error
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._config = IntegratedAutomationRequest()
        self._started_at: Optional[float] = None
        self._last_cycle_at: Optional[float] = None
        self._last_result: Optional[dict] = None
        self._last_error: Optional[str] = None
        self._executed_cycles = 0
        self._cycle_index = 0

    def start(self, config: IntegratedAutomationRequest) -> dict:
        self.stop()
        with self._lock:
            self._config = config
            self._running = True
            self._started_at = time.time()
            self._last_cycle_at = None
            self._last_result = None
            self._last_error = None
            self._executed_cycles = 0
            self._cycle_index = 0
            self._stop_event = threading.Event()

        self._run_cycle()

        with self._lock:
            if self._running:
                self._thread = threading.Thread(target=self._loop, name='adaptive-system-automation', daemon=True)
                self._thread.start()
        return self.status()

    def stop(self) -> dict:
        thread: Optional[threading.Thread]
        with self._lock:
            self._running = False
            self._stop_event.set()
            thread = self._thread
            self._thread = None
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        return self.status()

    def status(self) -> dict:
        with self._lock:
            config = self._config
            running = self._running
            started_at = self._started_at
            last_cycle_at = self._last_cycle_at
            last_result = dict(self._last_result) if self._last_result else None
            last_error = self._last_error
            executed_cycles = self._executed_cycles
            cycle_index = self._cycle_index
        next_scenario = self._predict_next_scenario(cycle_index, include_adaptive=True)
        return {
            'running': running,
            'strategy': config.strategy,
            'preferred_scenario': config.preferred_scenario,
            'scenario_sequence': list(config.scenario_sequence),
            'interval_sec': config.interval_sec,
            'workload_requests': config.workload_requests,
            'include_monitoring': config.include_monitoring,
            'include_intent': config.include_intent,
            'include_security': config.include_security,
            'max_cycles': config.max_cycles,
            'started_at': started_at,
            'last_cycle_at': last_cycle_at,
            'uptime_sec': round(time.time() - started_at, 2) if running and started_at else 0.0,
            'executed_cycles': executed_cycles,
            'last_result': last_result,
            'last_error': last_error,
            'next_scenario': next_scenario,
        }

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
                interval_sec = self._config.interval_sec
                stop_event = self._stop_event
            if stop_event.wait(interval_sec):
                return
            self._run_cycle()

    def _run_cycle(self) -> None:
        with self._lock:
            if not self._running:
                return
            config = self._config
            scenario = self._predict_next_scenario(self._cycle_index, include_adaptive=True)
            payload = IntegratedRunRequest(
                scenario=scenario,
                reset=config.reset_on_start and self._executed_cycles == 0,
                workload_requests=config.workload_requests,
                include_security=config.include_security,
                include_monitoring=config.include_monitoring,
                include_intent=config.include_intent,
            )
        try:
            result = self.run_callback(payload, 'automation')
            cycle_time = time.time()
            snapshot = {
                'scenario': result.get('scenario'),
                'latency_ms': result.get('latency_ms'),
                'ts': cycle_time,
                'steps': result.get('steps', []),
            }
            with self._lock:
                self._last_cycle_at = cycle_time
                self._last_result = snapshot
                self._last_error = None
                self._executed_cycles += 1
                self._cycle_index += 1
                max_cycles = self._config.max_cycles
                if max_cycles is not None and self._executed_cycles >= max_cycles:
                    self._running = False
                    self._stop_event.set()
            if self.on_cycle:
                self.on_cycle(result, snapshot)
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
            if self.on_error:
                self.on_error(exc)

    def _predict_next_scenario(self, cycle_index: int, include_adaptive: bool) -> str:
        with self._lock:
            config = self._config
        if include_adaptive and config.strategy == 'adaptive':
            inferred = self._adaptive_scenario()
            if inferred:
                return inferred
        sequence = list(config.scenario_sequence) or [config.preferred_scenario]
        return sequence[cycle_index % len(sequence)]

    def _adaptive_scenario(self) -> Optional[str]:
        try:
            context = self.context_callback()
        except Exception:
            return None
        component_1 = context.get('component_1', {})
        component_2 = context.get('component_2', {})
        component_4 = context.get('component_4', {})
        latest_label = str(context.get('latest_prediction_label') or '').lower()

        if latest_label in {'ddos', 'port_scan'}:
            return latest_label
        if int(component_4.get('blocked_iocs', 0) or 0) > 0 or int(component_4.get('active_security_rules', 0) or 0) > 0:
            return 'ddos'
        if latest_label == 'congestion':
            return 'congestion'
        if int(component_1.get('failed_requests', 0) or 0) > 0:
            return 'congestion'
        if int(component_2.get('high_risk_predictions', 0) or 0) > 0:
            return 'ddos'
        return None
