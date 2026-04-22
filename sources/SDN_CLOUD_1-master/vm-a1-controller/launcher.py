#!/usr/bin/env python3
from __future__ import annotations

import logging
import os

from os_ken.lib import hub
hub.patch(thread=False)

from os_ken import cfg, log as osken_log
osken_log.early_init_log(logging.INFO)
from os_ken.base import app_manager
from os_ken.controller import controller  # noqa: F401

try:
    from os_ken.topology import switches  # noqa: F401
except Exception:
    switches = None

CONF = cfg.CONF


def _safe_conf_init() -> None:
    try:
        CONF(args=[], project='os_ken', prog='sdn-hybrid-controller')
    except TypeError:
        try:
            CONF([], project='os_ken', prog='sdn-hybrid-controller')
        except TypeError:
            CONF([])


def _set_opt(name: str, value) -> None:
    try:
        CONF.set_override(name, value)
    except Exception:
        try:
            setattr(CONF, name, value)
        except Exception:
            pass


def main() -> None:
    ofp_port = int(os.environ.get('OFP_PORT', '6633'))
    rest_port = int(os.environ.get('REST_PORT', '8080'))

    _safe_conf_init()
    for opt_name in ('ofp_tcp_listen_port', 'ofp_listen_port'):
        _set_opt(opt_name, ofp_port)
    _set_opt('wsapi_port', rest_port)

    app_list = ['sdn_hybrid_lb.controller.osken_app']

    if hasattr(app_manager, 'run_apps'):
        app_manager.run_apps(app_list)
        return

    mgr = app_manager.AppManager.get_instance()
    mgr.load_apps(app_list)
    ctx = mgr.create_contexts()
    services = mgr.instantiate_apps(**ctx)
    try:
        hub.joinall(services)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
