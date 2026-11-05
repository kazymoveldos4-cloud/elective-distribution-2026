from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Student
from app.schemas import StudentCreate, StudentUpdate

router = APIRouter(prefix="/students", tags=["Студенты"])


@router.get("", response_model=list[Student])
def list_students(session: Session = Depends(get_session)):
    return session.exec(select(Student)).all()


@router.get("/{student_id}", response_model=Student)
def get_student(student_id: int, session: Session = Depends(get_session)):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    return student


@router.post("", response_model=Student, status_code=201)
def create_student(data: StudentCreate, session: Session = Depends(get_session)):
    student = Student(**data.model_dump())
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.patch("/{student_id}", response_model=Student)
def update_student(
    student_id: int,
    data: StudentUpdate,
    session: Session = Depends(get_session),
):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    update_data = data.model_dump(exclude_unset=True)
    student.sqlmodel_update(update_data)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student
