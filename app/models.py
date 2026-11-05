from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(index=True)
    group_name: str
    rating: float = Field(index=True)

    applications: List["Application"] = Relationship(back_populates="student")
    enrollments: List["Enrollment"] = Relationship(back_populates="student")


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    teacher: str
    capacity: int

    applications: List["Application"] = Relationship(back_populates="course")
    enrollments: List["Enrollment"] = Relationship(back_populates="course")


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    course_id: int = Field(foreign_key="course.id")
    priority: int
    status: str = Field(default="new")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    student: Optional[Student] = Relationship(back_populates="applications")
    course: Optional[Course] = Relationship(back_populates="applications")


class Enrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    course_id: int = Field(foreign_key="course.id")

    student: Optional[Student] = Relationship(back_populates="enrollments")
    course: Optional[Course] = Relationship(back_populates="enrollments")
