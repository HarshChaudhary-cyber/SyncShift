from datetime import date
from typing import Optional
from pydantic import BaseModel
from app.schemas.block import BlockOut
from app.schemas.conflict import ConflictItem, WeeklyTotals


class WeekViewData(BaseModel):
    week_start: Optional[date] = None
    blocks: list[BlockOut]
    conflicts: list[ConflictItem]
    totals: WeeklyTotals
