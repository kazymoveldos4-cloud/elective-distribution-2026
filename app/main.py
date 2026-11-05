from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import applications, courses, students
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="АРМ Замдекана: элективные курсы", lifespan=lifespan)

app.include_router(students.router)
app.include_router(courses.router)
app.include_router(applications.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "АРМ Замдекана: модуль элективных курсов работает"}
