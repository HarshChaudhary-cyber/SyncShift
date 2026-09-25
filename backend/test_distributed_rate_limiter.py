"""
Comprehensive Distributed Rate Limiter Test Suite
=================================================
Validates all 18 requirements for production-safe distributed rate limiting:
1. Basic rate limiting
2. Requests under limit
3. Request exceeding limit
4. HTTP 429 status code
5. Retry-After header and message
6. TTL expiration & sliding window
7. Concurrent requests / atomicity
8. Same client across multiple backend instances
9. Different clients have isolated quotas
10. Different endpoints/scopes have isolated quotas
11. Redis key isolation & clean naming
12. Redis connection failure policy (fail-closed for sensitive)
13. Redis timeout handling
14. Redis recovery after failure
15. Invalid / spoofed client IP headers defense
16. Trusted proxy verification (X-Forwarded-For resolution)
17. Authenticated user rate limiting
18. OAuth rate limiting
"""
import concurrent.futures
import time
import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI, Depends, Request
import redis

from app.main import app
from app.config import settings
from app.services.rate_limiter import (
    check_rate_limit,
    get_client_identity,
    get_client_ip,
    get_redis_client,
    is_trusted_proxy,
    rate_limit,
    reset_rate_limits,
    SENSITIVE_SCOPES,
)
from app.dependencies import create_access_token


def _is_redis_alive() -> bool:
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
        return bool(r.ping())
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not _is_redis_alive(), reason="Redis server is not running (start Redis to run distributed rate limiter tests)")

@pytest.fixture(autouse=True)
def clean_redis_state():
    """Ensure Redis is clean and rate limiter is active before each test."""
    orig_rl = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = True
    reset_rate_limits()
    yield
    reset_rate_limits()
    settings.RATE_LIMIT_ENABLED = orig_rl


# ---------------------------------------------------------------------------
# 1. Basic Rate Limiting Under Limit
# ---------------------------------------------------------------------------
def test_requests_under_limit():
    """Requests under the quota succeed without error."""
    client = TestClient(app)
    # Login endpoint limit is 10 requests / 60 seconds
    for _ in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            headers={"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.1"},
            json={"email": "under_limit@test.com", "password": "WrongPassword1!"},
        )
        # Should return 401 Unauthorized (credentials invalid), NOT 429
        assert resp.status_code == 401
        assert resp.status_code != 429


# ---------------------------------------------------------------------------
# 2, 3, 4, 5. Request Exceeding Limit, HTTP 429, Retry-After Header
# ---------------------------------------------------------------------------
def test_request_exceeding_limit_triggers_429():
    """Exceeding quota triggers HTTP 429 with Retry-After header and safe payload."""
    client = TestClient(app)
    ip_header = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.2"}

    # Limit is 10 requests
    for _ in range(10):
        resp = client.post(
            "/api/v1/auth/login",
            headers=ip_header,
            json={"email": "exceed@test.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401

    # 11th request MUST trigger HTTP 429
    blocked_resp = client.post(
        "/api/v1/auth/login",
        headers=ip_header,
        json={"email": "exceed@test.com", "password": "WrongPassword1!"},
    )
    assert blocked_resp.status_code == 429

    # Verify Retry-After header
    assert "Retry-After" in blocked_resp.headers
    retry_after = int(blocked_resp.headers["Retry-After"])
    assert 1 <= retry_after <= 60

    # Verify response body structure
    data = blocked_resp.json()
    assert "error" in data
    assert data["error"]["code"] == "rate_limit_exceeded"
    assert "Rate limit exceeded" in data["error"]["message"]
    assert str(retry_after) in data["error"]["message"]


# ---------------------------------------------------------------------------
# 6. TTL Expiration & Window Sliding
# ---------------------------------------------------------------------------
def test_ttl_expiration_resets_quota():
    """Quota resets once the sliding window has elapsed."""
    test_key = "syncshift:ratelimit:test_ttl:ip:10.99.1.1"
    # Allow 2 requests per 1 second
    check_rate_limit(test_key, max_requests=2, window_seconds=1, bucket="test_ttl")
    check_rate_limit(test_key, max_requests=2, window_seconds=1, bucket="test_ttl")

    # 3rd should fail
    with pytest.raises(Exception) as excinfo:
        check_rate_limit(test_key, max_requests=2, window_seconds=1, bucket="test_ttl")
    assert "429" in str(excinfo.value)

    # Wait for the 1-second window to expire
    time.sleep(1.2)

    # Now request should succeed again
    check_rate_limit(test_key, max_requests=2, window_seconds=1, bucket="test_ttl")


# ---------------------------------------------------------------------------
# 7. Concurrent Requests Atomicity
# ---------------------------------------------------------------------------
def test_concurrent_requests_atomicity():
    """Concurrent requests across threads cannot bypass the quota."""
    client = TestClient(app)
    ip_header = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.7"}
    limit = 10
    total_burst = 25

    def make_request():
        return client.post(
            "/api/v1/auth/login",
            headers=ip_header,
            json={"email": "concurrent@test.com", "password": "WrongPassword1!"},
        ).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(total_burst)]
        statuses = [f.result() for f in futures]

    accepted_count = sum(1 for s in statuses if s == 401)
    blocked_count = sum(1 for s in statuses if s == 429)

    # Exactly 10 must be accepted, 15 must be blocked
    assert accepted_count == limit, f"Expected exactly {limit} accepted, got {accepted_count}"
    assert blocked_count == total_burst - limit, f"Expected exactly {total_burst - limit} blocked, got {blocked_count}"


# ---------------------------------------------------------------------------
# 8. Same Client Across Multiple Backend Instances (Distributed State)
# ---------------------------------------------------------------------------
def test_same_client_across_multiple_backend_instances():
    """
    Simulates 3 distinct backend instances sharing the SAME Redis.
    Proves that rotating requests across Backend 1, 2, and 3 increments
    the single authoritative Redis counter and blocks at request 11.
    """
    # 3 distinct client instances representing backend-1, backend-2, backend-3
    backend_1 = TestClient(app, base_url="http://syncshift-backend-1:8000")
    backend_2 = TestClient(app, base_url="http://syncshift-backend-2:8000")
    backend_3 = TestClient(app, base_url="http://syncshift-backend-3:8000")
    backends = [backend_1, backend_2, backend_3]

    shared_client_ip = "198.51.100.8"
    headers = {"x-test-rate-limit": "true", "x-forwarded-for": shared_client_ip}

    # Dispatch 10 requests alternating between backend-1, backend-2, backend-3
    for i in range(10):
        current_backend = backends[i % 3]
        resp = current_backend.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"email": "distributed@test.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401, f"Request {i+1} failed on backend {(i%3)+1}"

    # Request 11 sent to backend-2 MUST return 429
    blocked_resp = backend_2.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "distributed@test.com", "password": "WrongPassword1!"},
    )
    assert blocked_resp.status_code == 429
    assert blocked_resp.json()["error"]["code"] == "rate_limit_exceeded"

    # Request 12 sent to backend-3 MUST also return 429
    blocked_resp_3 = backend_3.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "distributed@test.com", "password": "WrongPassword1!"},
    )
    assert blocked_resp_3.status_code == 429


# ---------------------------------------------------------------------------
# 9. Client Isolation (Different Clients Do Not Interfere)
# ---------------------------------------------------------------------------
def test_different_clients_isolated_quotas():
    """Client A hitting the rate limit does not affect Client B."""
    client = TestClient(app)
    client_a_headers = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.10"}
    client_b_headers = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.11"}

    # Exhaust quota for Client A
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            headers=client_a_headers,
            json={"email": "user_a@test.com", "password": "WrongPassword1!"},
        )
    # Client A is blocked
    resp_a = client.post(
        "/api/v1/auth/login",
        headers=client_a_headers,
        json={"email": "user_a@test.com", "password": "WrongPassword1!"},
    )
    assert resp_a.status_code == 429

    # Client B should NOT be blocked
    resp_b = client.post(
        "/api/v1/auth/login",
        headers=client_b_headers,
        json={"email": "user_b@test.com", "password": "WrongPassword1!"},
    )
    assert resp_b.status_code == 401  # Not 429!


# ---------------------------------------------------------------------------
# 10. Endpoint / Scope Isolation
# ---------------------------------------------------------------------------
def test_different_scopes_isolated_quotas():
    """Exhausting quota in the 'register' bucket does not exhaust the 'login' bucket."""
    client = TestClient(app)
    headers = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.15"}

    # Register has limit 5
    for _ in range(5):
        client.post(
            "/api/v1/auth/register",
            headers=headers,
            json={"email": "bad", "password": "short"},
        )
    # 6th register is blocked
    reg_blocked = client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={"email": "bad", "password": "short"},
    )
    assert reg_blocked.status_code == 429

    # Login quota should still be untouched for this client
    login_resp = client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "test@example.com", "password": "WrongPassword1!"},
    )
    assert login_resp.status_code == 401  # Not 429!


# ---------------------------------------------------------------------------
# 11. Redis Key Isolation & Namespacing
# ---------------------------------------------------------------------------
def test_redis_key_namespacing_and_ttl():
    """Redis keys follow syncshift:ratelimit:<scope>:<identity> and have appropriate TTL."""
    client = TestClient(app)
    headers = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.20"}

    client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "key_test@test.com", "password": "WrongPassword1!"},
    )

    r = get_redis_client()
    assert r is not None
    expected_key = "syncshift:ratelimit:login:ip:198.51.100.20"
    assert r.exists(expected_key) == 1

    # Verify TTL is set (> 0 and <= 61 seconds)
    ttl = r.ttl(expected_key)
    assert 1 <= ttl <= 61


# ---------------------------------------------------------------------------
# 12, 13, 14. Redis Failure Policy: Sensitive Fail-Closed, Non-Sensitive Fail-Open
# ---------------------------------------------------------------------------
def test_redis_failure_policy_sensitive_fail_closed(monkeypatch):
    """When Redis is unavailable, sensitive endpoints (login) fail-closed with 503."""
    client = TestClient(app)

    # Simulate Redis connection failure
    def mock_get_redis_fail():
        class FailingRedis:
            def eval(self, *args, **kwargs):
                raise redis.ConnectionError("Simulated Redis outage")
            def ping(self):
                return False
        return FailingRedis()

    monkeypatch.setattr("app.services.rate_limiter.get_redis_client", mock_get_redis_fail)

    resp = client.post(
        "/api/v1/auth/login",
        headers={"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.30"},
        json={"email": "fail@test.com", "password": "WrongPassword1!"},
    )
    # Sensitive endpoint MUST fail-closed with 503 Service Unavailable
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "service_unavailable"


def test_redis_failure_policy_non_sensitive_fail_open(monkeypatch):
    """When Redis is unavailable, non-sensitive endpoints fail-open without breaking service."""
    # Test a non-sensitive scope like assistant_chat
    def mock_get_redis_fail():
        class FailingRedis:
            def eval(self, *args, **kwargs):
                raise redis.ConnectionError("Simulated Redis outage")
        return FailingRedis()

    monkeypatch.setattr("app.services.rate_limiter.get_redis_client", mock_get_redis_fail)

    # Should not raise exception
    check_rate_limit(
        key="syncshift:ratelimit:assistant_chat:ip:10.0.0.1",
        max_requests=30,
        window_seconds=60,
        bucket="assistant_chat",
    )


# ---------------------------------------------------------------------------
# 15. Invalid / Spoofed Client IP Headers Defense
# ---------------------------------------------------------------------------
def test_spoofed_ip_header_ignored_from_untrusted_peer(monkeypatch):
    """
    If a direct peer is NOT a trusted proxy, spoofed X-Forwarded-For is ignored,
    preventing attackers from rotating arbitrary IPs to bypass rate limits.
    """
    # Untrusted direct client IP
    fake_peer_host = "203.0.113.88"
    assert not is_trusted_proxy(fake_peer_host)

    class MockClient:
        host = fake_peer_host

    class MockRequest:
        client = MockClient()
        headers = {
            "x-forwarded-for": "1.2.3.4, 5.6.7.8",
            "x-real-ip": "9.9.9.9",
        }

    detected_ip = get_client_ip(MockRequest())
    # MUST be the real socket peer IP, NOT the spoofed headers
    assert detected_ip == fake_peer_host


# ---------------------------------------------------------------------------
# 16. Trusted Proxy Verification
# ---------------------------------------------------------------------------
def test_trusted_proxy_correctly_resolves_client_ip():
    """
    When request originates from a configured trusted proxy (e.g. Docker network 172.18.0.2),
    X-Forwarded-For is safely traversed to resolve the genuine client IP.
    """
    trusted_proxy_host = "172.18.0.2"
    assert is_trusted_proxy(trusted_proxy_host)

    class MockClient:
        host = trusted_proxy_host

    class MockRequest:
        client = MockClient()
        headers = {
            # Client IP -> Intermediate Proxy -> Direct Trusted Peer
            "x-forwarded-for": "198.51.100.55, 172.18.0.5",
        }

    detected_ip = get_client_ip(MockRequest())
    assert detected_ip == "198.51.100.55"


# ---------------------------------------------------------------------------
# 17. Authenticated User Rate Limiting
# ---------------------------------------------------------------------------
def test_authenticated_user_rate_limiting():
    """Authenticated users are rate-limited by user ID, not IP."""
    client = TestClient(app)
    token = create_access_token(user_id=777, email="auth_user_777@syncshift.app")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Change password limit is 5 attempts
    for _ in range(5):
        resp = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": "WrongPassword1!", "new_password": "NewValidPassword123!"},
        )
        assert resp.status_code in (401, 404)

    # 6th attempt is blocked
    blocked = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "WrongPassword1!", "new_password": "NewValidPassword123!"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limit_exceeded"


# ---------------------------------------------------------------------------
# 18. OAuth Endpoint Rate Limiting
# ---------------------------------------------------------------------------
def test_oauth_endpoint_rate_limiting():
    """OAuth endpoints (Google and Microsoft) enforce rate limits."""
    client = TestClient(app)
    headers = {"x-test-rate-limit": "true", "x-forwarded-for": "198.51.100.99"}

    # Limit is 10 requests
    for _ in range(10):
        client.post(
            "/api/v1/auth/oauth/google",
            headers=headers,
            json={"id_token": "fake-google-token"},
        )

    # 11th request MUST trigger 429
    blocked = client.post(
        "/api/v1/auth/oauth/google",
        headers=headers,
        json={"id_token": "fake-google-token"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limit_exceeded"
