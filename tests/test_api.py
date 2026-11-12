from fastapi.testclient import TestClient


def test_get_courses_empty_and_list(client: TestClient):
    # GET /courses возвращает 200 и пустой список вначале
    response = client.get("/courses")
    assert response.status_code == 200
    assert response.json() == []

    # Создаём курс и проверяем, что GET возвращает список с ним
    client.post("/courses", json={"title": "Теория графов", "teacher": "Петров П.П.", "capacity": 15})
    response = client.get("/courses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Теория графов"


def test_post_create_course(client: TestClient):
    payload = {
        "title": "Machine Learning",
        "teacher": "Ахметов А.К.",
        "capacity": 25,
    }
    response = client.post("/courses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["teacher"] == payload["teacher"]
    assert data["capacity"] == payload["capacity"]


def test_post_create_student(client: TestClient):
    payload = {
        "full_name": "Аскаров Нурлан",
        "group_name": "ИС-21",
        "rating": 95.5,
    }
    response = client.post("/students", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["full_name"] == payload["full_name"]
    assert data["group_name"] == payload["group_name"]
    assert data["rating"] == payload["rating"]


def test_post_invalid_data_422(client: TestClient):
    # Невалидный курс (отрицательная вместимость и пустое название)
    res_course = client.post("/courses", json={"title": "", "teacher": "Иванов", "capacity": -10})
    assert res_course.status_code == 422

    # Невалидный студент (рейтинг больше 100)
    res_student = client.post("/students", json={"full_name": "Тест", "group_name": "ИС", "rating": 150.0})
    assert res_student.status_code == 422

    # Невалидная заявка (приоритет вне диапазона 1-3)
    res_app = client.post("/applications", json={"student_id": 1, "course_id": 1, "priority": 5})
    assert res_app.status_code == 422


def test_get_courses_with_search(client: TestClient):
    client.post("/courses", json={"title": "Python для анализа данных", "teacher": "Т1", "capacity": 20})
    client.post("/courses", json={"title": "Архитектура ПО", "teacher": "Т2", "capacity": 15})

    # Поиск по подстроке
    res_search = client.get("/courses?search=Python")
    assert res_search.status_code == 200
    data = res_search.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python для анализа данных"

    # Поиск без совпадений
    res_empty = client.get("/courses?search=Несуществующий")
    assert res_empty.status_code == 200
    assert res_empty.json() == []


def test_patch_single_field(client: TestClient):
    # Создаём студента
    create_res = client.post(
        "/students",
        json={"full_name": "Бекова Айгерим", "group_name": "ИС-21", "rating": 91.0},
    )
    student_id = create_res.json()["id"]

    # Обновляем только rating
    patch_res = client.patch(f"/students/{student_id}", json={"rating": 98.5})
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["rating"] == 98.5
    # Проверяем, что остальные поля остались неизменными
    assert data["full_name"] == "Бекова Айгерим"
    assert data["group_name"] == "ИС-21"

    # Создаём курс и обновляем только capacity
    course_res = client.post("/courses", json={"title": "Веб-дизайн", "teacher": "Иванова Е.П.", "capacity": 10})
    course_id = course_res.json()["id"]

    patch_course = client.patch(f"/courses/{course_id}", json={"capacity": 25})
    assert patch_course.status_code == 200
    course_data = patch_course.json()
    assert course_data["capacity"] == 25
    assert course_data["title"] == "Веб-дизайн"
    assert course_data["teacher"] == "Иванова Е.П."


def test_patch_not_found_404(client: TestClient):
    res_student = client.patch("/students/99999", json={"rating": 50.0})
    assert res_student.status_code == 404

    res_course = client.patch("/courses/99999", json={"capacity": 10})
    assert res_course.status_code == 404


def test_delete_course_without_applications_200(client: TestClient):
    # Создаём курс
    course_res = client.post("/courses", json={"title": "Курс без заявок", "teacher": "Преподаватель", "capacity": 10})
    course_id = course_res.json()["id"]

    # Удаляем курс
    del_res = client.delete(f"/courses/{course_id}")
    assert del_res.status_code == 200
    assert "успешно удален" in del_res.json().get("message", "")

    # Проверяем, что курс удален из базы
    get_res = client.get(f"/courses/{course_id}")
    assert get_res.status_code == 404


def test_delete_course_with_applications_409(client: TestClient):
    # Создаём студента и курс
    s_res = client.post("/students", json={"full_name": "Сериков Данияр", "group_name": "ИС-22", "rating": 87.3})
    c_res = client.post("/courses", json={"title": "Кибербезопасность", "teacher": "Касымов Т.Р.", "capacity": 5})
    student_id = s_res.json()["id"]
    course_id = c_res.json()["id"]

    # Подаём заявку на этот курс
    app_res = client.post("/applications", json={"student_id": student_id, "course_id": course_id, "priority": 1})
    assert app_res.status_code == 201

    # Пытаемся удалить курс с существующей заявкой
    del_res = client.delete(f"/courses/{course_id}")
    assert del_res.status_code == 409
    assert "заявки" in del_res.json().get("detail", "")


def test_repeated_delete_404(client: TestClient):
    # Создаём и удаляем курс
    course_res = client.post("/courses", json={"title": "Временный курс", "teacher": "Тест", "capacity": 10})
    course_id = course_res.json()["id"]

    first_del = client.delete(f"/courses/{course_id}")
    assert first_del.status_code == 200

    # Повторное удаление того же ID должно вернуть 404
    second_del = client.delete(f"/courses/{course_id}")
    assert second_del.status_code == 404
