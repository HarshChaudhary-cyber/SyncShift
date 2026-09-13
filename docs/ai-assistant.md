# SyncShift Assistant: Natural-Language Scheduling Intelligence

SyncShift Assistant brings conversational, natural-language scheduling intelligence to university students and shift workers. Designed with strict security and reliability principles, the assistant interprets user intent, coordinates with deterministic scheduling and optimization algorithms, and safeguards user schedules through action previews and multi-stage revalidation.

---

## 1. Architectural Philosophy: AI as Interpreter, Not Source of Truth

Traditional LLM integrations often suffer from hallucinations, arbitrary data mutations, or unconstrained database access. In SyncShift, we adhere strictly to the following principle:

```
                  USER PROMPT
                       │
                       ▼
          AI INTERPRETS INTENT & PARAMS
                       │
                       ▼
         PYDANTIC STRUCTURED VALIDATION
                       │
                       ▼
         DETERMINISTIC BUSINESS LOGIC
   (Conflict Engine / Optimizer / Planner)
                       │
                       ▼
               ACTION PREVIEW CARD
         (Checks: Overlaps, Limits, Travel)
                       │
                       ▼
           USER CONFIRMS IN FRONTEND
                       │
                       ▼
        BACKEND RE-VALIDATES CONSTRAINTS
                       │
                       ▼
          POSTGRESQL / DATABASE COMMIT
                       │
                       ▼
             STRUCTURED AUDIT LOG
```

### Core Invariants
1. **AI Never Directly Writes to the Database**: The LLM has zero direct SQL or ORM access. It produces structured intents which are processed by FastAPI services.
2. **Deterministic Source of Truth**: Availability calculations, work hours, conflict overlaps, and travel buffers are computed exclusively by Python business logic.
3. **No Phantom Changes**: Any modifying action (`MOVE_EVENT`, `RESCHEDULE_EVENT`) requires explicit user confirmation via an Action Preview card with full visual safety checks.
4. **Backend Revalidation**: Even after the user clicks "Confirm", the backend re-runs the entire conflict and constraint engine before executing the database mutation, preventing race conditions or stale assumptions.

---

## 2. Intent Extraction & Structured Schemas

Incoming chat messages to `POST /api/v1/assistant/chat` pass through an intent classification and parameter extraction pipeline.

### Supported Intents
- `GET_TODAY_SCHEDULE`: Queries events for the current date in the user's IANA timezone.
- `GET_WEEK_SCHEDULE`: Retrieves weekly blocks and totals.
- `GET_NEXT_EVENT`: Identifies the immediate upcoming class, shift, or study session.
- `GET_CONFLICTS`: Queries active hard overlaps and travel/transition warnings.
- `GET_WORK_HOURS`: Reports scheduled vs. configured weekly work hour limits.
- `GET_EARNINGS`: Calculates estimated earnings based on shift hourly rates.
- `FIND_AVAILABLE_TIME`: Identifies conflict-free blocks of requested duration.
- `FIND_WORK_SCHEDULE`: Solves feasible shift placements using the deterministic optimizer.
- `PLAN_STUDY`: Generates study session recommendations via the Study Planner service.
- `CHECK_SCHEDULE_HEALTH`: Summarizes schedule health score and flags bottlenecks.
- `MOVE_EVENT`: Previews moving a specific shift or study event to a new time.
- `RESCHEDULE_EVENT`: Proposes alternative conflict-free slots for a conflicted event.
- `UNKNOWN`: Fallback when intent cannot be safely classified.

### Pydantic Validation Schema
```python
class AssistantIntent(str, Enum):
    GET_TODAY_SCHEDULE = "GET_TODAY_SCHEDULE"
    GET_WEEK_SCHEDULE = "GET_WEEK_SCHEDULE"
    GET_NEXT_EVENT = "GET_NEXT_EVENT"
    GET_CONFLICTS = "GET_CONFLICTS"
    GET_WORK_HOURS = "GET_WORK_HOURS"
    GET_EARNINGS = "GET_EARNINGS"
    FIND_AVAILABLE_TIME = "FIND_AVAILABLE_TIME"
    FIND_WORK_SCHEDULE = "FIND_WORK_SCHEDULE"
    PLAN_STUDY = "PLAN_STUDY"
    CHECK_SCHEDULE_HEALTH = "CHECK_SCHEDULE_HEALTH"
    MOVE_EVENT = "MOVE_EVENT"
    RESCHEDULE_EVENT = "RESCHEDULE_EVENT"
    UNKNOWN = "UNKNOWN"

class IntentParameters(BaseModel):
    date: Optional[str] = None
    target_date: Optional[str] = None
    target_start_time: Optional[str] = None
    target_end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    target_hours: Optional[float] = None
    preferred_days: List[str] = []
    course_name: Optional[str] = None
    event_id: Optional[str] = None
    event_title: Optional[str] = None
```

Malformed, extra, or out-of-spec parameters are rejected at the schema level.

---

## 3. Disambiguation & Safe Read-Only Queries

### Ambiguity Handling
When a user requests an action without sufficient specificity (e.g., *"Move my shift"* when the user has multiple shifts):
- The assistant **does not guess**.
- It identifies candidate blocks from the database within the upcoming window.
- It returns structured choices (`choices: List[AmbiguousChoice]`) prompting the user:
  > *"I found 2 upcoming shifts. Which one would you like to move?"*
- The frontend renders interactive selection buttons so the user can disambiguate with a single click.

### Read Queries Powered by Ground Truth
When answering *"How many hours am I working?"* or *"What are my conflicts?"*:
- The assistant service queries `detect_conflicts_and_totals` from `backend/app/store.py`.
- Calculations strictly respect the user's configured weekly limit (e.g. 20h) and rate ($/hr).
- If the AI service is unreachable, a robust deterministic regex fallback resolves common scheduling queries without taking down the assistant or the app.

---

## 4. Action Preview & Confirmation Pipeline

For any destructive or mutating operation:

1. **Target Identification**: The shift or event is matched deterministically by `id` or title/date in the authenticated user's store.
2. **Constraint & Conflict Check**:
   - The proposed slot is checked for hard class overlaps.
   - Weekly work limits are checked against `weekly_work_hour_limit`.
   - Late-night thresholds are flagged (e.g., ending after 21:00).
   - Travel buffers are verified against adjacent events using the user's `minimum_transition_minutes`.
3. **Action Preview Construction**: An `ActionPreview` payload is returned:
   ```json
   {
     "action_type": "MOVE_EVENT",
     "block_id": "b-101",
     "title": "Café Roma",
     "original_start": "2026-09-18T14:00:00",
     "original_end": "2026-09-18T18:00:00",
     "target_start": "2026-09-18T16:00:00",
     "target_end": "2026-09-18T20:00:00",
     "checks": [
       {"passed": true, "label": "No class overlap"},
       {"passed": true, "label": "Work-hour limit respected (16/20h)"},
       {"passed": false, "label": "Ends later than usual (20:00)", "severity": "warning"}
     ]
   }
   ```
4. **User Confirmation**: The UI renders a dedicated Action Card with safety checklist badges, `[Cancel]`, and `[Confirm]`.
5. **Execution & Audit**:
   - The client calls `POST /api/v1/assistant/confirm`.
   - The backend runs `detect_conflicts_and_totals` to ensure conditions haven't changed.
   - If clean, the block is updated via `update_block_in_store`.
   - An audit log entry (`AI_ACTION_CONFIRMED`) is written with structured metadata.
   - The frontend triggers `syncshift:schedule-updated` event to refresh calendar and analytics views in real time.

---

## 5. Security & Privacy Boundaries

### Minimal Context Window
The backend only provides the LLM with the minimum necessary context for the current request:
- Current date and day in user's timezone.
- Today's and week's block summaries (titles, times, locations).
- Active conflict summaries and weekly totals.
- **NEVER SENT TO AI**:
  - Passwords or password hashes.
  - JWTs, access tokens, or refresh tokens.
  - User database IDs or foreign keys.
  - Other users' schedules or shared configurations.
  - Raw filesystem paths or environmental secrets.

### Prompt Injection Defense
- System prompts are enclosed within strict boundary instructions enforcing structured JSON output.
- All user input is treated as untrusted text.
- Any attempt to instruct the model to *"Ignore previous instructions"*, *"Expose system prompt"*, or *"Show other users' schedules"* is intercepted and cleanly rejected.
- Even if an LLM was jailbroken, **it has no API to query another user's schedule** because the backend context builder scopes queries strictly to `current_user.user_id` from the verified JWT.
