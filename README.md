# SyncShift – Student / Work Schedule Conflict Assistant

> _A lightweight personal scheduling assistant that helps students who also work manage class timetables and work shifts without hidden conflicts._

---

## Problem

<!-- TODO: Insert a concise description of the problem this app solves. -->

- University portals export raw `.ics` files for class schedules.
- Many students hold part‑time jobs with weekly shift rosters.
- Manually reconciling the two sources leads to missed overlaps, late‑night lectures, or double‑booked shifts.
- The app parses the `.ics` feeds, normalises shift data, and flags any time‑block collisions before the semester begins.

---

## Features

### In‑Scope
- **Import** university `.ics` class schedule (full‑semester or per‑section).  
- **Import** recurring work‑shift rosters (weekly RRULEs) via CSV or manual entry.
- **Detect** overlapping time blocks (class ↔ class, class ↔ shift, shift ↔ shift).
- **Visualise** a week‑view calendar with colour‑coded blocks (class / shift / conflict).
- **Responsive** UI built with React, Tailwind CSS and Framer Motion animations.
- **REST API** (FastAPI) exposing CRUD for courses, sections, shifts and conflict checks.
- **Dockerised** development environment for easy local setup.

### Out of Scope (Explicitly Not Planned)
- Multi‑user / team sharing functionality.
- Automatic schedule optimisation (moving classes‑ or shift‑times).
- Mobile‑native app (the web UI is fully responsive).
- Integration with external calendar services (Google Calendar, Outlook) – import only.
- Real‑time collaborative editing.

---

## Architecture

```
+-------------------+        +----------------------+        +-------------------+
|  Front‑end (Next) | <----> |  FastAPI (Python)   | <----> |  PostgreSQL DB    |
|  React + TSX      |        |  CRUD + Service      |        |  Persist models   |
+-------------------+        +----------------------+        +-------------------+
        |                               |
        |   (Optional)  Docker Compose |
        +-------------------------------+
```

- **Front‑end**: Next.js (React) – renders the **CalendarWeekView** component and a SaaS‑style landing page (**LandingHero**).
- **Back‑end**: FastAPI – provides clean REST endpoints for `Course`, `Section`, `Shift`, and `TimeBlock` entities. Conflict detection is encapsulated in a pure‑Python service module.
- **Database**: PostgreSQL – stores normalized relational data (courses, sections, shifts, time blocks).
- **Containerisation**: `docker-compose.yml` orchestrates the API, DB, and (optionally) a dev‑only hot‑reload Next.js server.

---

## Tech Stack + Why

| Layer          | Technology                | Reasoning |
|----------------|---------------------------|-----------|
| UI / Front‑end | **Next.js (React)**       | Server‑side rendering for SEO, easy routing, and TypeScript support. |
| Styling        | **Tailwind CSS**          | Utility‑first, rapid design iteration, small bundle size. |
| Animations     | **Framer Motion**         | Declarative, performant motion APIs for subtle UI polish. |
| API            | **FastAPI**               | Modern async framework, automatic OpenAPI docs, great for Python‑centric logic. |
| ORM / DB       | **SQLAlchemy 2.0** + **Alembic** | Explicit model definitions, migration tooling, type‑safe queries. |
| Database       | **PostgreSQL**            | Proven relational store, rich date‑time support, easy local Docker image. |
| Containerisation| **Docker / docker‑compose**| Guarantees reproducible dev environment across OSes. |
| Testing        | **Pytest** + **Jest**    | Unit‑testable Python service (conflict algorithm) and React component tests. |

---

## Setup Instructions

```bash
# 1️⃣ Clone the repo
git clone https://github.com/your‑username/syncshift.git && cd syncshift

# 2️⃣ Copy env template & edit as needed
cp .env.example .env
# (set DATABASE_URL, SECRET_KEY, etc.)

# 3️⃣ Build & start containers (API + DB + optional Next dev server)
docker compose up --build

# 4️⃣ Apply database migrations
docker compose exec api alembic upgrade head

# 5️⃣ Front‑end (in another terminal) – optional if you prefer hot‑reload dev server
cd frontend
npm install
npm run dev   # http://localhost:3000
```

**Running Tests**
```bash
# API tests
docker compose exec api pytest

# Front‑end tests
cd frontend && npm test
```

---

## Algorithm Explanation (Brief)

*The conflict‑detection service works as a pure‑function that receives a list of `TimeBlock` objects (day, start, end, type). It:
1. Normalises all times to UTC or the user‑selected timezone.
2. Groups blocks by day of the week.
3. For each day, sorts the blocks by start time and performs a linear sweep, checking whether the start of the current block is < the end of the previous block.
4. Flags any overlapping pair as a **conflict** and returns a list of conflicted block IDs.
*
> **Note** – The implementation lives in `conflict_service.py`; you can replace it with a more sophisticated interval‑tree approach later without touching the API.

---

## Future Work

- **Multi‑user support** (OAuth login, per‑user schedules).
- **Export** calendars back to `.ics` or directly to Google Calendar.
- **Advanced conflict resolution** (suggest alternative sections / shift swaps).
- **Machine‑learning‑based time‑block clustering** for recommending optimal work‑hour windows.
- **Accessibility improvements** (WCAG colour contrast, keyboard navigation).
- **Performance optimisation** – migrate conflict detection to a compiled Rust library via PyO3 for very large timetables.

---

*Feel free to replace the placeholder sections (Problem, Scope) with your own narrative. Happy coding!*
