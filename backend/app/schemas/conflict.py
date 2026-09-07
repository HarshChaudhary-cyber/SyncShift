from pydantic import BaseModel, Field


class ConflictItem(BaseModel):
    id: int
    block_a_id: int
    block_b_id: int
    overlap_minutes: int
    severity: str = Field(..., description="'hard' or 'warning'")
    overlap_start: str
    overlap_end: str


class WeeklyTotals(BaseModel):
    shift_hours: float
    class_hours: float
    expected_earnings: float
    over_limit: bool


class ConflictsResponseData(BaseModel):
    conflicts: list[ConflictItem]
    weekly_totals: WeeklyTotals
