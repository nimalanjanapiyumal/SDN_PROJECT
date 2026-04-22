from mininet.topo import Topo


class CloudThreeTierTopo(Topo):
    def build(self):

        # --------------------------
        # 1. CORE LAYER
        # --------------------------
        core = self.addSwitch('s1')

        # --------------------------
        # 2. DISTRIBUTION LAYER
        # --------------------------
        dist1 = self.addSwitch('s2')
        dist2 = self.addSwitch('s3')

        # Connect distribution → core
        self.addLink(dist1, core)
        self.addLink(dist2, core)

        # --------------------------
        # 3. ACCESS LAYER
        # --------------------------
        access1 = self.addSwitch('s4')
        access2 = self.addSwitch('s5')
        access3 = self.addSwitch('s6')

        # Connect access → distribution
        self.addLink(access1, dist1)
        self.addLink(access2, dist1)
        self.addLink(access3, dist2)

        # --------------------------
        # 4. HOSTS (15 total)
        # --------------------------

        # Web tier (6 hosts)
        for i in range(1, 7):
            h = self.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
            self.addLink(h, access1)   # s4

        # App tier (5 hosts)
        for i in range(7, 12):
            h = self.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
            self.addLink(h, access2)   # s5

        # DB tier (4 hosts)
        for i in range(12, 16):
            h = self.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
            self.addLink(h, access3)   # s6


topos = {'cloud': CloudThreeTierTopo}
