from datetime import date
from typing import Optional
from app.schemas.block import BlockOut
from app.schemas.conflict import ConflictItem, WeeklyTotals

# In-memory shared persistence store for SyncShift development
INITIAL_BLOCKS = [
    {
        "id": 1,
        "type": "class",
        "title": "CS 210: Data Structures",
        "location": "Room 302, Prof. Sharma",
        "day_of_week": 1,  # Monday
        "start_time": "09:00:00",
        "end_time": "10:30:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": False,
        "hourly_wage": None,
        "course_id": 1,
        "deleted": False,
    },
    {
        "id": 2,
        "type": "shift",
        "title": "Campus Library Desk",
        "location": "Shift Supervisor: Sarah",
        "day_of_week": 1,  # Monday
        "start_time": "10:00:00",
        "end_time": "14:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": True,
        "hourly_wage": 17.50,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 3,
        "type": "shift",
        "title": "Dining Hall Cashier",
        "location": "Main Cafeteria",
        "day_of_week": 3,  # Wednesday
        "start_time": "16:00:00",
        "end_time": "20:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": True,
        "hourly_wage": 16.00,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 4,
        "type": "class",
        "title": "CS 210: Data Structures",
        "location": "Room 302",
        "day_of_week": 2,  # Tuesday
        "start_time": "09:30:00",
        "end_time": "11:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": False,
        "hourly_wage": None,
        "course_id": 1,
        "deleted": False,
    },
    {
        "id": 5,
        "type": "shift",
        "title": "IT Helpdesk Shift",
        "location": "Student Services Bldg",
        "day_of_week": 2,  # Tuesday
        "start_time": "13:00:00",
        "end_time": "17:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": True,
        "hourly_wage": 18.50,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 6,
        "type": "class",
        "title": "PHYS 150 Lab",
        "location": "Lab B, TA: Chen",
        "day_of_week": 3,  # Wednesday
        "start_time": "14:00:00",
        "end_time": "17:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": False,
        "hourly_wage": None,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 7,
        "type": "shift",
        "title": "Dining Hall Cashier",
        "location": "Main Cafeteria",
        "day_of_week": 3,  # Wednesday
        "start_time": "16:00:00",
        "end_time": "20:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": True,
        "hourly_wage": 16.00,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 9,
        "type": "class",
        "title": "MATH 220: Linear Algebra",
        "location": "Hall C, Prof. Williams",
        "day_of_week": 4,  # Thursday
        "start_time": "11:00:00",
        "end_time": "12:30:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": False,
        "hourly_wage": None,
        "course_id": 2,
        "deleted": False,
    },
    {
        "id": 10,
        "type": "shift",
        "title": "Library Circulation Desk",
        "location": "2nd Floor",
        "day_of_week": 4,  # Thursday
        "start_time": "14:00:00",
        "end_time": "18:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": True,
        "hourly_wage": 17.50,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 11,
        "type": "class",
        "title": "ENG 201: Technical Writing",
        "location": "Room 105",
        "day_of_week": 5,  # Friday
        "start_time": "10:00:00",
        "end_time": "11:30:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": False,
        "hourly_wage": None,
        "course_id": None,
        "deleted": False,
    },
    {
        "id": 12,
        "type": "shift",
        "title": "Campus Security Night Shift",
        "location": "Main Gate · Overnight",
        "day_of_week": 0,  # Sunday
        "start_time": "22:00:00",
        "end_time": "02:00:00",
        "effective_from": "2026-09-01",
        "effective_until": None,
        "is_flexible": True,
        "hourly_wage": 20.00,
        "course_id": None,
        "deleted": False,
    },
]

# Shared list that persists in memory across requests
BLOCKS_DB = [{**b, "user_id": b.get("user_id", 1)} for b in INITIAL_BLOCKS]


def time_to_minutes(t_str: str) -> int:
    parts = t_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(m: int) -> str:
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"


def get_all_blocks(user_id: Optional[int] = None, include_deleted: bool = False) -> list[BlockOut]:
    result = []
    for b in BLOCKS_DB:
        if not include_deleted and b.get("deleted", False):
            continue
        if user_id is not None and b.get("user_id", 1) != user_id:
            continue
        eff_from = b.get("effective_from")
        if isinstance(eff_from, str):
            eff_from = date.fromisoformat(eff_from)
        eff_until = b.get("effective_until")
        if isinstance(eff_until, str):
            eff_until = date.fromisoformat(eff_until)

        result.append(
            BlockOut(
                id=b["id"],
                user_id=b.get("user_id", 1),
                type=b["type"],
                title=b["title"],
                location=b.get("location"),
                day_of_week=b["day_of_week"],
                start_time=b["start_time"],
                end_time=b["end_time"],
                effective_from=eff_from or date(2026, 9, 1),
                effective_until=eff_until,
                is_flexible=b.get("is_flexible", False),
                hourly_wage=b.get("hourly_wage"),
                course_id=b.get("course_id"),
                deleted=b.get("deleted", False),
            )
        )
    return result


def get_block_by_id(block_id: int, user_id: Optional[int] = None) -> Optional[dict]:
    for b in BLOCKS_DB:
        if b["id"] == block_id:
            if user_id is not None and b.get("user_id", 1) != user_id:
                return None
            return b
    return None


def update_block_in_store(block_id: int, updates: dict, user_id: Optional[int] = None) -> Optional[BlockOut]:
    for b in BLOCKS_DB:
        if b["id"] == block_id:
            if user_id is not None and b.get("user_id", 1) != user_id:
                return None
            for k, v in updates.items():
                if v is not None and k != "user_id":
                    if k in ("start_time", "end_time") and not str(v).endswith(":00") and len(str(v)) == 5:
                        b[k] = f"{v}:00"
                    else:
                        b[k] = v
            # Return updated BlockOut
            all_b = get_all_blocks(user_id=user_id, include_deleted=True)
            for item in all_b:
                if item.id == block_id:
                    return item
    return None


def add_block_to_store(data: dict, user_id: int = 1) -> BlockOut:
    new_id = max([b["id"] for b in BLOCKS_DB], default=0) + 1
    data["id"] = new_id
    data["user_id"] = user_id
    if "deleted" not in data:
        data["deleted"] = False
    BLOCKS_DB.append(data)
    all_b = get_all_blocks(user_id=user_id, include_deleted=True)
    return [b for b in all_b if b.id == new_id][0]


def delete_block_from_store(block_id: int, user_id: Optional[int] = None) -> bool:
    for b in BLOCKS_DB:
        if b["id"] == block_id:
            if user_id is not None and b.get("user_id", 1) != user_id:
                return False
            b["deleted"] = True
            return True
    return False


def detect_conflicts_and_totals(
    user_id: Optional[int] = None,
    weekly_hour_limit: float = 20.0,
) -> tuple[list[ConflictItem], WeeklyTotals]:
    active_blocks = [
        b for b in BLOCKS_DB
        if not b.get("deleted", False) and (user_id is None or b.get("user_id", 1) == user_id)
    ]
    conflicts: list[ConflictItem] = []
    conflict_id = 9000

    # Pairwise comparison
    for i in range(len(active_blocks)):
        for j in range(i + 1, len(active_blocks)):
            b1 = active_blocks[i]
            b2 = active_blocks[j]

            # Only blocks on the same day can conflict
            if b1["day_of_week"] != b2["day_of_week"]:
                continue

            s1 = time_to_minutes(b1["start_time"])
            e1 = time_to_minutes(b1["end_time"])
            s2 = time_to_minutes(b2["start_time"])
            e2 = time_to_minutes(b2["end_time"])

            # Overlap test: s1 < e2 and s2 < e1
            if s1 < e2 and s2 < e1:
                conflict_id += 1
                overlap_start_min = max(s1, s2)
                overlap_end_min = min(e1, e2)
                overlap_minutes = overlap_end_min - overlap_start_min
                severity = "hard" if b1["type"] == "class" or b2["type"] == "class" else "warning"

                conflicts.append(
                    ConflictItem(
                        id=conflict_id,
                        block_a_id=b1["id"],
                        block_b_id=b2["id"],
                        overlap_minutes=overlap_minutes,
                        severity=severity,
                        overlap_start=minutes_to_time(overlap_start_min),
                        overlap_end=minutes_to_time(overlap_end_min),
                        day_of_week=b1["day_of_week"],
                        description=f"{b1['title']} overlaps with {b2['title']}",
                    )
                )

    # Calculate weekly totals
    shift_hours = 0.0
    class_hours = 0.0
    expected_earnings = 0.0

    for b in active_blocks:
        s = time_to_minutes(b["start_time"])
        e = time_to_minutes(b["end_time"])
        hours = max(0, e - s) / 60.0
        if b["type"] == "shift":
            shift_hours += hours
            wage = b.get("hourly_wage") or 0.0
            expected_earnings += hours * wage
        elif b["type"] == "class":
            class_hours += hours

    totals = WeeklyTotals(
        shift_hours=round(shift_hours, 1),
        class_hours=round(class_hours, 1),
        expected_earnings=round(expected_earnings, 2),
        over_limit=shift_hours > weekly_hour_limit,
    )

    return conflicts, totals

