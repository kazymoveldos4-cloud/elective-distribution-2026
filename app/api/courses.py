from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.database import get_session
from app.models import Application, Course, Enrollment
from app.schemas import CourseCreate, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Курсы"])


@router.get("", response_model=list[Course])
def list_courses(
    search: Optional[str] = None,
    min_capacity: Optional[int] = None,
    max_capacity: Optional[int] = None,
    session: Session = Depends(get_session),
):
    query = select(Course)
    if search:
        query = query.where(col(Course.title).ilike(f"%{search}%"))
    if min_capacity is not None:
        query = query.where(Course.capacity >= min_capacity)
    if max_capacity is not None:
        query = query.where(Course.capacity <= max_capacity)
    return session.exec(query).all()


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


@router.patch("/{course_id}", response_model=Course)
def update_course(
    course_id: int,
    data: CourseUpdate,
    session: Session = Depends(get_session),
):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")
    update_data = data.model_dump(exclude_unset=True)
    course.sqlmodel_update(update_data)
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(course_id: int, session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")
    has_applications = session.exec(
        select(Application).where(Application.course_id == course_id)
    ).first()
    has_enrollments = session.exec(
        select(Enrollment).where(Enrollment.course_id == course_id)
    ).first()
    if has_applications or has_enrollments:
        raise HTTPException(
            status_code=409,
            detail="Невозможно удалить курс: существуют связанные заявки или зачисления",
        )
    session.delete(course)
    session.commit()
    return {"message": "Курс успешно удален"}
