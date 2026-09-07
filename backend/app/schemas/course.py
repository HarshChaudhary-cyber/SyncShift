from typing import Optional
from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    code: str = Field(..., example="CS101", max_length=32)
    name: str = Field(..., example="Introduction to Computer Science", max_length=255)
    color: str = Field(default="#2563eb", example="#2563eb", max_length=32)


class CourseUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=32)
    name: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, max_length=32)


class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    color: str

    class Config:
        from_attributes = True
