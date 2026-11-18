# Отчёт об исправленных ошибках (Bugs Fixed)

В ходе расширенного интеграционного и параметризованного тестирования бэкенда были обнаружены и устранены две реальные ошибки в валидации и бизнес-логике приложения.

---

## Ошибка 1: Пропуск валидации строк, состоящих исключительно из пробелов

- **Затронутые файлы:** `app/schemas.py`
- **Обнаружено тестом:** `tests/test_api_parameterized.py::test_course_title_boundaries[   -422]`
- **Категория:** Ошибка валидации пользовательского ввода / целостность данных.

### Что было:
В схемах `CourseCreate`, `CourseUpdate`, `StudentCreate`, `StudentUpdate` строковые поля (`title`, `teacher`, `full_name`, `group_name`) валидировались исключительно с помощью `Field(min_length=1)`. 
Строка, состоящая только из пробелов (например, `"   "`), имеет длину 3 символа и формально удовлетворяла условию `min_length=1`. В результате клиент мог успешно создать курс или студента с невидимым именем (HTTP 201), что засоряло базу данных и приводило к сбоям при поиске и отображении в Streamlit.

### Что стало:
В схемы Pydantic были добавлены валидаторы `@field_validator`:
```python
@field_validator("title", "teacher")
@classmethod
def validate_not_whitespace(cls, v: str) -> str:
    if not v.strip():
        raise ValueError("Поле не может состоять только из пробелов")
    return v.strip()
```
Теперь строки очищаются от краевых пробелов, а строки, состоящие исключительно из пробелов, отклоняются на этапе валидации со статусом **HTTP 422 Unprocessable Entity**.

---

## Ошибка 2: Отсутствие проверки уникальности приоритетов заявок студента

- **Затронутые файлы:** `app/api/applications.py`
- **Обнаружено тестом:** `tests/test_api_parameterized.py::test_conflict_duplicate_priority_for_same_student`
- **Категория:** Логическая ошибка бизнес-правил предметной области.

### Что было:
В эндпоинте `POST /applications` существовала только проверка на повторную подачу заявки на один и тот же курс:
```python
duplicate_course = session.exec(
    select(Application).where(
        Application.student_id == data.student_id,
        Application.course_id == data.course_id,
    )
).first()
if duplicate_course:
    raise HTTPException(status_code=409, detail="Заявка на этот курс уже подана")
```
При этом проверка уникальности приоритета (`priority`) отсутствовала. Студент мог подать две или три заявки на разные курсы с одним и тем же приоритетом (например, две заявки с `priority: 1`). Это делало алгоритм распределения замдекана недетерминированным, нарушая регламент ранжирования дисциплин по выбору (1 — наивысший, 2 — альтернативный, 3 — резервный).

### Что стало:
В эндпоинт `create_application` добавлена проверка наличия у студента ранее поданной заявки с тем же приоритетом:
```python
duplicate_priority = session.exec(
    select(Application).where(
        Application.student_id == data.student_id,
        Application.priority == data.priority,
    )
).first()
if duplicate_priority:
    raise HTTPException(
        status_code=409,
        detail=f"Заявка с приоритетом {data.priority} уже существует для данного студента",
    )
```
Теперь при попытке дублировать приоритет API возвращает **HTTP 409 Conflict** с понятным описанием причины конфликта.
