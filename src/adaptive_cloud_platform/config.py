from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from sdn_hybrid_lb.utils.config import AppConfig, load_config


@dataclass
class RuntimeConfig:
    app_env: str = os.environ.get("APP_ENV", "development")
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
    app_host: str = os.environ.get("APP_HOST", "0.0.0.0")
    app_port: int = int(os.environ.get("APP_PORT", "8080"))
    prometheus_exporter_port: int = int(os.environ.get("PROMETHEUS_EXPORTER_PORT", "9108"))
    controller_url: str = os.environ.get("CONTROLLER_URL", "http://127.0.0.1:8080")
    prometheus_url: str = os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:9090")
    system_config_path: str = os.environ.get("SYSTEM_CONFIG", "configs/system.yaml")

    @property
    def system_config(self) -> AppConfig:
        return load_config(self.system_config_path)


def get_runtime_config() -> RuntimeConfig:
    return RuntimeConfig()
