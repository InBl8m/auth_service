from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import router
from app.core.config import settings

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.include_router(router)
