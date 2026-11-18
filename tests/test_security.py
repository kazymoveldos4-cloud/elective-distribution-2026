import pytest
from fastapi.testclient import TestClient


def test_empty_and_invalid_payloads(client: TestClient):
    """Проверка отклонения пустых и некорректных структур данных."""
    # Пустой JSON
    res1 = client.post("/courses", json={})
    assert res1.status_code == 422

    res2 = client.post("/students", json={})
    assert res2.status_code == 422

    res3 = client.post("/applications", json={})
    assert res3.status_code == 422

    # Некорректные типы полей (передаём строку вместо int/float)
    res4 = client.post(
        "/students",
        json={"full_name": "Тест", "group_name": "ИС", "rating": "отличник"},
    )
    assert res4.status_code == 422

    res5 = client.post(
        "/courses",
        json={"title": "Тест", "teacher": "Учитель", "capacity": "много"},
    )
    assert res5.status_code == 422


@pytest.mark.parametrize(
    "sqli_payload",
    [
        "' OR '1'='1",
        "'; DROP TABLE course; --",
        "' UNION SELECT 1, 'hacked', 'hacked', 99 --",
        "1' OR capacity > 0 --",
        "'--",
        "admin'/*",
        "' OR 1=1 #",
    ],
)
def test_sql_injection_in_search_does_not_break_system(client: TestClient, sqli_payload: str):
    """
    SQL-инъекция в параметре search не должна ломать систему,
    не должна приводить к 500 Internal Server Error или удалению таблиц.
    """
    # Создаём контрольный курс
    client.post("/courses", json={"title": "Компьютерные сети", "teacher": "Петров", "capacity": 20})

    # Отправляем запрос с SQLi-пейлоадом
    response = client.get(f"/courses?search={sqli_payload}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Пейлоад трактуется буквально как подстрока, инъекция не срабатывает
    assert len(data) == 0

    # Проверяем, что таблица course цела и контрольный курс доступен
    all_courses = client.get("/courses").json()
    assert any(c["title"] == "Компьютерные сети" for c in all_courses)


def test_error_responses_do_not_leak_traces_or_paths(client: TestClient):
    """
    Ответы на ошибки (404, 409, 422) не должны раскрывать трассировку стека,
    локальные пути файловой системы сервера или внутренние детали интерпретатора.
    """
    # 404 Not Found
    res_404 = client.get("/courses/999999")
    assert res_404.status_code == 404
    text_404 = res_404.text

    # 422 Validation Error
    res_422 = client.post("/students", json={"rating": 999})
    assert res_422.status_code == 422
    text_422 = res_422.text

    for response_text in [text_404, text_422]:
        lower_text = response_text.lower()
        assert "traceback (most recent call last)" not in lower_text
        assert "c:\\users" not in lower_text
        assert ".py\", line" not in lower_text
        assert "site-packages" not in lower_text


def test_absence_of_sensitive_data_in_responses(client: TestClient):
    """Проверка отсутствия паролей, секретных ключей или токенов в ответах API."""
    res = client.get("/courses")
    assert res.status_code == 200
    content = res.text.lower()
    for sensitive_keyword in ["password", "secret_key", "private_key", "bearer"]:
        assert sensitive_keyword not in content
