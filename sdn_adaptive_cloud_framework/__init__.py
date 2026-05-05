"""SDN-Based Adaptive Cloud Network Management Framework.

Top-level package implementing the development outline:

* ``controller`` - Module 1 (Ryu app + intent + DFPS + flow + topology + hosts)
* ``api``        - REST API layer wired to the controller's shared state
* ``load_balancer`` - Module 4 (RR + GA + hybrid)
* ``monitoring``    - Module 5 (Prometheus exporter + Grafana dashboards)
* ``ml_module``     - Module 6 (heuristic + sklearn baseline)
* ``security``      - Module 7 (segmentation, CTI, continuous-auth, suricata)
* ``topology``      - Mininet topology + evaluation scenarios
* ``tests``         - pytest unit tests
"""
__version__ = "0.1.0"
