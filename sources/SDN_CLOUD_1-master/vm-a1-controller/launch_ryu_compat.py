#!/usr/bin/env python3
from __future__ import annotations

import os
import warnings

# Avoid Eventlet greendns import path which can pull an old dnspython build
# incompatible with Python 3.10+ (collections.MutableMapping removal).
os.environ.setdefault("EVENTLET_NO_GREENDNS", "yes")

# Keep controller logs cleaner on newer Python/Eventlet stacks.
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"eventlet(\..*)?")

# Ryu 4.34 imports ryu.app.wsgi through ryu.cmd.manager.
# Newer Eventlet releases removed eventlet.wsgi.ALREADY_HANDLED,
# which makes that import fail. Patch the symbol before importing Ryu.
try:
    import eventlet.wsgi as _eventlet_wsgi
    if not hasattr(_eventlet_wsgi, "ALREADY_HANDLED"):
        _eventlet_wsgi.ALREADY_HANDLED = object()
except Exception:
    pass

from ryu.cmd.manager import main

if __name__ == "__main__":
    main()
