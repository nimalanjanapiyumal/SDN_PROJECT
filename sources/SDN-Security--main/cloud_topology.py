#!/usr/bin/env python3
# cloud_topology.py
# Three-zone cloud topology: Web Tier, App Tier, DB Tier
# H D P Chathuranga — IT22902566 — SLIIT

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import time, subprocess

def create_cloud_topology():
    "Create 3-zone cloud network with remote Ryu controller"

    setLogLevel('info')

    # Connect to remote Ryu controller running on localhost:6633
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True
    )

    info('*** Adding Remote Controller (Ryu)\n')
    c0 = net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6633
    )

    info('*** Adding Core Switch\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')  # Core SDN switch

    info('*** Adding Zone Switches\n')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')  # Zone A - Web Tier
    s3 = net.addSwitch('s3', protocols='OpenFlow13')  # Zone B - App Tier
    s4 = net.addSwitch('s4', protocols='OpenFlow13')  # Zone C - DB Tier

    info('*** Adding Hosts — Zone A (Web Tier: 10.0.0.x)\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', defaultRoute='via 10.0.0.254')
    h2 = net.addHost('h2', ip='10.0.0.2/24', defaultRoute='via 10.0.0.254')

    info('*** Adding Hosts — Zone B (App Tier: 10.0.1.x)\n')
    h3 = net.addHost('h3', ip='10.0.1.1/24', defaultRoute='via 10.0.1.254')
    h4 = net.addHost('h4', ip='10.0.1.2/24', defaultRoute='via 10.0.1.254')

    info('*** Adding Hosts — Zone C (DB Tier: 10.0.2.x)\n')
    h5 = net.addHost('h5', ip='10.0.2.1/24', defaultRoute='via 10.0.2.254')
    h6 = net.addHost('h6', ip='10.0.2.2/24', defaultRoute='via 10.0.2.254')

    info('*** Adding Links with bandwidth constraints\n')
    # Core switch links (1 Gbps)
    net.addLink(s1, s2, cls=TCLink, bw=1000)
    net.addLink(s1, s3, cls=TCLink, bw=1000)
    net.addLink(s1, s4, cls=TCLink, bw=1000)

    # Host links (100 Mbps, 1ms delay — realistic cloud)
    net.addLink(s2, h1, cls=TCLink, bw=100, delay='1ms')
    net.addLink(s2, h2, cls=TCLink, bw=100, delay='1ms')
    net.addLink(s3, h3, cls=TCLink, bw=100, delay='1ms')
    net.addLink(s3, h4, cls=TCLink, bw=100, delay='1ms')
    net.addLink(s4, h5, cls=TCLink, bw=100, delay='1ms')
    net.addLink(s4, h6, cls=TCLink, bw=100, delay='1ms')

    info('*** Starting Network\n')
    net.start()

    # Set OpenFlow 1.3 on all switches
    for sw in [s1, s2, s3, s4]:
        sw.cmd(f'ovs-vsctl set bridge {sw.name} protocols=OpenFlow13')

    info('*** Testing basic connectivity\n')
    net.pingAll()

    info('\n*** Network is running. Zones:\n')
    info('  Zone A (Web):  h1=10.0.0.1  h2=10.0.0.2\n')
    info('  Zone B (App):  h3=10.0.1.1  h4=10.0.1.2\n')
    info('  Zone C (DB):   h5=10.0.2.1  h6=10.0.2.2\n')
    info('*** Type "exit" to stop\n\n')

    CLI(net)   # Opens interactive Mininet CLI

    net.stop()
    info('*** Network stopped\n')

if __name__ == '__main__':
    create_cloud_topology()
