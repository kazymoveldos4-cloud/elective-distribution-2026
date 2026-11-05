from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    group_name: str = Field(min_length=1, max_length=20)
    rating: float = Field(ge=0, le=100)


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    teacher: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0, le=500)


class ApplicationCreate(BaseModel):
    student_id: int
    course_id: int
    priority: int = Field(ge=1, le=3)
