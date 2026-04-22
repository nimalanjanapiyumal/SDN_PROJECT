from __future__ import annotations

import json
from typing import Any, Dict

from ryu.app.wsgi import ControllerBase, route
from webob import Response


class LBRestController(ControllerBase):
    """REST API:
    - GET  /lb/status
    - POST /lb/recompute
    - POST /lb/health/{name}   body: {"healthy": true/false}
    """

    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.app = data["app"]

    @route("lb", "/lb/status", methods=["GET"])
    def status(self, req, **kwargs):
        body = json.dumps(self.app.lb.status(), indent=2)
        return Response(content_type="application/json", body=body)

    @route("lb", "/lb/recompute", methods=["POST"])
    def recompute(self, req, **kwargs):
        weights = self.app.lb.force_ga()
        body = json.dumps({"weights": weights}, indent=2)
        return Response(content_type="application/json", body=body)

    @route("lb", "/lb/health/{name}", methods=["POST"])
    def set_health(self, req, **kwargs):
        name = kwargs.get("name")
        try:
            payload = req.json_body if req.body else {}
        except Exception:
            payload = {}
        healthy = bool(payload.get("healthy", True))
        ok = self.app.lb.set_backend_health(name, healthy)
        body = json.dumps({"ok": ok, "name": name, "healthy": healthy}, indent=2)
        return Response(content_type="application/json", body=body)
