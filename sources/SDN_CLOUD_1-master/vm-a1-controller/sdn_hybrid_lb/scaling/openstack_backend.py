from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenStackScaleConfig:
    cloud: Optional[str] = None  # clouds.yaml profile name
    image: Optional[str] = None
    flavor: Optional[str] = None
    network: Optional[str] = None
    key_name: Optional[str] = None
    security_groups: Optional[list[str]] = None


class OpenStackScalerBackend:
    """Optional skeleton for OpenStack-based scaling.

    Real deployments typically use Heat autoscaling groups or Nova API calls.
    This class shows where that integration would live.

    Requires: openstacksdk
    """

    def __init__(self, cfg: OpenStackScaleConfig) -> None:
        self.cfg = cfg
        try:
            import openstack  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "openstacksdk is required for OpenStack scaling. Install with: pip install openstacksdk"
            ) from e
        self.conn = openstack.connect(cloud=cfg.cloud)  # type: ignore

    def scale_out(self, count: int = 1) -> None:
        for i in range(count):
            name = f"hybrid-lb-srv-{int(__import__('time').time())}-{i}"
            self.conn.compute.create_server(  # type: ignore
                name=name,
                image_id=self.cfg.image,
                flavor_id=self.cfg.flavor,
                networks=[{"uuid": self.cfg.network}] if self.cfg.network else None,
                key_name=self.cfg.key_name,
                security_groups=self.cfg.security_groups,
            )

    def scale_in(self, count: int = 1) -> None:
        # Placeholder: implement policy (least loaded, oldest, etc.)
        servers = list(self.conn.compute.servers())  # type: ignore
        for s in servers[:count]:
            self.conn.compute.delete_server(s.id, ignore_missing=True)  # type: ignore
