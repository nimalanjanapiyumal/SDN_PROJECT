#!/usr/bin/env python3
import importlib.util
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)

required = ['yaml', 'ryu', 'webob', 'netaddr', 'requests']
optional = ['eventlet']
missing = []
for m in required:
    if importlib.util.find_spec(m) is None:
        missing.append(m)
for m in optional:
    if importlib.util.find_spec(m) is None:
        missing.append(m)
if missing:
    raise SystemExit('Missing controller modules: ' + ', '.join(missing))
print('[OK] Controller Python dependencies verified.')
