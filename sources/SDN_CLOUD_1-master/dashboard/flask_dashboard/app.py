
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'data' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STORE_PATH = UPLOAD_DIR / 'benchmark_store.json'


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('DASHBOARD_SECRET_KEY', 'sdn-hybrid-dashboard')
    app.config['CONTROLLER_API_URL'] = os.environ.get('CONTROLLER_API_URL', 'http://127.0.0.1:8080').rstrip('/')

    @app.context_processor
    def inject_globals():
        return {
            'controller_api_url': app.config['CONTROLLER_API_URL'],
            'now_ts': int(time.time()),
        }

    @app.get('/')
    @app.get('/overview')
    def overview():
        status, status_error = fetch_controller_status(app.config['CONTROLLER_API_URL'])
        overview_cards = build_overview_cards(status)
        chart_payload = build_overview_chart_payload(status)
        return render_template(
            'overview.html',
            status=status,
            status_error=status_error,
            cards=overview_cards,
            chart_payload=chart_payload,
        )

    @app.get('/openstack')
    def openstack_page():
        os_data = inspect_openstack()
        return render_template('openstack.html', os_data=os_data)

    @app.route('/testing', methods=['GET', 'POST'])
    def testing_page():
        if request.method == 'POST':
            action = request.form.get('action', '').strip()
            if action == 'upload_http':
                save_upload('http_results', request.files.get('http_file'))
            elif action == 'upload_iperf':
                save_upload('iperf_results', request.files.get('iperf_file'))
            elif action == 'clear_results':
                clear_store()
                flash('Uploaded benchmark results cleared.', 'success')
            elif action == 'recompute':
                ok, msg = post_json(f"{app.config['CONTROLLER_API_URL']}/lb/recompute", {})
                flash(msg, 'success' if ok else 'error')
            elif action.startswith('health:'):
                _, backend, value = action.split(':', 2)
                healthy = value == 'up'
                ok, msg = post_json(f"{app.config['CONTROLLER_API_URL']}/lb/health/{backend}", {'healthy': healthy})
                flash(msg, 'success' if ok else 'error')
            return redirect(url_for('testing_page'))

        status, status_error = fetch_controller_status(app.config['CONTROLLER_API_URL'])
        store = load_store()
        testing_payload = build_testing_payload(store)
        return render_template(
            'testing.html',
            status=status,
            status_error=status_error,
            store=store,
            testing_payload=testing_payload,
        )

    @app.post('/actions/recompute')
    def recompute():
        ok, msg = post_json(f"{app.config['CONTROLLER_API_URL']}/lb/recompute", {})
        flash(msg, 'success' if ok else 'error')
        return redirect(request.referrer or url_for('overview'))

    @app.post('/actions/backend/<name>/<state>')
    def backend_health(name: str, state: str):
        healthy = state == 'up'
        ok, msg = post_json(f"{app.config['CONTROLLER_API_URL']}/lb/health/{name}", {'healthy': healthy})
        flash(msg, 'success' if ok else 'error')
        return redirect(request.referrer or url_for('overview'))

    return app


def fetch_controller_status(base_url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        resp = requests.get(f'{base_url}/lb/status', timeout=2.5)
        resp.raise_for_status()
        data = resp.json()
        return data, None
    except Exception as e:
        return None, str(e)


def post_json(url: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        resp = requests.post(url, json=payload, timeout=2.5)
        text = None
        try:
            text = resp.json()
        except Exception:
            text = resp.text
        if resp.ok:
            return True, f'Action completed: {text}'
        return False, f'Controller returned {resp.status_code}: {text}'
    except Exception as e:
        return False, f'Action failed: {e}'


def build_overview_cards(status: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not status:
        return [
            {'label': 'Controller status', 'value': 'Unavailable'},
            {'label': 'VIP', 'value': 'Unknown'},
            {'label': 'Backends', 'value': '0'},
            {'label': 'Active flows', 'value': '0'},
        ]
    backends = status.get('backends', [])
    healthy = sum(1 for b in backends if b.get('healthy'))
    throughput = sum((b.get('metrics', {}) or {}).get('throughput_mbps') or 0 for b in backends)
    return [
        {'label': 'Controller status', 'value': 'Connected'},
        {'label': 'VIP', 'value': (status.get('vip', {}) or {}).get('ip', 'Unknown')},
        {'label': 'Healthy backends', 'value': f'{healthy} / {len(backends)}'},
        {'label': 'Active flows', 'value': str(status.get('active_flows', 0))},
        {'label': 'Aggregate throughput', 'value': f'{throughput:.1f} Mbps'},
        {'label': 'RR mode', 'value': (status.get('controller', {}) or {}).get('rr_mode', 'Unknown')},
    ]


def build_overview_chart_payload(status: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not status:
        return {'backend_labels': [], 'cpu': [], 'mem': [], 'bw': [], 'throughput': [], 'weights': []}
    labels, cpu, mem, bw, throughput, weights, active_conn = [], [], [], [], [], [], []
    weight_map = status.get('weights', {}) or {}
    for b in status.get('backends', []):
        metrics = b.get('metrics', {}) or {}
        labels.append(b.get('name', 'backend'))
        cpu.append(round(((metrics.get('cpu_util') or 0) * 100), 2))
        mem.append(round(((metrics.get('mem_util') or 0) * 100), 2))
        bw.append(round(((metrics.get('bw_util') or 0) * 100), 2))
        throughput.append(round((metrics.get('throughput_mbps') or 0), 2))
        weights.append(round((weight_map.get(b.get('name'), b.get('weight') or 0) * 100), 2))
        active_conn.append(int(metrics.get('active_connections') or 0))
    return {
        'backend_labels': labels,
        'cpu': cpu,
        'mem': mem,
        'bw': bw,
        'throughput': throughput,
        'weights': weights,
        'active_conn': active_conn,
    }


def inspect_openstack() -> Dict[str, Any]:
    env = {
        'OS_CLOUD': os.environ.get('OS_CLOUD', ''),
        'OS_AUTH_URL': os.environ.get('OS_AUTH_URL', ''),
        'OS_USERNAME': os.environ.get('OS_USERNAME', ''),
        'OS_PASSWORD': os.environ.get('OS_PASSWORD', ''),
        'OS_PROJECT_NAME': os.environ.get('OS_PROJECT_NAME', ''),
        'OS_USER_DOMAIN_NAME': os.environ.get('OS_USER_DOMAIN_NAME', ''),
        'OS_PROJECT_DOMAIN_NAME': os.environ.get('OS_PROJECT_DOMAIN_NAME', ''),
    }
    checklist = [
        {'name': key, 'present': bool(val), 'value': ('***' if key == 'OS_PASSWORD' and val else val)}
        for key, val in env.items()
    ]
    clouds_paths = [
        Path.home() / '.config' / 'openstack' / 'clouds.yaml',
        Path('/etc/openstack/clouds.yaml'),
        BASE_DIR.parent / 'clouds.yaml',
    ]
    clouds_found = [str(p) for p in clouds_paths if p.exists()]

    configured = bool(env['OS_CLOUD']) or all(env[k] for k in ['OS_AUTH_URL', 'OS_USERNAME', 'OS_PASSWORD', 'OS_PROJECT_NAME'])
    result = {
        'configured': configured,
        'checklist': checklist,
        'clouds_found': clouds_found,
        'servers': [],
        'networks': [],
        'status': 'Not configured' if not configured else 'Configured',
        'error': None,
        'guidance': 'Set OS_CLOUD with clouds.yaml or export OS_AUTH_URL, OS_USERNAME, OS_PASSWORD, OS_PROJECT_NAME and OS_USER_DOMAIN_NAME / OS_PROJECT_DOMAIN_NAME.',
    }
    if not configured:
        return result

    try:
        import openstack  # type: ignore
        kwargs = {}
        if env['OS_CLOUD']:
            kwargs['cloud'] = env['OS_CLOUD']
            conn = openstack.connect(**kwargs)
        else:
            conn = openstack.connection.Connection(
                auth_url=env['OS_AUTH_URL'],
                project_name=env['OS_PROJECT_NAME'],
                username=env['OS_USERNAME'],
                password=env['OS_PASSWORD'],
                user_domain_name=env['OS_USER_DOMAIN_NAME'] or 'Default',
                project_domain_name=env['OS_PROJECT_DOMAIN_NAME'] or 'Default',
            )
        servers = []
        for s in conn.compute.servers(details=True):
            addrs = []
            for net_name, entries in (getattr(s, 'addresses', {}) or {}).items():
                ips = [e.get('addr', '') for e in entries if e.get('addr')]
                if ips:
                    addrs.append(f"{net_name}: {', '.join(ips)}")
            servers.append({
                'name': getattr(s, 'name', '-'),
                'status': getattr(s, 'status', '-'),
                'addresses': '; '.join(addrs) or '-',
            })
        result['servers'] = servers
        nets = []
        try:
            for n in conn.network.networks():
                nets.append({'name': getattr(n, 'name', '-'), 'status': getattr(n, 'status', '-')})
        except Exception:
            pass
        result['networks'] = nets
        result['status'] = 'Connected'
    except Exception as e:
        result['status'] = 'Connection failed'
        result['error'] = str(e)
    return result


def load_store() -> Dict[str, List[Dict[str, Any]]]:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'http_results': [], 'iperf_results': []}


def save_store(data: Dict[str, Any]) -> None:
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding='utf-8')


def save_upload(key: str, file_storage) -> None:
    if not file_storage or not file_storage.filename:
        flash('No file selected.', 'error')
        return
    try:
        raw = file_storage.read().decode('utf-8')
        payload = json.loads(raw)
        store = load_store()
        store.setdefault(key, []).append(payload)
        save_store(store)
        flash(f'Uploaded {file_storage.filename} successfully.', 'success')
    except Exception as e:
        flash(f'Could not read JSON: {e}', 'error')


def clear_store() -> None:
    save_store({'http_results': [], 'iperf_results': []})


def build_testing_payload(store: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    http_results = sorted(store.get('http_results', []), key=lambda x: x.get('concurrency', 0))
    iperf_results = sorted(store.get('iperf_results', []), key=lambda x: x.get('parallel', 0))
    return {
        'http_labels': [str(x.get('concurrency', '?')) for x in http_results],
        'http_throughput': [round(x.get('throughput_req_s', 0), 2) for x in http_results],
        'http_p95': [round(x.get('p95_ms', 0) or 0, 2) for x in http_results],
        'http_sla': [round(x.get('sla_pct', 0), 2) for x in http_results],
        'iperf_labels': [str(x.get('parallel', '?')) for x in iperf_results],
        'iperf_throughput': [round(x.get('throughput_mbps', 0), 2) for x in iperf_results],
    }


app = create_app()


if __name__ == '__main__':
    host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    port = int(os.environ.get('DASHBOARD_PORT', '5050'))
    app.run(host=host, port=port, debug=False)
