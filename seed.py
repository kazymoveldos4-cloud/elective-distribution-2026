from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import Application, Course, Enrollment, Student


def seed():
    init_db()
    with Session(engine) as session:
        if session.exec(select(Student)).first():
            print("База уже заполнена, пропускаю.")
            return

        students = [
            Student(full_name="Аскаров Нурлан", group_name="ИС-21", rating=95.5),
            Student(full_name="Бекова Айгерим", group_name="ИС-21", rating=91.0),
            Student(full_name="Сериков Данияр", group_name="ИС-22", rating=87.3),
            Student(full_name="Омарова Динара", group_name="ИС-22", rating=82.7),
            Student(full_name="Жумабаев Ерлан", group_name="ИС-23", rating=76.4),
            Student(full_name="Ким Анастасия", group_name="ИС-23", rating=70.1),
        ]
        courses = [
            Course(title="Machine Learning", teacher="Ахметов А.К.", capacity=2),
            Course(title="Веб-дизайн", teacher="Иванова Е.П.", capacity=3),
            Course(title="Основы кибербезопасности", teacher="Касымов Т.Р.", capacity=2),
        ]
        session.add_all(students + courses)
        session.commit()
        for obj in students + courses:
            session.refresh(obj)

        applications = []
        for i, s in enumerate(students):
            applications.append(Application(student_id=s.id, course_id=courses[0].id, priority=1))
            applications.append(Application(student_id=s.id, course_id=courses[1 + i % 2].id, priority=2))
        session.add_all(applications)
        session.commit()

        print(
            f"Готово: студентов {len(students)}, курсов {len(courses)}, "
            f"заявок {len(applications)}, зачислений 0"
        )


if __name__ == "__main__":
    seed()
