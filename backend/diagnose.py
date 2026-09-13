"""
SyncShift Backend – Diagnostic Script
Run with: python diagnose.py
(No server running? It will tell you that too.)
"""
import sys
import socket
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Try to import httpx (bundled in requirements.txt) ──────────────────────
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

BASE_URL = "http://localhost:8000"
REACT_ORIGIN = "http://localhost:3000"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def check(label: str, ok: bool, detail: str = ""):
    icon = PASS if ok else FAIL
    print(f"  {icon}  {label}")
    if detail:
        for line in detail.splitlines():
            print(f"         {line}")


# ──────────────────────────────────────────────────────────────────────────
section("1 · Port 8000 – Is the server running?")
# ──────────────────────────────────────────────────────────────────────────
try:
    sock = socket.create_connection(("localhost", 8000), timeout=2)
    sock.close()
    port_open = True
    check("Port 8000 is open", True)
except OSError:
    port_open = False
    check("Port 8000 is open", False,
          "Nothing is listening on port 8000.\n"
          "Start the server with:  startup.bat\n"
          "  –or–  .venv\\Scripts\\uvicorn app.main:app --reload")


# ──────────────────────────────────────────────────────────────────────────
section("2 · HTTP – /health endpoint")
# ──────────────────────────────────────────────────────────────────────────
if not port_open:
    print(f"  {WARN}  Skipped (server not reachable)")
elif not HAS_HTTPX:
    print(f"  {WARN}  httpx not installed – run: pip install httpx")
else:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        check(
            f"GET /health → {r.status_code}",
            ok,
            str(r.json()) if not ok else "",
        )
    except Exception as e:
        check("GET /health", False, str(e))


# ──────────────────────────────────────────────────────────────────────────
section("3 · CORS – preflight from React origin")
# ──────────────────────────────────────────────────────────────────────────
if not port_open:
    print(f"  {WARN}  Skipped (server not reachable)")
elif not HAS_HTTPX:
    print(f"  {WARN}  httpx not installed")
else:
    try:
        r = httpx.options(
            f"{BASE_URL}/health",
            headers={
                "Origin": REACT_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
            timeout=5,
        )
        acao = r.headers.get("access-control-allow-origin", "")
        acac = r.headers.get("access-control-allow-credentials", "")

        origin_ok = acao in (REACT_ORIGIN, "*")
        creds_ok = acac.lower() == "true"

        check(
            f"Access-Control-Allow-Origin: {acao or '(missing)'}",
            origin_ok,
            "" if origin_ok else f"Expected '{REACT_ORIGIN}' or '*'",
        )
        check(
            f"Access-Control-Allow-Credentials: {acac or '(missing)'}",
            creds_ok,
            "" if creds_ok else "Expected 'true'",
        )
    except Exception as e:
        check("CORS preflight", False, str(e))


# ──────────────────────────────────────────────────────────────────────────
section("4 · Routers – key endpoint smoke test")
# ──────────────────────────────────────────────────────────────────────────
PROBE_ENDPOINTS = [
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/courses"),
    ("GET", "/api/v1/blocks"),
]
if not port_open:
    print(f"  {WARN}  Skipped (server not reachable)")
elif not HAS_HTTPX:
    print(f"  {WARN}  httpx not installed")
else:
    for method, path in PROBE_ENDPOINTS:
        try:
            fn = getattr(httpx, method.lower())
            r = fn(f"{BASE_URL}{path}", timeout=5)
            # 401 is fine (needs auth), 404 means route missing
            ok = r.status_code != 404
            check(
                f"{method} {path} → {r.status_code}",
                ok,
                "" if ok else "Route not found – check router registration",
            )
        except Exception as e:
            check(f"{method} {path}", False, str(e))


# ──────────────────────────────────────────────────────────────────────────
section("5 · Dependencies – import check")
# ──────────────────────────────────────────────────────────────────────────
DEPS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "sqlalchemy": "sqlalchemy",
    "jose": "python-jose",
    "passlib": "passlib",
    "multipart": "python-multipart",
    "icalendar": "icalendar",
}
for mod, pkg in DEPS.items():
    try:
        __import__(mod)
        check(f"import {mod}  ({pkg})", True)
    except ImportError:
        check(f"import {mod}  ({pkg})", False,
              f"Install with: pip install {pkg}")


# ──────────────────────────────────────────────────────────────────────────
section("Summary")
# ──────────────────────────────────────────────────────────────────────────
if not port_open:
    print("""
  The server is NOT running. Fix this first:

  Option A – double-click:
      startup.bat

  Option B – PowerShell:
      cd backend
      .venv\\Scripts\\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  Then re-run this script:
      python diagnose.py
""")
else:
    print("\n  Server is up. Review any ❌ items above.\n")
