# Runtime fixes included

This package fixes two runtime issues:

1. **Controller REST 500 on /lb/recompute and /lb/health**
   - Ryu/WebOb requires bytes or an explicit charset for JSON bodies.
   - The REST API now returns UTF-8 encoded JSON responses.

2. **Mininet interface pair already exists**
   - Previous runs can leave stale interfaces and OVS state behind.
   - `vm-a2-dataplane/run_mininet.sh` now runs cleanup automatically using `mn -c` and removes stale bridge state before starting.

## Commands

Controller VM:
```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh fix-perms
bash manage.sh controller bootstrap
bash manage.sh controller start
bash manage.sh controller logs
```

Dataplane VM:
```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh dataplane bootstrap
CTRL_IP=<controller-ip> bash manage.sh dataplane start
```

If you need to skip cleanup once:
```bash
cd /home/user/SDN_CLOUD_1/vm-a2-dataplane
CLEAN_MININET=0 CTRL_IP=<controller-ip> ./run_mininet.sh
```
