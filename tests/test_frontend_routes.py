from pathlib import Path

from adaptive_cloud_platform.app import FRONTEND_DIR, favicon, frontend


def test_frontend_assets_exist():
    index = FRONTEND_DIR / "index.html"
    icon = FRONTEND_DIR / "favicon.svg"
    assert index.exists()
    assert icon.exists()
    assert "Adaptive Cloud SDN Console" in index.read_text(encoding="utf-8")


def test_favicon_route_exists():
    response = favicon()
    assert response.media_type == "image/svg+xml"


def test_frontend_route_points_to_index():
    response = frontend()
    assert Path(response.path) == FRONTEND_DIR / "index.html"
