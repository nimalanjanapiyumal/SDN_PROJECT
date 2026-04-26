from adaptive_cloud_platform.services.security_service import SecurityService


def test_security_action_builder():
    service = SecurityService()
    action = service.build_action('block', '10.0.0.5', 'test', 4)
    assert action['action'] == 'block'
    assert action['subject'] == '10.0.0.5'
    assert action['severity'] == 4


def test_continuous_auth_quarantines_high_risk_session():
    service = SecurityService()
    login = service.create_session('admin', '10.0.0.2', 'admin123')

    result = service.verify_session(
        login['token'],
        '10.0.0.88',
        bytes_sent=120 * 1024 * 1024,
        failed_attempts=2,
    )

    assert result['allowed'] is False
    assert result['session']['status'] == 'quarantined'
    assert result['security_action']['action'] == 'quarantine'


def test_micro_segmentation_blocks_web_to_db_lateral_flow():
    service = SecurityService()

    result = service.evaluate_flow('10.0.0.1', '10.0.0.12', 3306, 'tcp')

    assert result['allowed'] is False
    assert result['src_zone'] == 'web'
    assert result['dst_zone'] == 'db'
    assert result['security_action']['action'] == 'quarantine'


def test_cti_alert_blocks_known_indicator():
    service = SecurityService()

    result = service.handle_alert({
        'src_ip': '91.108.4.1',
        'signature': 'DDoS source detected',
        'severity': 1,
    })

    assert result['should_block'] is True
    assert result['security_action']['action'] == 'block'


def test_security_status_exposes_objectives_graphs_and_linux_links():
    service = SecurityService()
    status = service.status()
    platform = status["platform"]

    assert status["objectives"]["continuous_authentication"]["implemented"] is True
    assert status["functional_requirements"]["auto_update_rules"]["implemented"] is True
    assert status["graphs"]["benchmark"]["title"] == "Adaptive vs static firewall"
    assert any(link["name"] == "OpenStack Install Guide" for link in platform["deployment_links"])
    assert "current_platform" in platform["linux_runtime"]
