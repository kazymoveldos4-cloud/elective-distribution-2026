from typing import Optional

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    group_name: str = Field(min_length=1, max_length=20)
    rating: float = Field(ge=0, le=100)


class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    group_name: Optional[str] = Field(default=None, min_length=1, max_length=20)
    rating: Optional[float] = Field(default=None, ge=0, le=100)


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    teacher: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0, le=500)


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    teacher: Optional[str] = Field(default=None, min_length=1, max_length=100)
    capacity: Optional[int] = Field(default=None, gt=0, le=500)


class ApplicationCreate(BaseModel):
    student_id: int
    course_id: int
    priority: int = Field(ge=1, le=3)
