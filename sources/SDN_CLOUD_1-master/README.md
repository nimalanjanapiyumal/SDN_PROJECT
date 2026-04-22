# SDN-Based Adaptive Cloud Network Management Framework

This package includes the working SDN core plus an improved professional dashboard and the missing helper scripts to run the project quickly.

## What is included
- Hybrid SDN controller code
- Mininet dataplane and backend services
- Professional Flask dashboard with separate **Overview**, **OpenStack**, and **Testing & Evaluation** pages
- `manage.sh` command runner
- `start_parallel.sh` to start controller and dashboard on the same VM
- VM bootstrap scripts under `scripts/`

## Fastest way to run

### Controller VM
```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh fix-perms
bash manage.sh controller bootstrap
bash manage.sh controller start
bash manage.sh controller logs
```

### Dashboard VM or same VM
```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh dashboard bootstrap
export CONTROLLER_API_URL=http://<controller-ip>:8080
bash manage.sh dashboard start
bash manage.sh dashboard logs
```

### Controller + Dashboard on one VM
```bash
cd /home/user/SDN_CLOUD_1
bash start_parallel.sh
```

### Dataplane VM
```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh dataplane bootstrap
CTRL_IP=<controller-ip> bash manage.sh dataplane start
```

## Dashboard pages
- **Overview**: backend health, flow counts, throughput, utilization, GA weights
- **OpenStack**: configuration checklist, servers, addresses, networks
- **Testing & Evaluation**: testing plan, metrics, benchmark uploads, graphs, testing action buttons

## Important notes
- `10.0.0.100:8000` is the VIP inside Mininet, so test it from `h1` inside Mininet.
- Prometheus is optional. OpenFlow port statistics still provide flow count and bandwidth-derived metrics even without Prometheus.
- OpenStack visibility becomes active when you set either `OS_CLOUD` with a valid `clouds.yaml` profile, or export `OS_AUTH_URL`, `OS_USERNAME`, `OS_PASSWORD`, `OS_PROJECT_NAME`, `OS_USER_DOMAIN_NAME`, and `OS_PROJECT_DOMAIN_NAME`.


## Python 3.10 controller fix
This build disables Eventlet greendns with `EVENTLET_NO_GREENDNS=yes` before importing Ryu to avoid the old dns/MutableMapping crash on Python 3.10+.
