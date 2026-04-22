# Adaptive SDN Controller with Intent-Based Networking

## Overview
This project implements a centralized SDN controller using Ryu that supports:
- Intent-based networking
- Context-aware decision making
- DFPS prioritization
- Automatic host discovery
- Dynamic flow rule installation

## Features
- Centralized SDN control plane
- REST API integration
- Real-time host discovery
- Per-switch flow installation
- Context-aware decision engine

## Technologies Used
- Ryu Controller
- Mininet
- OpenFlow 1.3
- Flask API
- Python

## Topology
- 6 switches (Core, Distribution, Access)
- 15 hosts (Web, App, DB tiers)

## APIs

### Submit Intent
POST /api/intent/submit


### Update Context

POST /api/context/update


### Get Hosts

GET /api/network/hosts


## How to Run

### Start Controller
```bash
cd controller
source ../venv/bin/activate
ryu-manager main_controller.py
Start Topology
sudo mn -c
sudo mn --custom topology/cloud_topology.py --topo cloud \
--controller remote,ip=127.0.0.1,port=6633 \
--switch ovs,protocols=OpenFlow13
Test
pingall
