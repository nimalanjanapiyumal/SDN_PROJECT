from pathlib import Path

from adaptive_cloud_platform.app import FRONTEND_DIR, component_one_platform, favicon, frontend


def test_frontend_assets_exist():
    index = FRONTEND_DIR / "index.html"
    icon = FRONTEND_DIR / "favicon.svg"
    content = index.read_text(encoding="utf-8")
    assert index.exists()
    assert icon.exists()
    assert "Adaptive Cloud SDN Integrated Console" in content
    assert "componentTwoOutcomeGrid" in content
    assert "componentTwoLinkGrid" in content
    assert "componentFourObjectiveGrid" in content
    assert "componentFourGraphGrid" in content
    assert "componentFourLinuxGrid" in content
    assert "componentFourLinkGrid" in content


def test_favicon_route_exists():
    response = favicon()
    assert response.media_type == "image/svg+xml"


def test_frontend_route_points_to_index():
    response = frontend()
    assert Path(response.path) == FRONTEND_DIR / "index.html"


def test_component_one_platform_reports_backend_mode():
    platform = component_one_platform()
    assert platform["integrated_backend_mode"] == "fastapi_simulated_flow_manager"
    assert "component_1_ryu_controller" in platform["source_integrations"]
