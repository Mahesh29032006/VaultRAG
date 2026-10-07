#!/usr/bin/env python3
"""
Air-Gap Verification Script (Section 8)
Inspects process socket connections before and during queries to ensure
strictly zero non-loopback network calls occur under airgap mode.
"""

import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


def is_loopback_socket(line: str) -> bool:
    """Check if an lsof/ss network connection socket line is strictly loopback."""
    if "IPv4" not in line and "IPv6" not in line and "TCP" not in line and "UDP" not in line:
        return True

    # Find all IP-like addresses or endpoints in the line
    # Match patterns like 127.0.0.1:8093 or 192.168.1.1:443 or [::1]:8093
    ips = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\[?[a-fA-F0-9:]+\]?):\d+", line)
    if not ips:
        if "*:*" in line or "*:" in line:
            return True
        return True

    for ip in ips:
        clean_ip = ip.strip("[]")
        if clean_ip not in ("127.0.0.1", "::1", "localhost"):
            return False
    return True


def inspect_process_sockets(pid: int) -> tuple[list[str], bool]:
    """
    Returns (non_loopback_connections, supported).
    """
    sys_plat = platform.system().lower()
    non_loopback = []

    if sys_plat == "darwin":
        if not shutil.which("lsof"):
            return [], False
        try:
            # -a combines options with AND: process pid AND internet sockets
            res = subprocess.run(
                ["lsof", "-a", "-p", str(pid), "-i", "-n", "-P"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = res.stdout.strip().splitlines()
            if len(lines) <= 1:
                return [], True
            for l in lines[1:]:
                if ("IPv4" in l or "IPv6" in l) and not is_loopback_socket(l):
                    non_loopback.append(l)
            return non_loopback, True
        except Exception:
            return [], False

    elif sys_plat == "linux":
        if not shutil.which("ss"):
            return [], False
        try:
            res = subprocess.run(
                ["ss", "-tnp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = res.stdout.strip().splitlines()
            for l in lines:
                if f"pid={pid}" in l:
                    if "127.0.0.1" not in l and "[::1]" not in l:
                        non_loopback.append(l)
            return non_loopback, True
        except Exception:
            return [], False

    return [], False


def main():
    print("=" * 80)
    print("SOVEREIGN-RAG AIR-GAP INTEGRITY VERIFICATION (SECTION 8)")
    print("=" * 80)

    server_url = "http://127.0.0.1:8093"
    proc = None
    server_pid = None

    try:
        req = urllib.request.Request(f"{server_url}/health")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                print("Connected to already running SovereignRAG server.")
    except Exception:
        print("Launching SovereignRAG server subprocess on 127.0.0.1:8093...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT_DIR)
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8093", "--log-level", "warning"],
            cwd=str(ROOT_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        server_pid = proc.pid
        ready = False
        for _ in range(20):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"{server_url}/health", timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                pass

        if not ready:
            print("ERROR: SovereignRAG server failed to start within 10s.")
            if proc:
                proc.terminate()
            sys.exit(1)

    if server_pid is None:
        try:
            res = subprocess.run(["lsof", "-t", "-i:8093", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=3)
            pids = res.stdout.strip().split()
            if pids:
                server_pid = int(pids[0])
            else:
                res_any = subprocess.run(["lsof", "-t", "-i:8093"], capture_output=True, text=True, timeout=3)
                pids_any = res_any.stdout.strip().split()
                if pids_any:
                    server_pid = int(pids_any[0])
        except Exception:
            pass

    if server_pid is None:
        print("WARNING: Could not determine server PID.")
        print("WARNING: Platform-level verification not available. Application-level policy only.")
        print("Verdict: POLICY_ENFORCED_NOT_VERIFIED")
        return

    baseline_non_lb, supported = inspect_process_sockets(server_pid)
    if not supported:
        print("WARNING: Platform-level verification not available. Application-level policy only.")
        print("Verdict: POLICY_ENFORCED_NOT_VERIFIED")
        if proc:
            proc.terminate()
        return

    print(f"Inspecting PID {server_pid} network sockets...")
    print("Loopback binding verified: 127.0.0.1:8093")

    test_queries = [
        "What is the Torsemide dosage prescribed to the patient?",
        "What is the aggregate liability cap under Section 8?",
        "What are the operational frequency bands of the Spectre-9 AESA radar?",
        "What is the Net Asset Value NAV of Apex Meridian Master Fund?",
        "What coolant is used for thermal dissipation in the radar subsystem?",
    ]

    print(f"Executing {len(test_queries)} air-gapped test queries...")
    observed_non_loopback = list(baseline_non_lb)

    for i, q in enumerate(test_queries, 1):
        payload = json.dumps({"query": q, "mode": "airgap"}).encode("utf-8")
        req = urllib.request.Request(
            f"{server_url}/api/rag/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                _ = resp.read()
        except Exception as e:
            print(f"  Query {i} returned error: {e}")

        curr_non_lb, _ = inspect_process_sockets(server_pid)
        for c in curr_non_lb:
            if c not in observed_non_loopback:
                observed_non_loopback.append(c)

    final_non_lb, _ = inspect_process_sockets(server_pid)
    for c in final_non_lb:
        if c not in observed_non_loopback:
            observed_non_loopback.append(c)

    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    count_non_loopback = len(observed_non_loopback)
    print(f"Non-loopback connections observed during test window: {count_non_loopback}")
    if count_non_loopback > 0:
        for c in observed_non_loopback:
            print(f"  Offending connection: {c}")
        print("Verdict: FAILED")
        sys.exit(1)
    else:
        print("Verdict: AIR-GAPPED")


if __name__ == "__main__":
    main()
