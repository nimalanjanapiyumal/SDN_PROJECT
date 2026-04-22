# Complete Steps

## 1. Extract the project on each VM
Use the same project folder name on each VM, for example:

```bash
mkdir -p /home/user
cd /home/user
unzip sdn_hybrid_openstack_project_complete_professional.zip
mv sdn_hybrid_openstack_project_complete_professional SDN_CLOUD_1
cd SDN_CLOUD_1
bash manage.sh fix-perms
```

On Linux, the `.tar.gz` package preserves executable bits more reliably than `.zip`.

## 2. Controller VM

```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh controller bootstrap
bash manage.sh controller start
bash manage.sh controller status
bash manage.sh controller logs
```

The controller listens on OpenFlow port `6633` and REST API port `8080` by default.

## 3. Find the controller IP
On the controller VM:

```bash
hostname -I
```

or

```bash
ip route get 1.1.1.1 | awk '{print $7; exit}'
```

Use that IP as `<controller-ip>` on the dataplane and dashboard VM.

## 4. Dashboard VM or same VM

```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh dashboard bootstrap
export CONTROLLER_API_URL=http://<controller-ip>:8080
bash manage.sh dashboard start
bash manage.sh dashboard status
bash manage.sh dashboard logs
```

Open:

```text
http://<dashboard-vm-ip>:5050
```

## 5. Start controller and dashboard together on one VM

```bash
cd /home/user/SDN_CLOUD_1
bash start_parallel.sh
```

## 6. Dataplane VM

```bash
cd /home/user/SDN_CLOUD_1
bash manage.sh dataplane bootstrap
CTRL_IP=<controller-ip> bash manage.sh dataplane start
```

This opens the Mininet CLI.

## 7. Validate the VIP from Mininet
Inside the Mininet CLI:

```bash
h1 ping -c 2 10.0.0.100
h1 curl http://10.0.0.100:8000
```

The response should identify the backend serving the request.

## 8. Run testing and evaluation benchmarks
Inside the Mininet CLI:

```bash
h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 10 --duration 20 --sla-ms 200 --json /tmp/http_10.json
h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 20 --duration 20 --sla-ms 200 --json /tmp/http_20.json
h1 python3 tools/http_benchmark.py --url http://10.0.0.100:8000 --concurrency 50 --duration 20 --sla-ms 200 --json /tmp/http_50.json
h1 python3 tools/iperf3_benchmark.py --vip 10.0.0.100 --port 5201 --duration 15 --parallel 4 --json /tmp/iperf_4.json
```

Then upload these JSON files on the dashboard's **Testing & Evaluation** page.

## 9. OpenStack integration
OpenStack is optional for the SDN demo. To enable visibility on the dashboard's OpenStack page, set either:

### Option A: Use `clouds.yaml`
```bash
export OS_CLOUD=mycloud
```

### Option B: Export Keystone variables
```bash
export OS_AUTH_URL=http://<keystone-host>:5000/v3
export OS_USERNAME=<username>
export OS_PASSWORD=<password>
export OS_PROJECT_NAME=<project>
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
```

Then restart the dashboard:

```bash
bash manage.sh dashboard stop
bash manage.sh dashboard start
```
