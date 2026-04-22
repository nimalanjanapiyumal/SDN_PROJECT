#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BACKEND_NAME = os.environ.get('BACKEND_NAME', 'backend')
BACKEND_IP = os.environ.get('BACKEND_IP', '0.0.0.0')
PORT = int(os.environ.get('BACKEND_PORT', '8000'))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({
            'backend_name': BACKEND_NAME,
            'backend_ip': BACKEND_IP,
            'path': self.path,
            'status': 'ok',
        }).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()
