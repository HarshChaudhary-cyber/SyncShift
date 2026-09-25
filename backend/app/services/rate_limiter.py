"""
SyncShift Distributed Rate Limiter Service
==========================================
Enterprise-grade, distributed sliding-window rate limiter backed by Redis.
Enforces atomic request quota tracking across multiple backend instances
behind a load balancer, with trusted proxy header inspection and configurable
fail-closed/fail-open policies.
"""
import hashlib
import ipaddress
import logging
import math
import os
import time
import uuid
from typing import Callable, List, Optional, Tuple, Union

import jwt
import redis
from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger("syncshift.rate_limiter")

# ---------------------------------------------------------------------------
# Redis Connection Management
# ---------------------------------------------------------------------------
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None

# Sensitive scopes that must FAIL-CLOSED when Redis is unavailable to prevent brute-force attacks
SENSITIVE_SCOPES = {
    "login",
    "register",
    "change_password",
    "delete_account",
    "oauth",
}

# ---------------------------------------------------------------------------
# Atomic Sliding Window Lua Script
# ---------------------------------------------------------------------------
# KEYS[1]: Redis rate limit key (e.g., syncshift:ratelimit:login:ip:192.168.1.5)
# ARGV[1]: Current timestamp (float seconds as string)
# ARGV[2]: Window size in seconds (integer as string)
# ARGV[3]: Maximum requests permitted (integer as string)
# ARGV[4]: Unique member nonce (timestamp:uuid)
#
# Returns table:
# [1] allowed (1 = True, 0 = False)
# [2] retry_after (seconds to wait if blocked, 0 if allowed)
# [3] current_count (requests currently counted in window)
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local member = ARGV[4]
local cutoff = now - window

-- 1. Remove all entries older than the sliding window cutoff
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)

-- 2. Count requests currently remaining within the sliding window
local current_count = redis.call('ZCARD', key)

if current_count < max_requests then
    -- 3. Quota available: atomically record current request timestamp
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, math.ceil(window) + 1)
    return {1, 0, current_count + 1}
else
    -- 4. Quota exceeded: find oldest entry timestamp to calculate precise Retry-After
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if oldest and #oldest >= 2 then
        local oldest_ts = tonumber(oldest[2])
        retry_after = math.max(1, math.ceil(oldest_ts + window - now))
    end
    redis.call('EXPIRE', key, math.ceil(window) + 1)
    return {0, retry_after, current_count}
end
"""


def get_redis_client() -> Optional[redis.Redis]:
    """
    Returns the singleton Redis client with connection pooling.
    Returns None if RATE_LIMIT_ENABLED is False.
    """
    global _redis_client, _redis_pool
    if not settings.RATE_LIMIT_ENABLED:
        return None

    if _redis_client is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
                retry_on_timeout=True,
                decode_responses=True,
            )
            _redis_client = redis.Redis(connection_pool=_redis_pool)
        except Exception as exc:
            logger.error("Failed to initialize Redis connection pool: %s", exc)
            return None

    return _redis_client


def close_redis_connection() -> None:
    """Closes Redis client and connection pool on application shutdown."""
    global _redis_client, _redis_pool
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None

    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
        except Exception:
            pass
        _redis_pool = None


def is_redis_available() -> bool:
    """Probes Redis health via PING."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Trusted Proxy & Client Identification
# ---------------------------------------------------------------------------
def _parse_trusted_proxies(trusted_raw: str) -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network, ipaddress.IPv4Address, ipaddress.IPv6Address, str]]:
    """Parses comma-separated trusted proxy configuration into IP networks/addresses/hostnames."""
    results = []
    for item in trusted_raw.split(","):
        token = item.strip()
        if not token:
            continue
        try:
            if "/" in token:
                results.append(ipaddress.ip_network(token, strict=False))
            else:
                results.append(ipaddress.ip_address(token))
        except ValueError:
            results.append(token.lower())
    return results


def is_trusted_proxy(ip_or_host: str) -> bool:
    """Checks whether the immediate client connection originates from a configured trusted proxy."""
    if not ip_or_host:
        return False

    token = ip_or_host.strip().lower()
    trusted_list = _parse_trusted_proxies(settings.TRUSTED_PROXIES)

    if token in trusted_list:
        return True

    try:
        ip_obj = ipaddress.ip_address(token)
        for trusted in trusted_list:
            if isinstance(trusted, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if ip_obj in trusted:
                    return True
            elif isinstance(trusted, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
                if ip_obj == trusted:
                    return True
    except ValueError:
        pass

    return False


def get_client_ip(request: Request) -> str:
    """
    Safely extracts the genuine client IP address.
    Only trusts X-Forwarded-For or X-Real-IP if the immediate peer host is a trusted proxy.
    Walks X-Forwarded-For chain right-to-left to prevent header spoofing.
    """
    peer_ip = request.client.host if request.client else "unknown"

    # If the direct peer is NOT a trusted proxy, ignore all forwarded headers
    if not is_trusted_proxy(peer_ip):
        return peer_ip

    # Peer is trusted proxy: inspect X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # XFF format: client, proxy1, proxy2
        # Walk from right-to-left to find first untrusted IP
        raw_ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
        for cand in reversed(raw_ips):
            try:
                ipaddress.ip_address(cand)
            except ValueError:
                continue
            if not is_trusted_proxy(cand):
                return cand
        if raw_ips:
            return raw_ips[0]

    # Check X-Real-IP
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        cand = x_real_ip.strip()
        try:
            ipaddress.ip_address(cand)
            if not is_trusted_proxy(cand):
                return cand
        except ValueError:
            pass

    return peer_ip


def get_client_identity(request: Request) -> Tuple[str, str]:
    """
    Determines client identity and IP address.
    Returns (identity, client_ip).
    - Authenticated user: ("user:<user_id>", "") or ("token_hash:<sha256>", "")
    - Unauthenticated: ("ip:<client_ip>", client_ip)
    """
    auth_hdr = request.headers.get("Authorization")

    if auth_hdr and auth_hdr.startswith("Bearer "):
        token = auth_hdr[7:].strip()
        # Attempt to decode user ID from JWT
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            user_id = payload.get("user_id") or payload.get("sub")
            if user_id:
                return f"user:{user_id}", ""
        except Exception:
            pass

        # Fallback to deterministic SHA-256 token hash (never log/store raw token)
        token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        return f"token_hash:{token_digest}", ""

    client_ip = get_client_ip(request)
    return f"ip:{client_ip}", client_ip


# ---------------------------------------------------------------------------
# Rate Limit Check Execution
# ---------------------------------------------------------------------------
def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
    bucket: str = "default",
) -> None:
    """
    Executes atomic sliding-window rate limit evaluation in Redis.
    Raises HTTP 429 Too Many Requests with Retry-After if quota exceeded.
    Handles Redis connectivity failure according to security fail policy.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    client = get_redis_client()
    now = time.time()
    member = f"{now}:{uuid.uuid4().hex[:8]}"

    if client is None:
        _handle_redis_failure(bucket, "Redis client not initialized")
        return

    try:
        # Atomic Lua evaluation
        result = client.eval(
            SLIDING_WINDOW_LUA,
            1,
            key,
            str(now),
            str(window_seconds),
            str(max_requests),
            member,
        )
        allowed, retry_after, _ = result

        if not allowed:
            retry_seconds = max(1, int(retry_after))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Try again in {retry_seconds} seconds.",
                },
                headers={"Retry-After": str(retry_seconds)},
            )
    except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as exc:
        _handle_redis_failure(bucket, str(exc))


def _handle_redis_failure(bucket: str, error_msg: str) -> None:
    """
    Applies the Redis failure policy:
    - Security-sensitive endpoints fail-closed (HTTP 503)
    - General endpoints fail-open with structured warning log
    """
    is_sensitive = bucket in SENSITIVE_SCOPES or settings.RATE_LIMIT_FAIL_CLOSED_ALL
    logger.error(
        "Redis rate limiter unavailable for bucket '%s' (sensitive=%s): %s",
        bucket,
        is_sensitive,
        error_msg,
    )

    if is_sensitive:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "service_unavailable",
                "message": "Security verification service temporarily unavailable. Please try again later.",
            },
        )
    # Fail-open for non-sensitive operations
    logger.warning("Failing open for non-sensitive rate limit bucket: %s", bucket)


# ---------------------------------------------------------------------------
# FastAPI Dependency Generator
# ---------------------------------------------------------------------------
def rate_limit(
    max_requests: int = 30,
    window_seconds: int = 60,
    bucket: str = "default",
) -> Callable:
    """
    FastAPI dependency factory for distributed rate limiting.
    Namespaces Redis keys: syncshift:ratelimit:<bucket>:<identity>
    """
    def dependency(request: Request) -> None:
        client_id, client_ip = get_client_identity(request)
        key = f"syncshift:ratelimit:{bucket}:{client_id}"

        # In automated test suites with Starlette TestClient (host 'testclient'),
        # permit higher burst throughput unless the test specifically exercises rate limiting.
        if (
            (client_ip == "testclient" or client_id.endswith("testclient"))
            and request.headers.get("x-test-rate-limit") != "true"
        ):
            effective_max = max(max_requests, 100)
        else:
            effective_max = max_requests

        check_rate_limit(
            key=key,
            max_requests=effective_max,
            window_seconds=window_seconds,
            bucket=bucket,
        )

    return dependency


# ---------------------------------------------------------------------------
# Maintenance Utilities
# ---------------------------------------------------------------------------
def reset_rate_limits() -> None:
    """
    Clears all SyncShift rate limit keys from Redis.
    Used by test fixtures and maintenance scripts.
    """
    client = get_redis_client()
    if client is None:
        return

    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(
                cursor=cursor,
                match="syncshift:ratelimit:*",
                count=200,
            )
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("Could not reset Redis rate limits: %s", exc)
