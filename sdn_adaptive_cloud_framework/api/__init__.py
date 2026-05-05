"""REST API package for the Adaptive Cloud SDN framework.

Importing ``.app`` is deferred so the package can still be imported in
environments without FastAPI installed (e.g. controller-only nodes).
"""
try:
    from .app import app, create_app  # noqa: F401
    __all__ = ["app", "create_app"]
except Exception:  # pragma: no cover - FastAPI not installed
    app = None  # type: ignore[assignment]

    def create_app():  # type: ignore[no-redef]
        raise RuntimeError(
            "FastAPI is not installed; pip install fastapi to use the REST API"
        )

    __all__ = ["app", "create_app"]

