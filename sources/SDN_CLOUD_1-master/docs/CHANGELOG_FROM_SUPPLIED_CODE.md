# Fresh Package Change Log

## What changed from the supplied code
- Kept the original hybrid RR + GA logic and controller structure.
- Preserved the `max_connections`-aware overload fix for backend eligibility.
- Rebuilt the deployment wrapper scripts from scratch.
- Replaced the fragile Ryu installation path with an OS-Ken based controller runtime.
- Added a clean `manage.sh` launcher for controller, dashboard, dataplane, and combined stack operations.
- Added `start_parallel.sh` to bootstrap and start controller + dashboard together on one host.
- Added complete run steps in `docs/COMPLETE_STEPS.md`.
- Retained Flask dashboard, Prometheus config, Grafana dashboard, and OpenStack helper modules.
