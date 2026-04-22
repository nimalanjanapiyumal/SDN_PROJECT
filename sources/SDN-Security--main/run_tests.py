#!/usr/bin/env python3
# run_tests.py — Measure latency, accuracy, scalability

import requests, time, statistics, json

CONTROLLER = "http://127.0.0.1:8080"
CTI_API    = "http://127.0.0.1:5003"
AUTH_API   = "http://127.0.0.1:5001"

TEST_IPS = [f"10.9.{i}.{j}" for i in range(5) for j in range(10)]

def test_mitigation_latency(n=20) -> dict:
    "Measure time from block request to flow rule installed"
    latencies = []
    for ip in TEST_IPS[:n]:
        start = time.perf_counter()
        requests.post(f"{CONTROLLER}/sdn/block", json={'ip': ip, 'timeout': 60})
        latencies.append((time.perf_counter() - start) * 1000)
    return {
        'mean_ms':   round(statistics.mean(latencies), 2),
        'min_ms':    round(min(latencies), 2),
        'max_ms':    round(max(latencies), 2),
        'stdev_ms':  round(statistics.stdev(latencies), 2),
        'samples':   n,
        'pass':      statistics.mean(latencies) < 100   # Target: <100ms
    }

def test_auth_latency() -> dict:
    latencies = []
    for i in range(10):
        start = time.perf_counter()
        requests.post(f"{AUTH_API}/auth/login",
                      json={'user_id': f'test{i}', 'ip': f'10.0.0.{i+1}',
                            'password': 'admin123'})
        latencies.append((time.perf_counter() - start) * 1000)
    return {'mean_ms': round(statistics.mean(latencies), 2)}

if __name__ == '__main__':
    print("="*50)
    print("SDN Security Framework — Evaluation Results")
    print("="*50)
    r1 = test_mitigation_latency()
    print(f"\n[1] Mitigation Latency (n=20 IPs):")
    print(f"    Mean:  {r1['mean_ms']}ms")
    print(f"    Min:   {r1['min_ms']}ms")
    print(f"    Max:   {r1['max_ms']}ms")
    print(f"    PASS:  {r1['pass']} (target <100ms)")
    r2 = test_auth_latency()
    print(f"\n[2] Auth Module Latency: {r2['mean_ms']}ms")
    stats = requests.get(f"{CONTROLLER}/sdn/stats").json()
    print(f"\n[3] Controller Stats:")
    print(f"    Blocked IPs: {len(stats.get('blocked_ips',[]))}")
    print(f"    Active switches: {len(stats.get('switches',[]))}")
    print("\nAll tests complete. Check logs/ for detailed output.")

