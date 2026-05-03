from __future__ import annotations

import collections
import collections.abc
import os


def _patch_collections_aliases() -> None:
    for alias in ("Mapping", "MutableMapping", "Sequence", "MutableSequence", "MutableSet"):
        if not hasattr(collections, alias):
            setattr(collections, alias, getattr(collections.abc, alias))


def _patch_eventlet_for_ryu() -> None:
    if str(os.environ.get("ADAPTIVE_RYU_COMPAT", "")).lower() not in {"1", "true", "yes", "on"}:
        return

    os.environ.setdefault("EVENTLET_NO_GREENDNS", "yes")
    try:
        import eventlet.wsgi as eventlet_wsgi  # type: ignore
    except Exception:
        return

    if not hasattr(eventlet_wsgi, "ALREADY_HANDLED"):
        # Ryu still imports this sentinel from eventlet.wsgi in older releases.
        # Newer eventlet builds no longer expose it, so provide a compatibility
        # object early in interpreter startup before ryu.app.wsgi is imported.
        eventlet_wsgi.ALREADY_HANDLED = object()


_patch_collections_aliases()
_patch_eventlet_for_ryu()
