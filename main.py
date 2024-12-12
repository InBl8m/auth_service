from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Разрешить React-приложение
    allow_credentials=True,                  # Если вы используете cookies
    allow_methods=["*"],                     # Разрешить все HTTP-методы
    allow_headers=["*"],                     # Разрешить все заголовки
)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.include_router(router)
