from adaptive_cloud_platform.services.security_service import SecurityService


def test_security_action_builder():
    service = SecurityService()
    action = service.build_action('block', '10.0.0.5', 'test', 4)
    assert action['action'] == 'block'
    assert action['subject'] == '10.0.0.5'
    assert action['severity'] == 4
