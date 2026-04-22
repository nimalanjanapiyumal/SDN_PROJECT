#!/usr/bin/env python3
"""iperf3 benchmark helper.

Example:
  h1 python3 tools/iperf3_benchmark.py --vip 10.0.0.100 --port 5201 --duration 15 --parallel 4 --json /tmp/iperf.json
"""

import argparse
import json
import subprocess
import sys
import time


def run_iperf3(vip: str, port: int, duration: int, parallel: int):
    cmd = ['iperf3', '-c', vip, '-p', str(port), '-t', str(duration), '-P', str(parallel), '-J']
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return json.loads(p.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vip', required=True)
    ap.add_argument('--port', type=int, default=5201)
    ap.add_argument('--duration', type=int, default=10)
    ap.add_argument('--parallel', type=int, default=1)
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    try:
        raw = run_iperf3(args.vip, args.port, args.duration, args.parallel)
    except FileNotFoundError:
        print('iperf3 not found. Install with: sudo apt install iperf3', file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f'iperf3 error: {e}', file=sys.stderr)
        sys.exit(1)

    received = raw.get('end', {}).get('sum_received', {}) or {}
    sent = raw.get('end', {}).get('sum_sent', {}) or {}
    bps = float(received.get('bits_per_second') or sent.get('bits_per_second') or 0.0)
    retransmits = sent.get('retransmits')
    payload = {
        'vip': args.vip,
        'port': args.port,
        'duration': args.duration,
        'parallel': args.parallel,
        'throughput_mbps': round(bps / 1_000_000.0, 4),
        'retransmits': retransmits,
        'timestamp': int(time.time()),
    }

    print('=== iperf3 Benchmark ===')
    for k, v in payload.items():
        print(f'{k}: {v}')

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        print(f'JSON written: {args.json}')


if __name__ == '__main__':
    main()
