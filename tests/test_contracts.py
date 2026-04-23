import yaml
from pathlib import Path


def test_openapi_contains_core_paths():
    data = yaml.safe_load(Path('openapi/openapi.yaml').read_text(encoding='utf-8'))
    assert '/api/v1/intents' in data['paths']
    assert '/api/v1/context' in data['paths']
    assert '/api/v1/security-actions' in data['paths']
    assert '/api/v1/component-2/telemetry' in data['paths']
