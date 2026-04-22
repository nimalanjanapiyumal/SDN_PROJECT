from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class _LBRequestHandler(BaseHTTPRequestHandler):
    server_version = "HybridLBRest/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        app = getattr(self.server, 'app_ref', None)
        if app is not None and hasattr(app, 'logger'):
            app.logger.info("REST %s - %s", self.address_string(), fmt % args)

    def _send_json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get('Content-Length', '0') or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {}

    @property
    def app(self):
        return getattr(self.server, 'app_ref', None)

    def do_GET(self) -> None:
        if self.path == '/lb/status':
            self._send_json(200, self.app.lb.status())
            return
        self._send_json(404, {'error': 'not found', 'path': self.path})

    def do_POST(self) -> None:
        if self.path == '/lb/recompute':
            weights = self.app.lb.force_ga()
            self._send_json(200, {'weights': weights})
            return
        if self.path.startswith('/lb/health/'):
            name = self.path.rsplit('/', 1)[-1]
            payload = self._read_json()
            healthy = bool(payload.get('healthy', True))
            ok = self.app.lb.set_backend_health(name, healthy)
            self._send_json(200, {'ok': ok, 'name': name, 'healthy': healthy})
            return
        self._send_json(404, {'error': 'not found', 'path': self.path})


class RestServerHandle:
    def __init__(self, httpd: ThreadingHTTPServer, thread: threading.Thread):
        self.httpd = httpd
        self.thread = thread

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def start_rest_server(app: Any, host: str = '0.0.0.0', port: int = 8080) -> RestServerHandle:
    httpd = ThreadingHTTPServer((host, int(port)), _LBRequestHandler)
    httpd.app_ref = app
    thread = threading.Thread(target=httpd.serve_forever, name='hybrid-lb-rest', daemon=True)
    thread.start()
    return RestServerHandle(httpd, thread)
