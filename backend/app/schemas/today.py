from typing import List
from pydantic import BaseModel
from app.schemas.block import BlockOut
from app.schemas.conflict import ConflictItem


class TodayViewData(BaseModel):
    date: str
    day_of_week: int
    blocks: List[BlockOut]
    conflicts: List[ConflictItem]
    shift_hours: float
    expected_earnings: float
    class_hours: float
