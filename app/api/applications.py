from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Application, Course, Student
from app.schemas import ApplicationCreate

router = APIRouter(prefix="/applications", tags=["Заявки"])


@router.get("", response_model=list[Application])
def list_applications(
    status: Optional[str] = None,
    course_id: Optional[int] = None,
    student_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    query = select(Application)
    if status is not None:
        query = query.where(Application.status == status)
    if course_id is not None:
        query = query.where(Application.course_id == course_id)
    if student_id is not None:
        query = query.where(Application.student_id == student_id)
    query = query.order_by(Application.priority)
    return session.exec(query).all()


@router.get("/{application_id}", response_model=Application)
def get_application(application_id: int, session: Session = Depends(get_session)):
    application = session.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return application


@router.post("", response_model=Application, status_code=201)
def create_application(data: ApplicationCreate, session: Session = Depends(get_session)):
    if not session.get(Student, data.student_id):
        raise HTTPException(status_code=404, detail="Студент не найден")
    if not session.get(Course, data.course_id):
        raise HTTPException(status_code=404, detail="Курс не найден")
    duplicate = session.exec(
        select(Application).where(
            Application.student_id == data.student_id,
            Application.course_id == data.course_id,
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Заявка на этот курс уже подана")
    application = Application(**data.model_dump())
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(application_id: int, session: Session = Depends(get_session)):
    application = session.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    session.delete(application)
    session.commit()
    return {"message": "Заявка успешно удалена"}
