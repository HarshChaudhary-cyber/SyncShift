from pydantic import BaseModel
from app.schemas.block import BlockOut
from app.schemas.conflict import ConflictItem, WeeklyTotals


class WeekViewData(BaseModel):
    blocks: list[BlockOut]
    conflicts: list[ConflictItem]
    totals: WeeklyTotals
