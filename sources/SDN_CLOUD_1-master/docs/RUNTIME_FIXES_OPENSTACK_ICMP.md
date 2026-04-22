
Updated fixes in this build:
- OpenStack dashboard page can now save local Keystone or OS_CLOUD settings for the dashboard.
- OS_USER_DOMAIN_NAME and OS_PROJECT_DOMAIN_NAME default to Default.
- VIP ping now works through ICMP-aware VIP rewrite rules.
- Mininet diagnostics now show the correct CLI syntax using `sh ovs-vsctl show` and `sh ovs-ofctl -O OpenFlow13 dump-flows s1`.
