# Travel & Transition-Aware Scheduling Intelligence

SyncShift recognizes a fundamental reality of university student and shift worker lives: **"No temporal overlap" does not necessarily mean "feasible".**

If a student finishes a class at 16:00 on Campus A and starts a shift at 16:10 at a coffee shop 20 minutes away across town, traditional calendar engines report zero conflicts. In practice, the student is guaranteed to be late, stressed, or forced to leave class early. SyncShift's Travel / Transition-Aware Intelligence closes this critical gap.

---

## 1. Core Architectural Principle

SyncShift distinguishes between two fundamentally different types of schedule issues:

| Attribute | Hard Overlap Conflict | Travel / Transition Warning |
| :--- | :--- | :--- |
| **Semantics** | Temporal collision ($A.start < B.end \land B.start < A.end$) | Insufficient transit/prep buffer between consecutive events |
| **Severity** | `severity: "hard"` | `severity: "warning"` |
| **Conflict Type** | `"class_shift"` or `"overlap"` | `"transition"` |
| **Impact on Optimizer**| Invalidates slot in hard mode; disqualifies shift | Applies a scoring penalty (or disqualifies if strict mode) |
| **Impact on Health** | Severe penalty (-15 per conflict) | Mild penalty (-4 per warning) with transit coaching tips |
| **User Notice** | Red badge, blocking alerts | Amber warning badge (`⚠ Short transition`) |

---

## 2. Configuration & Location Model

### User Configuration
Transition buffers are user-configurable in **Settings → Preferences**:
- **Field**: `minimum_transition_minutes` (persisted on `User` model, default: `15`).
- **Allowed presets**: `0`, `10`, `15`, `30`, `45`, `60` minutes.
- SyncShift avoids invasive GPS tracking or battery-draining continuous location monitoring. Instead, it leverages event location tags and configurable buffers.

### Location Pair Semantics
When evaluating two consecutive events $A$ and $B$ (where $A$ ends before $B$ starts on the same calendar day):
1. **Missing or Blank Locations**:
   - If either event has no location specified, the default buffer is evaluated to ensure general schedule breathing room.
2. **Same Location ($Loc_A == Loc_B$, case-insensitive)**:
   - Example: Class in *Lecture Hall 101* followed by Class in *Lecture Hall 204* or *Campus A*.
   - Zero transition penalty is applied (`required_buffer = 0`). Consecutive events in the same location are considered seamless.
3. **Distinct Locations ($Loc_A \ne Loc_B$)**:
   - Example: *Campus North* to *Café Central*.
   - Required buffer = `user.minimum_transition_minutes`.
   - If `available_minutes < required_buffer`, a transition conflict is raised.

---

## 3. Conflict Detection Algorithm

In `backend/app/store.py`, `detect_conflicts_and_totals()` executes the transition check after direct temporal overlaps:

```python
# Chronological traversal per day
for i in range(len(day_events) - 1):
    ev1 = day_events[i]
    ev2 = day_events[i + 1]
    
    # Check if ev1 ends before ev2 starts
    if ev1["end_dt"] <= ev2["start_dt"]:
        gap_minutes = (ev2["start_dt"] - ev1["end_dt"]).total_seconds() / 60.0
        loc1 = (ev1.get("location") or "").strip()
        loc2 = (ev2.get("location") or "").strip()
        
        # If locations are identical and non-empty, no buffer required
        if loc1 and loc2 and loc1.lower() == loc2.lower():
            continue
            
        if gap_minutes < min_transition_minutes:
            conflicts.append(ConflictItem(
                id=f"transition_{ev1['id']}_{ev2['id']}",
                title=f"Short transition between '{ev1['title']}' and '{ev2['title']}'",
                description=f"Only {int(gap_minutes)}m available between locations ('{loc1}' and '{loc2}'), but {min_transition_minutes}m preferred.",
                severity="warning",
                conflict_type="transition",
                available_transition_minutes=int(gap_minutes),
                required_transition_minutes=min_transition_minutes,
                location_a=loc1,
                location_b=loc2,
                day=day_events[0]["start_dt"].strftime("%Y-%m-%d"),
                block_a_id=ev1["id"],
                block_b_id=ev2["id"]
            ))
```

---

## 4. Integration Across SyncShift Engines

### Schedule Optimizer (`backend/app/services/optimizer.py`)
- When scoring candidate work shifts against fixed course timetables:
  - Candidates with tight transitions ($< \text{min\_transition}$) incur a dynamic score penalty proportional to the shortage:
    $$\text{penalty} = \frac{\text{required} - \text{available}}{\text{required}} \times 25$$
  - Shifts with spacious, relaxed transition windows ($> 45\text{m}$) receive bonus points.
  - Candidates that cause hard class overlaps remain disqualified.

### Study Planner (`backend/app/services/planner.py`)
- Study sessions require cognitive preparation and setup.
- The planner's `find_free_gaps` routine factors `user.minimum_transition_minutes` into gap detection, preventing recommendations that start immediately after an exhausting 3-hour lab or shift across town.

### Schedule Health (`backend/app/services/schedule_health.py`)
- Transition warnings reduce health score by 4 points (compared to 15 for hard overlaps).
- The advice engine flags tight transitions:
  > *"You have 2 tight travel transitions between different locations. Consider extending your buffer in Settings to avoid rushing."*

### Dashboard & Calendar UI
- Dashboard highlights tight transitions in the day overview without cluttering the screen.
- Calendar blocks display amber transition badges when an adjacent event requires travel buffer attention.
