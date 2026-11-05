from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Course
from app.schemas import CourseCreate

router = APIRouter(prefix="/courses", tags=["Курсы"])


@router.get("", response_model=list[Course])
def list_courses(session: Session = Depends(get_session)):
    return session.exec(select(Course)).all()


@router.get("/{course_id}", response_model=Course)
def get_course(course_id: int, session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")
    return course


@router.post("", response_model=Course, status_code=201)
def create_course(data: CourseCreate, session: Session = Depends(get_session)):
    course = Course(**data.model_dump())
    session.add(course)
    session.commit()
    session.refresh(course)
    return course
