# SyncShift Security Hardening, Audit Logging & Privacy Controls

Security and user privacy are foundational pillars of SyncShift. Because scheduling data contains sensitive personal routines, workplace locations, and academic timetables, the system implements defense-in-depth across authentication, authorization, input validation, audit trails, and data sovereignty.

---

## 1. Authentication & JWT Scoping

### Strict User Scoping
- All state-altering and data-retrieval endpoints extract the identity strictly from the verified JWT payload:
  ```python
  current_user: CurrentUser = Depends(get_current_user)
  ```
- **Zero Request-Body Identity Binding**: Even if an attacker injects `{"user_id": "victim-id"}` into the request payload or query parameters, the backend strictly discards or ignores it, executing exclusively against `current_user.user_id`.
- **Token Invalidation & Expiry**: Access tokens are cryptographically signed using HMAC-SHA256 (`HS256`) with a short expiration window (60 minutes). Expired or tampered signatures immediately return `HTTP 401 Unauthorized`.

---

## 2. Insecure Direct Object Reference (IDOR) Defense

SyncShift enforces row-level multi-tenant isolation on all database queries:
- **Block Endpoints (`/blocks/{block_id}`)**:
  ```python
  # IDOR check: returns 404 to avoid leaking existence of another user's block
  if not block or block["user_id"] != current_user.user_id:
      raise HTTPException(status_code=404, detail="Block not found")
  ```
- **Audit Logs (`/audit-logs`)**:
  - Filtered exclusively by `AuditLog.user_id == current_user.user_id`.
  - Normal users have zero visibility into other users' activity or system-level administrative records.
- **Privacy Export (`/privacy/export`)**:
  - Exports exclusively the dataset belonging to `current_user.user_id`.

---

## 3. Rate Limiting

To protect authentication and compute-intensive endpoints (such as LLM assistant chats and timetable parsing) from brute-force or denial-of-service attempts:
- A thread-safe, sliding-window in-memory rate limiter (`backend/app/services/rate_limiter.py`) tracks requests per client IP / user identifier.
- **Rate-Limited Routes**:
  - `POST /api/v1/auth/register`: 10 requests / minute.
  - `POST /api/v1/auth/login`: 15 requests / minute.
  - `POST /api/v1/assistant/chat`: 30 requests / minute.
  - `POST /api/v1/import/upload`: 10 requests / minute.
- Exceeding limits results in `HTTP 429 Too Many Requests` with a descriptive retry message.

---

## 4. File Upload & Timetable Import Security

The timetable import pipeline accepts `.ics`, `.csv`, and image/PDF timetable files:
- **Path Traversal Defense**:
  - Filenames are sanitized using `os.path.basename`.
  - Any filename containing directory traversal sequences (`..`, `/`, `\`) is rejected immediately:
    ```python
    if ".." in original_name or "/" in original_name or "\\" in original_name:
        raise HTTPException(status_code=400, detail="Invalid filename: path traversal characters detected")
    ```
- **Dangerous File Extension Blocking**:
  - Executables and script formats (`.exe`, `.sh`, `.bat`, `.py`, `.cmd`, `.vbs`, etc.) are blocked at the boundary.
- **File Size Clamping**:
  - Maximum upload size is strictly capped at 10 MB (`MAX_FILE_SIZE = 10 * 1024 * 1024`).
- **Memory Streaming**:
  - Files are processed through in-memory streams or isolated temporary directories outside the application runtime path.

---

## 5. Structured Audit Logging

SyncShift maintains an immutable audit trail in the `audit_logs` table:

### Audit Log Schema
```sql
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64),
    entity_id VARCHAR(64),
    description TEXT,
    metadata_json TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Audited Actions
- `LOGIN_SUCCESS`, `LOGIN_FAILED`, `REGISTER_SUCCESS`
- `BLOCK_CREATED`, `BLOCK_UPDATED`, `BLOCK_DELETED`
- `TIMETABLE_IMPORTED`
- `AI_ACTION_CONFIRMED`
- `SETTINGS_UPDATED`
- `ACCOUNT_DELETED`

### Data Sanitization
Before writing to `metadata_json`, the audit service scrubs all sensitive keywords:
- `password`, `token`, `secret`, `api_key`, `authorization` are redacted.

---

## 6. Privacy Center & Data Sovereignty

Located under **Settings → Security & Privacy**:
- **Right to Access (`GET /api/v1/privacy/export`)**:
  - Generates a complete JSON archive of the user's profile, courses, calendar blocks, recurring rules, study goals, notification settings, and personal audit history.
  - **Excludes**: Password hashes, JWT secrets, AI system prompts, and server configuration.
- **Right to Erasure (`POST /api/v1/privacy/delete-account`)**:
  - Soft-deletes user record (`is_active = False`).
  - Sets `deleted_at = datetime.utcnow()`.
  - Removes push notification tokens and invalidates subsequent login attempts.

---

## 7. HTTP Security Headers

FastAPI's security header middleware enforces standard defenses on all responses:
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing attacks.
- `X-Frame-Options: DENY`: Prevents clickjacking within iframes.
- `Referrer-Policy: strict-origin-when-cross-origin`: Controls referrer data leakage across origins.
- Production HTTPS deployments include `Strict-Transport-Security` (HSTS).
