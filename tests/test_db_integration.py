import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models import Application, Course, Student


@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Тестовая база данных SQLite in-memory с принудительно включенной
    проверкой внешних ключей (FOREIGN KEY).
    
    Обоснование:
    По умолчанию SQLite для сохранения обратной совместимости отключает
    проверку ограничений FOREIGN KEY. Чтобы протестировать каскадные правила
    и целостность связей, мы регистрируем обработчик события 'connect'
    и выполняем 'PRAGMA foreign_keys=ON;'.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


def test_crud_course_and_student(db_session: Session):
    """Проверка базовых операций добавления, чтения, изменения и удаления."""
    # 1. Создание (Create)
    course = Course(title="Архитектура ИС", teacher="Смирнов А.А.", capacity=30)
    student = Student(full_name="Ковалев Артем", group_name="ИС-24", rating=88.5)
    db_session.add(course)
    db_session.add(student)
    db_session.commit()
    db_session.refresh(course)
    db_session.refresh(student)

    assert course.id is not None
    assert student.id is not None

    # 2. Чтение (Read)
    loaded_course = db_session.get(Course, course.id)
    assert loaded_course is not None
    assert loaded_course.title == "Архитектура ИС"

    loaded_students = db_session.exec(select(Student).where(Student.group_name == "ИС-24")).all()
    assert len(loaded_students) == 1
    assert loaded_students[0].full_name == "Ковалев Артем"

    # 3. Изменение (Update)
    loaded_course.capacity = 35
    loaded_course.title = "Архитектура корпоративных ИС"
    db_session.add(loaded_course)
    db_session.commit()
    db_session.refresh(loaded_course)
    assert loaded_course.capacity == 35
    assert loaded_course.title == "Архитектура корпоративных ИС"

    # 4. Удаление (Delete)
    db_session.delete(loaded_course)
    db_session.commit()
    assert db_session.get(Course, course.id) is None


def test_transaction_rollback_on_error(db_session: Session):
    """
    Проверка транзакционности: при сбое в середине последовательности операций
    выполняется rollback, и незафиксированные данные не сохраняются.
    """
    # Сохраняем стабильную запись
    course1 = Course(title="Базовый курс", teacher="Учитель 1", capacity=10)
    db_session.add(course1)
    db_session.commit()

    initial_count = len(db_session.exec(select(Course)).all())
    assert initial_count == 1

    try:
        # Начинаем операцию добавления двух курсов
        course2 = Course(title="Второй курс", teacher="Учитель 2", capacity=15)
        db_session.add(course2)
        db_session.flush()  # запись отправлена в транзакцию, но не commit'нута

        # Принудительно вызываем ошибку (дубликат ID через raw model или IntegrityError)
        invalid_course = Course(id=course1.id, title="Конфликтный курс", teacher="Учитель 3", capacity=20)
        db_session.add(invalid_course)
        db_session.commit()  # Должно упасть из-за конфликта PRIMARY KEY
        pytest.fail("Ожидалось исключение IntegrityError")
    except IntegrityError:
        db_session.rollback()

    # Проверяем, что course2 откатился и количество курсов осталось прежним
    final_courses = db_session.exec(select(Course)).all()
    assert len(final_courses) == initial_count
    assert final_courses[0].title == "Базовый курс"


def test_primary_key_constraint(db_session: Session):
    """Проверка ограничения PRIMARY KEY: нельзя вставить две записи с одинаковым PK."""
    s1 = Student(id=500, full_name="Студент 1", group_name="ГР-1", rating=75.0)
    db_session.add(s1)
    db_session.commit()

    # Попытка создать студента с тем же ID
    s2 = Student(id=500, full_name="Студент 2", group_name="ГР-2", rating=80.0)
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_not_null_constraint(db_session: Session):
    """Проверка ограничения NOT NULL на уровне схемы базы данных."""
    # title в модели Course объявлен как обязательный (not null)
    invalid_course = Course(title=None, teacher="Преподаватель", capacity=20)  # type: ignore
    db_session.add(invalid_course)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_constraint(db_session: Session):
    """
    Проверка ограничения FOREIGN KEY при включенной PRAGMA foreign_keys=ON.
    Попытка создать заявку на несуществующего студента должна вызывать IntegrityError.
    """
    course = Course(title="Безопасность сетей", teacher="Петров П.П.", capacity=10)
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    # Заявка с student_id=999999 (студент отсутствует в базе данных)
    orphan_application = Application(
        student_id=999999,
        course_id=course.id,
        priority=1,
    )
    db_session.add(orphan_application)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
