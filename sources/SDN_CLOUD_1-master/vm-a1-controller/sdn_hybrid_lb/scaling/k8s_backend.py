from __future__ import annotations

from dataclasses import dataclass


@dataclass
class K8sScaleConfig:
    namespace: str = "default"
    deployment: str = "my-service"


class KubernetesScalerBackend:
    """Optional skeleton for Kubernetes-based scaling.

    Requires: kubernetes python client
    """

    def __init__(self, cfg: K8sScaleConfig) -> None:
        self.cfg = cfg
        try:
            from kubernetes import client, config  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "kubernetes client is required. Install with: pip install kubernetes"
            ) from e

        # loads kubeconfig from default location or in-cluster config
        try:
            config.load_kube_config()  # type: ignore
        except Exception:
            config.load_incluster_config()  # type: ignore

        self.api = client.AppsV1Api()  # type: ignore

    def _get_replicas(self) -> int:
        dep = self.api.read_namespaced_deployment(self.cfg.deployment, self.cfg.namespace)
        return int(dep.spec.replicas)

    def _set_replicas(self, replicas: int) -> None:
        body = {"spec": {"replicas": int(replicas)}}
        self.api.patch_namespaced_deployment_scale(self.cfg.deployment, self.cfg.namespace, body)

    def scale_out(self, count: int = 1) -> None:
        cur = self._get_replicas()
        self._set_replicas(cur + int(count))

    def scale_in(self, count: int = 1) -> None:
        cur = self._get_replicas()
        self._set_replicas(max(1, cur - int(count)))
