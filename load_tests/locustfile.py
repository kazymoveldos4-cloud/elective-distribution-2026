import random
from locust import HttpUser, between, task


class DeanWorkstationUser(HttpUser):
    # Пауза между запросами пользователя от 0.1 до 0.5 секунды
    wait_time = between(0.1, 0.5)

    search_terms = ["Machine", "Веб", "дизайн", "кибер", "основы", "информатика", "data"]

    @task(6)
    def get_courses(self):
        """Просмотр общего каталога курсов."""
        self.client.get("/courses", name="/courses")

    @task(5)
    def search_courses(self):
        """Поиск курса по названию (параметр search)."""
        term = random.choice(self.search_terms)
        self.client.get(f"/courses?search={term}", name="/courses?search=[term]")

    @task(5)
    def get_applications(self):
        """Просмотр списка заявок студентов."""
        self.client.get("/applications", name="/applications")

    @task(3)
    def filter_applications_by_status(self):
        """Фильтрация заявок по статусу."""
        status = random.choice(["new", "approved", "rejected"])
        self.client.get(f"/applications?status={status}", name="/applications?status=[status]")

    @task(1)
    def create_course(self):
        """Создание нового элективного курса (редкое действие)."""
        random_suffix = random.randint(1000, 9999999)
        payload = {
            "title": f"Курс {random_suffix}",
            "teacher": f"Преподаватель {random.randint(1, 50)}",
            "capacity": random.randint(5, 50),
        }
        self.client.post("/courses", json=payload, name="/courses [POST]")

    @task(1)
    def patch_course_or_student(self):
        """Обновление курса или студента (редкое действие)."""
        if random.random() < 0.5:
            # Обновление вместимости курса
            payload = {"capacity": random.randint(15, 60)}
            self.client.patch("/courses/1", json=payload, name="/courses/1 [PATCH]")
        else:
            # Обновление рейтинга студента
            payload = {"rating": round(random.uniform(70.0, 99.9), 1)}
            self.client.patch("/students/1", json=payload, name="/students/1 [PATCH]")
