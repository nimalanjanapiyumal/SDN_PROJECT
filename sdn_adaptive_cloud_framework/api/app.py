"""FastAPI application that exposes the SDN controller's REST surface.

Run with::

    uvicorn sdn_adaptive_cloud_framework.api.app:app --host 0.0.0.0 --port 8080

The app and the Ryu controller share the same ``ControllerState`` singleton,
so an intent submitted here will land as a flow-mod on the connected
datapaths managed by ``ryu_controller``.
"""
from __future__ import annotations

from fastapi import FastAPI

from . import routes_context, routes_intent, routes_network


def create_app() -> FastAPI:
    app = FastAPI(
        title="SDN Adaptive Cloud Framework API",
        version="0.1.0",
        description=(
            "REST surface for the Intelligent SDN Controller. "
            "Endpoints: /api/intent/*, /api/context/*, /api/network/*, /api/flow/*."
        ),
    )

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict:
        return {"status": "ok"}

    app.include_router(routes_intent.router)
    app.include_router(routes_context.router)
    app.include_router(routes_network.router)
    return app


app = create_app()


__all__ = ["app", "create_app"]
