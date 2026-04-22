from __future__ import annotations

import sys

try:
    import eventlet

    eventlet.monkey_patch()
    import eventlet.wsgi as eventlet_wsgi

    if not hasattr(eventlet_wsgi, "ALREADY_HANDLED"):
        eventlet_wsgi.ALREADY_HANDLED = object()
except Exception:
    # Let Ryu surface the real startup error if another dependency is missing.
    pass

from ryu.cmd.manager import main

if __name__ == "__main__":
    sys.exit(main())
