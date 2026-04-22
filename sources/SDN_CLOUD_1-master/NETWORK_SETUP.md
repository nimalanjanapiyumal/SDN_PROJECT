# 2-VM Network Setup (Mininet data plane + remote Ryu controller)

## Goal
VM-A2 (Mininet/OVS data plane) must reach VM-A1 (Ryu controller) over a stable IP network.

Best practice: **2 NICs per VM**
- **NIC 1 (NAT)**: Internet access for apt/pip installs.
- **NIC 2 (Host-only / Internal / Private LAN)**: Dedicated controller↔dataplane link.

---

## Recommended IP plan (example)
Host-only / internal network: `192.168.56.0/24`
- VM-A1 (Controller): `192.168.56.10/24`
- VM-A2 (Data plane): `192.168.56.11/24`

OpenFlow:
- Controller listens on: `tcp/6633`

REST API (optional):
- Controller listens on: `tcp/8080`

---

## Hypervisor-side setup
### VirtualBox (common)
1. Create/enable **Host-Only Network** (vboxnet0) with:
   - IPv4: `192.168.56.1`
   - Mask: `255.255.255.0`
   - DHCP: OFF (recommended)
2. For **each VM**:
   - Adapter 1: NAT
   - Adapter 2: Host-only Adapter = vboxnet0

### VMware Workstation / Player
- Use **VMnet1 (Host-only)** or a custom VMnet.
- Set the subnet to `192.168.56.0/24` and disable DHCP if you want static IPs.

---

## Ubuntu guest configuration (static IP on NIC 2)
### 1) Identify the NIC name
Run:
```bash
ip -br a
```
Typical names:
- NAT: `enp0s3`
- Host-only: `enp0s8`

### 2) Netplan example for VM-A1 (Controller)
Edit `/etc/netplan/01-netcfg.yaml` (or the existing netplan file):
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses:
        - 192.168.56.10/24
```
Apply:
```bash
sudo netplan apply
```

### 3) Netplan example for VM-A2 (Data plane)
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: true
    enp0s8:
      dhcp4: false
      addresses:
        - 192.168.56.11/24
```
Apply:
```bash
sudo netplan apply
```

---

## Connectivity checks
### Ping
From VM-A2:
```bash
ping -c 3 192.168.56.10
```
From VM-A1:
```bash
ping -c 3 192.168.56.11
```

### Check controller ports (from VM-A2)
After controller starts:
```bash
nc -vz 192.168.56.10 6633
nc -vz 192.168.56.10 8080
```

---

## Firewall rules
If UFW is enabled on VM-A1:
```bash
sudo ufw allow 6633/tcp
sudo ufw allow 8080/tcp
```

---

## Mininet controller target
On VM-A2, start Mininet with:
```bash
CTRL_IP=192.168.56.10 CTRL_PORT=6633 ./run_mininet.sh
```

