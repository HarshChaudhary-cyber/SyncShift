from datetime import date, time
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


class BlockBase(BaseModel):
    type: Literal["class", "shift", "study"]
    title: str = Field(..., max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    day_of_week: int = Field(..., ge=0, le=6, description="0 = Sunday, 1 = Monday ... 6 = Saturday")
    start_time: Union[time, str] = Field(..., description="Start time (HH:MM or HH:MM:SS)")
    end_time: Union[time, str] = Field(..., description="End time (HH:MM or HH:MM:SS)")
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    is_recurring: bool = True
    recurrence_interval: int = Field(default=1, ge=1, le=52, description="1 = weekly, 2 = biweekly (every 2 weeks)")
    specific_date: Optional[date] = None
    is_flexible: bool = False
    hourly_wage: Optional[float] = Field(None, ge=0.0)
    course_id: Optional[int] = None
    study_task_id: Optional[int] = None


class BlockCreate(BlockBase):
    @model_validator(mode="after")
    def validate_block_ranges(self) -> "BlockCreate":
        # 1. Effective date range validation
        if self.effective_from and self.effective_until:
            if self.effective_until < self.effective_from:
                raise ValueError("effective_until must be greater than or equal to effective_from")

        # 2. Time string to normalized format validation
        s_str = str(self.start_time)
        e_str = str(self.end_time)
        if s_str == e_str:
            raise ValueError("end_time cannot be identical to start_time")

        return self


class BlockUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[Union[time, str]] = None
    end_time: Optional[Union[time, str]] = None
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    is_recurring: Optional[bool] = None
    recurrence_interval: Optional[int] = Field(None, ge=1, le=52)
    specific_date: Optional[date] = None
    is_flexible: Optional[bool] = None
    hourly_wage: Optional[float] = Field(None, ge=0.0)
    course_id: Optional[int] = None
    # Recurrence edit scope: "this" (single occurrence), "future" (this and future), "all" (entire series)
    scope: Optional[Literal["this", "future", "all"]] = "all"
    occurrence_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_update_dates(self) -> "BlockUpdate":
        if self.effective_from and self.effective_until:
            if self.effective_until < self.effective_from:
                raise ValueError("effective_until must be greater than or equal to effective_from")
        return self


class BlockDeleteRequest(BaseModel):
    scope: Literal["this", "future", "all"] = "all"
    occurrence_date: Optional[date] = None


class BlockExceptionCreate(BaseModel):
    original_date: date
    override_date: Optional[date] = None
    start_time: Optional[Union[time, str]] = None
    end_time: Optional[Union[time, str]] = None
    title: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    is_cancelled: bool = False
    note: Optional[str] = Field(None, max_length=255)


class BlockDuplicate(BaseModel):
    days_offset: int = Field(default=0, description="Number of days to shift the duplicated block (e.g. +1, +2)")


class BlockOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    type: str
    title: str
    location: Optional[str] = None
    day_of_week: int
    start_time: str
    end_time: str
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    is_recurring: bool = True
    recurrence_interval: int = 1
    specific_date: Optional[date] = None
    is_flexible: bool = False
    hourly_wage: Optional[float] = None
    course_id: Optional[int] = None
    study_task_id: Optional[int] = None
    color: Optional[str] = None
    deleted: Optional[bool] = False

    # Single-occurrence fields (when returned in week or today occurrences)
    occurrence_date: Optional[date] = None
    is_exception: bool = False
    original_date: Optional[date] = None
    override_id: Optional[int] = None

    class Config:
        from_attributes = True


class ClearTimetableRequest(BaseModel):
    only_imported: bool = Field(default=False, description="If true, only delete imported timetable blocks")


class ClearTimetableResponseData(BaseModel):
    deleted_count: int = Field(..., description="Number of timetable blocks soft-deleted")
    remaining_count: int = Field(..., description="Number of active class blocks remaining")
    remaining_total_blocks: int = Field(..., description="Number of active blocks of all types remaining")
    preserved_shifts_count: int = Field(..., description="Number of active work shifts preserved")
    preserved_study_count: int = Field(..., description="Number of active study sessions preserved")
