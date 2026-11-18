import pytest
from fastapi.testclient import TestClient


# ============================================================================
# 1. Параметризованные тесты на граничные значения capacity
# ============================================================================
@pytest.mark.parametrize(
    "capacity,expected_status",
    [
        (0, 422),          # 0 недопустим (gt=0)
        (-1, 422),         # Отрицательное число недопустимо
        (1, 201),          # Минимально допустимая вместимость
        (500, 201),        # Максимально допустимая вместимость (le=500)
        (501, 422),        # Превышение верхнего порога
        (1000000, 422),    # Заведомо огромное значение
        ("abc", 422),      # Неверный тип данных (строка вместо int)
        (None, 422),       # None вместо int
    ],
)
def test_course_capacity_boundaries(client: TestClient, capacity, expected_status):
    payload = {
        "title": "Тестовый курс",
        "teacher": "Преподаватель",
        "capacity": capacity,
    }
    response = client.post("/courses", json=payload)
    assert response.status_code == expected_status


# ============================================================================
# 2. Параметризованные тесты на граничные значения title
# ============================================================================
@pytest.mark.parametrize(
    "title,expected_status",
    [
        ("", 422),           # Пустая строка недопустима (min_length=1)
        ("   ", 422),        # Строка только из пробелов не должна проходить валидацию
        ("A", 201),          # Минимальная длина (1 символ)
        ("A" * 150, 201),    # Максимальная длина (150 символов)
        ("A" * 151, 422),    # Превышение max_length=150
        (None, 422),         # None вместо строки
    ],
)
def test_course_title_boundaries(client: TestClient, title, expected_status):
    payload = {
        "title": title,
        "teacher": "Преподаватель",
        "capacity": 20,
    }
    response = client.post("/courses", json=payload)
    assert response.status_code == expected_status


# ============================================================================
# 3. Параметризованные тесты на обработку ошибок (404, 409, 422)
# ============================================================================
@pytest.mark.parametrize(
    "method,endpoint,payload,expected_status",
    [
        ("GET", "/courses/99999", None, 404),
        ("GET", "/students/99999", None, 404),
        ("GET", "/applications/99999", None, 404),
        ("PATCH", "/courses/99999", {"capacity": 10}, 404),
        ("PATCH", "/students/99999", {"rating": 90.0}, 404),
        ("DELETE", "/courses/99999", None, 404),
        ("DELETE", "/applications/99999", None, 404),
        ("POST", "/students", {"full_name": "Тест", "group_name": "ИС", "rating": -1.0}, 422),
        ("POST", "/students", {"full_name": "Тест", "group_name": "ИС", "rating": 105.0}, 422),
        ("POST", "/applications", {"student_id": 1, "course_id": 1, "priority": 0}, 422),
        ("POST", "/applications", {"student_id": 1, "course_id": 1, "priority": 4}, 422),
    ],
)
def test_error_handling_statuses(client: TestClient, method, endpoint, payload, expected_status):
    if method == "GET":
        resp = client.get(endpoint)
    elif method == "POST":
        resp = client.post(endpoint, json=payload)
    elif method == "PATCH":
        resp = client.patch(endpoint, json=payload)
    elif method == "DELETE":
        resp = client.delete(endpoint)
    else:
        pytest.fail(f"Неизвестный HTTP-метод: {method}")

    assert resp.status_code == expected_status


def test_conflict_duplicate_priority_for_same_student(client: TestClient):
    """
    Бизнес-правило: Студент не может подать две заявки с одинаковым приоритетом.
    При попытке назначить одинаковый приоритет разным курсам система должна возвращать 409.
    """
    s_res = client.post("/students", json={"full_name": "Иванов Иван", "group_name": "ИС-20", "rating": 85.0})
    c1_res = client.post("/courses", json={"title": "Курс 1", "teacher": "У1", "capacity": 10})
    c2_res = client.post("/courses", json={"title": "Курс 2", "teacher": "У2", "capacity": 10})

    student_id = s_res.json()["id"]
    course1_id = c1_res.json()["id"]
    course2_id = c2_res.json()["id"]

    # Первая заявка с приоритетом 1
    res1 = client.post(
        "/applications",
        json={"student_id": student_id, "course_id": course1_id, "priority": 1},
    )
    assert res1.status_code == 201

    # Вторая заявка того же студента с тем же приоритетом 1 на другой курс -> 409 Conflict
    res2 = client.post(
        "/applications",
        json={"student_id": student_id, "course_id": course2_id, "priority": 1},
    )
    assert res2.status_code == 409
    assert "приоритет" in res2.json().get("detail", "").lower()


# ============================================================================
# 4. Пять интеграционных тестов API
# ============================================================================
def test_integration_1_course_crud_lifecycle(client: TestClient):
    """Интеграционный тест 1: Полный жизненный цикл курса (GET -> POST -> PATCH -> DELETE -> 404)."""
    # 1. Список курсов пуст
    assert len(client.get("/courses").json()) == 0

    # 2. Создание
    c_res = client.post("/courses", json={"title": "Облачные вычисления", "teacher": "Кузнецов В.В.", "capacity": 15})
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    # 3. Чтение деталей
    detail_res = client.get(f"/courses/{course_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Облачные вычисления"

    # 4. Частичное обновление (PATCH)
    patch_res = client.patch(f"/courses/{course_id}", json={"capacity": 25})
    assert patch_res.status_code == 200
    assert patch_res.json()["capacity"] == 25
    assert patch_res.json()["title"] == "Облачные вычисления"

    # 5. Удаление
    del_res = client.delete(f"/courses/{course_id}")
    assert del_res.status_code == 200

    # 6. Проверка отсутствия
    assert client.get(f"/courses/{course_id}").status_code == 404


def test_integration_2_student_and_application_flow(client: TestClient):
    """Интеграционный тест 2: Связанный сценарий студент -> курс -> заявка -> фильтрация -> удаление."""
    s = client.post("/students", json={"full_name": "Павлов П.П.", "group_name": "ИС-22", "rating": 92.0}).json()
    c = client.post("/courses", json={"title": "Нейросети", "teacher": "Прохоров", "capacity": 10}).json()

    # Подача заявки
    app = client.post("/applications", json={"student_id": s["id"], "course_id": c["id"], "priority": 1}).json()
    assert app["id"] is not None
    assert app["status"] == "new"

    # Проверка отображения в фильтрах
    apps_by_student = client.get(f"/applications?student_id={s['id']}").json()
    assert len(apps_by_student) == 1
    assert apps_by_student[0]["course_id"] == c["id"]

    # Удаление заявки
    del_app = client.delete(f"/applications/{app['id']}")
    assert del_app.status_code == 200
    assert len(client.get(f"/applications?student_id={s['id']}").json()) == 0


def test_integration_3_nonexistent_ids_consistency(client: TestClient):
    """Интеграционный тест 3: Консистентная обработка несуществующих ID (404) во всех методах."""
    bogus_id = 888888
    assert client.get(f"/courses/{bogus_id}").status_code == 404
    assert client.get(f"/students/{bogus_id}").status_code == 404
    assert client.get(f"/applications/{bogus_id}").status_code == 404
    assert client.patch(f"/courses/{bogus_id}", json={"capacity": 5}).status_code == 404
    assert client.patch(f"/students/{bogus_id}", json={"rating": 80.0}).status_code == 404
    assert client.delete(f"/courses/{bogus_id}").status_code == 404
    assert client.delete(f"/applications/{bogus_id}").status_code == 404


def test_integration_4_empty_post_request(client: TestClient):
    """Интеграционный тест 4: Отправка пустого тела запроса в POST эндпоинты."""
    # Пустой POST без тела
    resp_empty_course = client.post("/courses", content=b"", headers={"Content-Type": "application/json"})
    assert resp_empty_course.status_code == 422

    resp_empty_student = client.post("/students", content=b"", headers={"Content-Type": "application/json"})
    assert resp_empty_student.status_code == 422

    resp_empty_app = client.post("/applications", content=b"", headers={"Content-Type": "application/json"})
    assert resp_empty_app.status_code == 422


def test_integration_5_malformed_json_payload(client: TestClient):
    """Интеграционный тест 5: Передача синтаксически невалидного JSON."""
    malformed_raw_bytes = b'{"title": "Broken JSON", "capacity": '  # оборванный JSON
    resp = client.post(
        "/courses",
        content=malformed_raw_bytes,
        headers={"Content-Type": "application/json"},
    )
    # FastAPI возвращает 422 или 400 при синтаксически битом JSON
    assert resp.status_code in (400, 422)
