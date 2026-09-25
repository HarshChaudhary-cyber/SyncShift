# SyncShift – FastAPI Backend Scaffolding

Lightweight REST API backend for **SyncShift** (Student / Work Schedule Conflict Assistant).

Built with **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0**, and **Alembic**.

---

## 1. Project Layout

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app factory, CORS, global error handlers
│   ├── config.py             # Pydantic Settings (DATABASE_URL, JWT, CORS)
│   ├── database.py           # SQLAlchemy engine, SessionLocal, Base
│   ├── dependencies.py       # JWT Bearer dependency (CurrentUser extraction)
│   ├── models/               # SQLAlchemy 2.0 ORM models
│   │   ├── __init__.py
│   │   ├── user.py           # User model (timezone, weekly_work_hour_limit)
│   │   ├── course.py         # Course model (code, name, color)
│   │   ├── time_block.py     # TimeBlock model (classes & work shifts)
│   │   ├── block_override.py # BlockOverride model (single-week exceptions)
│   │   └── conflict.py       # Conflict model (persisted overlap log)
│   ├── schemas/              # Pydantic v2 request & response schemas
│   │   ├── __init__.py
│   │   ├── common.py         # DataResponse[T] and ErrorResponse models
│   │   ├── auth.py           # UserRegister, UserLogin, AuthResponseData
│   │   ├── course.py         # CourseCreate, CourseUpdate, CourseOut
│   │   ├── block.py          # BlockCreate, BlockUpdate, BlockOut
│   │   ├── conflict.py       # ConflictItem, WeeklyTotals, ConflictsResponseData
│   │   ├── week.py           # WeekViewData
│   │   └── import_ics.py     # IcsPreviewResponseData, IcsConfirmRequest
│   └── routers/              # Modular API endpoints
│       ├── __init__.py
│       ├── auth.py           # /api/v1/auth
│       ├── courses.py        # /api/v1/courses
│       ├── blocks.py         # /api/v1/blocks
│       ├── conflicts.py      # /api/v1/conflicts
│       ├── week.py           # /api/v1/week
│       └── import_ics.py     # /api/v1/import
├── alembic/                  # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_syncshift_schema.py
├── alembic.ini
├── requirements.txt
├── test_api_endpoints.py     # Comprehensive API route test suite
└── README.md
```

---

## 2. API Endpoints Reference

All routes are mounted under the base URL: **`/api/v1/`**.
Protected endpoints require: `Authorization: Bearer <token>`.

### Auth (`/api/v1/auth`)
| Method | Path | Auth? | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/auth/register` | No | Register new student account (`email`, `password`, `timezone`, `weekly_work_hour_limit`) |
| `POST` | `/auth/login` | No | Authenticate user credentials and return JWT bearer token |
| `GET` | `/auth/me` | **Yes** | Fetch authenticated student profile |

### Courses (`/api/v1/courses`)
| Method | Path | Auth? | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/courses` | **Yes** | List all courses for the student |
| `POST` | `/courses` | **Yes** | Create a course (`code`, `name`, `color`) |
| `PATCH`| `/courses/{course_id}` | **Yes** | Partial update of course fields |
| `DELETE`| `/courses/{course_id}` | **Yes** | Delete course |

### Time Blocks (`/api/v1/blocks`)
| Method | Path | Auth? | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/blocks?week_start=YYYY-MM-DD&type=shift` | **Yes** | List blocks filtered by week and type (`class` or `shift`) |
| `POST` | `/blocks` | **Yes** | Create recurring/single block with date/time validation |
| `PATCH`| `/blocks/{block_id}` | **Yes** | Partial update of block details |
| `DELETE`| `/blocks/{block_id}` | **Yes** | Soft-delete block (`deleted = true`) |
| `POST` | `/blocks/{block_id}/duplicate` | **Yes** | Duplicate block to another day with optional `days_offset` |

### Conflict Engine & Week View
| Method | Path | Auth? | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/conflicts?week_start=YYYY-MM-DD` | **Yes** | Returns conflict pairs + weekly shift/visa work-hour totals |
| `GET` | `/week?start=YYYY-MM-DD` | **Yes** | Single convenience call returning blocks, conflicts, and totals |

### University Timetable Import (`/api/v1/import`)
| Method | Path | Auth? | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/import/ics` | **Yes** | Multipart upload of `.ics` file; returns preview of recurring classes and unmatched events |
| `POST` | `/import/ics/confirm` | **Yes** | Confirms previewed blocks and adds them to calendar without overwriting shifts |

---

## 3. General Envelope Rules

1. **Success Envelope**:
   ```json
   {
     "data": { ... }
   }
   ```
2. **Error Envelope**:
   ```json
   {
     "error": {
       "code": "validation_error",
       "message": "..."
     }
   }
   ```
3. **HTTP 422 Validation Handler**: Automatically intercept Pydantic errors and formats them into `{ "error": { "code": "validation_error", "message": "..." } }`.
4. **Timestamps**: All timestamps follow ISO 8601 UTC representation.

---

## 4. Local Development & Setup

```bash
# 1. Create virtual environment using uv or python
uv venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Apply database migrations (MANDATORY before first start)
# The application enforces Alembic as the single source of truth for schema;
# it will verify migration state on startup and will NOT auto-create tables.
alembic upgrade head

# 4. Start API server
uvicorn app.main:app --reload --port 8000
```

- Interactive OpenAPI Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Interactive ReDoc Docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Probe: [http://localhost:8000/health](http://localhost:8000/health)

---

## 5. Production Security & Environment Variables

When running in production mode (`ENV=production`), the application enforces strict secret validation on startup:

- **JWT Secret Enforcement**: `JWT_SECRET` (and `SECRET_KEY`) **must** be set to a custom value of at least **32 characters**.
- **Refusal to Boot with Dev Defaults**: The application strictly refuses to start if the public development fallback (`syncshift-dev-secret-key-32-chars-minimum!!`) is detected in production. It raises an explicit `RuntimeError` at startup rather than silently signing or verifying tokens with an insecure key.
- **Generate Production Secret**:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- **Local Development**: In non-production environments (`ENV=development`, `ENV=staging`, `ENV=test`), the fallback secret remains active for zero-config local setup.

---

## 6. Running Tests

```bash
pytest -k "not live" -W ignore
```
