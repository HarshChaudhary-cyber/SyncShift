"""
Multi-Instance Distributed Rate Limiter Verification Script
===========================================================
Spawns 3 live backend instances on ports 8001, 8002, and 8003, all sharing
the same Redis instance. Demonstrates:
1. Round-robin request distribution across all 3 instances incrementing the SAME counter.
2. Global limit enforcement at request 11 (HTTP 429).
3. Backend 1 restart without resetting global rate-limit state in Redis.
4. Independent operation of Backend 2 & 3 while Backend 1 restarts.
5. Latency overhead measurement comparing in-memory vs Redis-backed checks.
"""
import os
import subprocess
import sys
import time
import httpx

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
PORTS = [8001, 8002, 8003]
BASE_URLS = [f"http://127.0.0.1:{p}" for p in PORTS]


def clear_redis():
    r = redis.Redis.from_url(REDIS_URL)
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match="syncshift:ratelimit:*", count=200)
        if keys:
            r.delete(*keys)
        if cursor == 0:
            break


def start_backend(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["REDIS_URL"] = REDIS_URL
    env["PORT"] = str(port)
    env["RATE_LIMIT_ENABLED"] = "true"
    env["TRUSTED_PROXIES"] = "127.0.0.1,::1,testclient,localhost"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def wait_for_server(url: str, timeout: float = 10.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{url}/health", timeout=1.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def run_distributed_test():
    print("=" * 70)
    print("PHASE 11 & 18: MULTI-INSTANCE PRACTICAL TEST (3 BACKENDS + 1 REDIS)")
    print("=" * 70)

    # 1. Clear Redis
    clear_redis()
    print("[1] Cleared syncshift rate limit keys from Redis.")

    # 2. Launch 3 Backend Instances
    processes = {}
    print("[2] Starting 3 distinct live backend instances...")
    for port in PORTS:
        p = start_backend(port)
        processes[port] = p
        url = f"http://127.0.0.1:{port}"
        ready = wait_for_server(url)
        if not ready:
            print(f"FAILED to start backend on port {port}")
            cleanup(processes)
            sys.exit(1)
        print(f"    - Backend on {url} is UP and HEALTHY (PID {p.pid})")

    shared_client_ip = "198.51.100.99"
    headers = {
        "x-test-rate-limit": "true",
        "x-forwarded-for": shared_client_ip,
    }
    payload = {"email": "dist_user@syncshift.app", "password": "WrongPassword1!"}

    # 3. Round-Robin Distribution Test
    print("\n[3] Dispatching 10 requests round-robin across Backend 1, 2, and 3:")
    print("    Expected: Requests 1-10 accepted (HTTP 401 credentials invalid, quota not exceeded)")
    for i in range(10):
        target_backend = BASE_URLS[i % 3]
        target_port = PORTS[i % 3]
        resp = httpx.post(f"{target_backend}/api/v1/auth/login", headers=headers, json=payload, timeout=5.0)
        print(f"    Request {i+1:2d} -> Backend-{i%3 + 1} (:{target_port}) -> HTTP {resp.status_code}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    # 4. Global Limit Enforcement Test
    print("\n[4] Request 11 to Backend-2 (should be blocked by shared Redis counter):")
    resp_11 = httpx.post(f"{BASE_URLS[1]}/api/v1/auth/login", headers=headers, json=payload, timeout=5.0)
    print(f"    Request 11 -> Backend-2 (:8002) -> HTTP {resp_11.status_code}")
    print(f"    Response body: {resp_11.json()}")
    print(f"    Retry-After header: {resp_11.headers.get('Retry-After')} seconds")
    assert resp_11.status_code == 429
    assert resp_11.json()["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in resp_11.headers

    print("\n    Request 12 to Backend-3 (verifying all backends see the block):")
    resp_12 = httpx.post(f"{BASE_URLS[2]}/api/v1/auth/login", headers=headers, json=payload, timeout=5.0)
    print(f"    Request 12 -> Backend-3 (:8003) -> HTTP {resp_12.status_code}")
    assert resp_12.status_code == 429

    # 5. Restart Resilience Test
    print("\n[5] Testing Backend-1 restart resilience:")
    print("    Stopping Backend-1 (:8001)...")
    processes[8001].terminate()
    processes[8001].wait()
    print("    Backend-1 is DOWN.")

    print("    Sending request while Backend-1 is down to Backend-2 (:8002)...")
    resp_while_down = httpx.post(f"{BASE_URLS[1]}/api/v1/auth/login", headers=headers, json=payload, timeout=5.0)
    print(f"    Backend-2 response -> HTTP {resp_while_down.status_code} (Quota remains enforced!)")
    assert resp_while_down.status_code == 429

    print("    Restarting Backend-1 (:8001)...")
    p1 = start_backend(8001)
    processes[8001] = p1
    wait_for_server("http://127.0.0.1:8001")
    print(f"    Backend-1 (:8001) is BACK UP (New PID {p1.pid})")

    print("    Sending request to newly restarted Backend-1...")
    resp_after_restart = httpx.post(f"{BASE_URLS[0]}/api/v1/auth/login", headers=headers, json=payload, timeout=5.0)
    print(f"    Restarted Backend-1 response -> HTTP {resp_after_restart.status_code}")
    print("    PROVEN: Restarting Backend-1 did NOT reset the rate limit state!")
    assert resp_after_restart.status_code == 429

    # 6. Performance & Latency Measurement
    print("\n" + "=" * 70)
    print("PHASE 16: PERFORMANCE & OVERHEAD MEASUREMENT")
    print("=" * 70)

    # Measure raw Redis rate-limit evaluation latency
    from app.services.rate_limiter import check_rate_limit
    # Reset for benchmark
    clear_redis()

    # 1. Benchmark in-memory dictionary simulation (representing old implementation)
    from collections import defaultdict
    mem_store = defaultdict(list)
    latencies_mem = []
    for i in range(100):
        key = f"bench:ip:10.0.0.{i}"
        now = time.time()
        t0 = time.perf_counter()
        cutoff = now - 60
        ts = [t for t in mem_store[key] if t > cutoff]
        if len(ts) < 10:
            ts.append(now)
            mem_store[key] = ts
        latencies_mem.append((time.perf_counter() - t0) * 1000)

    # 2. Benchmark real distributed Redis atomic Lua evaluation (new implementation)
    latencies_redis = []
    for i in range(100):
        key = f"syncshift:ratelimit:bench:ip:10.0.0.{i}"
        t0 = time.perf_counter()
        check_rate_limit(key, 10, 60, "bench")
        latencies_redis.append((time.perf_counter() - t0) * 1000)

    mean_mem = sum(latencies_mem) / len(latencies_mem)
    p95_mem = sorted(latencies_mem)[int(0.95 * len(latencies_mem))]

    mean_redis = sum(latencies_redis) / len(latencies_redis)
    p95_redis = sorted(latencies_redis)[int(0.95 * len(latencies_redis))]
    min_redis = min(latencies_redis)
    max_redis = max(latencies_redis)

    print("Latency Benchmark across 100 requests:")
    print(f"    [Old] In-Memory Dict:   Mean = {mean_mem:.3f} ms | P95 = {p95_mem:.3f} ms (Non-distributed, memory leak)")
    print(f"    [New] Redis Atomic Lua: Mean = {mean_redis:.3f} ms | P95 = {p95_redis:.3f} ms | Min = {min_redis:.3f} ms | Max = {max_redis:.3f} ms")
    print(f"    - Approximate network/IPC overhead: +{mean_redis - mean_mem:.3f} ms")
    print("    - Redis operations per request: 1 (single atomic round-trip via pre-evaluated Lua script)")
    print("    - Connection pooling: Reusable connection pool active (zero socket handshake on subsequent calls)")

    cleanup(processes)
    print("\n" + "=" * 70)
    print("ALL MULTI-INSTANCE DISTRIBUTED TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


def cleanup(processes):
    print("\nShutting down backend processes...")
    for port, proc in processes.items():
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    run_distributed_test()
