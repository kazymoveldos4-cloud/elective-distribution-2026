import os
import requests
import streamlit as st

BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="АРМ Замдекана", layout="wide")

st.title("АРМ Замдекана: модуль распределения элективных курсов")

# Боковая панель с описанием проекта
with st.sidebar:
    st.header("О проекте")
    st.write(
        """
        **АРМ Замдекана** — модуль автоматизированного распределения студентов 
        по элективным курсам с учетом их успеваемости (рейтинга) и приоритетов в заявках.
        
        **Алгоритм распределения:**
        1. Студенты сортируются по рейтингу по убыванию.
        2. Заявки каждого студента рассматриваются по приоритетам (1, 2, 3).
        3. При наличии свободных мест студент зачисляется на курс.
        """
    )
    st.info(f"Адрес бэкенда: `{BASE_URL}`")


def api_request(method: str, endpoint: str, **kwargs):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=5, **kwargs)
        return response
    except requests.exceptions.RequestException:
        st.error(f"Бэкенд недоступен по адресу {BASE_URL}. Проверьте, запущен ли сервер FastAPI.")
        return None


# 1. Секция: Курсы
st.header("Элективные курсы")

search_query = st.text_input("Поиск курса по названию", "")
courses_params = {}
if search_query.strip():
    courses_params["search"] = search_query.strip()

courses_resp = api_request("GET", "/courses", params=courses_params)
if courses_resp is not None:
    if courses_resp.status_code == 200:
        courses_data = courses_resp.json()
        st.dataframe(courses_data, use_container_width=True)
    else:
        st.error(f"Ошибка получения списка курсов: {courses_resp.status_code}")

st.divider()

# 2. Секция: Заявки
st.header("Заявки студентов")

status_filter = st.selectbox(
    "Фильтр по статусу заявки",
    options=["Все", "new", "approved", "rejected"],
    index=0,
)
apps_params = {}
if status_filter != "Все":
    apps_params["status"] = status_filter

apps_resp = api_request("GET", "/applications", params=apps_params)
if apps_resp is not None:
    if apps_resp.status_code == 200:
        apps_data = apps_resp.json()
        st.dataframe(apps_data, use_container_width=True)
    else:
        st.error(f"Ошибка получения списка заявок: {apps_resp.status_code}")

st.divider()

# 3. Секция: Создание курса или заявки
st.header("Создание данных")

create_type = st.radio(
    "Выберите тип создаваемой сущности:",
    options=["Курс", "Заявка"],
    horizontal=True,
)

if create_type == "Курс":
    with st.form("create_course_form", clear_on_submit=True):
        st.subheader("Новый курс")
        c_title = st.text_input("Название курса", placeholder="Например: Архитектура облачных систем")
        c_teacher = st.text_input("Преподаватель", placeholder="Например: Сидоров С.С.")
        c_capacity = st.number_input("Вместимость курса (мест)", min_value=1, max_value=500, value=15, step=1)
        submit_course = st.form_submit_button("Создать курс")

        if submit_course:
            payload = {
                "title": c_title.strip(),
                "teacher": c_teacher.strip(),
                "capacity": int(c_capacity),
            }
            resp = api_request("POST", "/courses", json=payload)
            if resp is not None:
                if resp.status_code == 201:
                    st.success(f"Курс «{c_title}» успешно создан (ID: {resp.json().get('id')})!")
                    st.rerun()
                else:
                    try:
                        detail = resp.json().get("detail", resp.text)
                    except Exception:
                        detail = resp.text
                    st.error(f"Ошибка создания курса ({resp.status_code}): {detail}")

else:
    with st.form("create_app_form", clear_on_submit=True):
        st.subheader("Новая заявка")
        a_student_id = st.number_input("ID студента", min_value=1, step=1)
        a_course_id = st.number_input("ID курса", min_value=1, step=1)
        a_priority = st.selectbox("Приоритет (1 — наивысший)", options=[1, 2, 3], index=0)
        submit_app = st.form_submit_button("Создать заявку")

        if submit_app:
            payload = {
                "student_id": int(a_student_id),
                "course_id": int(a_course_id),
                "priority": int(a_priority),
            }
            resp = api_request("POST", "/applications", json=payload)
            if resp is not None:
                if resp.status_code == 201:
                    st.success(f"Заявка успешно создана (ID: {resp.json().get('id')})!")
                    st.rerun()
                else:
                    try:
                        detail = resp.json().get("detail", resp.text)
                    except Exception:
                        detail = resp.text
                    st.error(f"Ошибка создания заявки ({resp.status_code}): {detail}")

st.divider()

# 4. Секция: Удаление курса
st.header("Удаление курса")
with st.form("delete_course_form"):
    del_course_id = st.number_input("ID курса для удаления", min_value=1, step=1)
    submit_delete = st.form_submit_button("Удалить курс")

    if submit_delete:
        resp = api_request("DELETE", f"/courses/{int(del_course_id)}")
        if resp is not None:
            if resp.status_code == 200:
                try:
                    msg = resp.json().get("message", "Курс успешно удален")
                except Exception:
                    msg = "Курс успешно удален"
                st.success(f"Ответ сервера (200): {msg}")
                st.rerun()
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                st.error(f"Ответ сервера ({resp.status_code}): {detail}")
