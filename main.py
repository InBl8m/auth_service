from fastapi import FastAPI
from app.api.routes import router

app = FastAPI()

# Подключаем роутер

app.include_router(router)
