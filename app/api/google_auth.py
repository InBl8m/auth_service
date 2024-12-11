from app.core.config import settings
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.requests import Request
from datetime import timedelta
from app.api.models import User, Role
from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.core.security import create_access_token


# Настройки приложения
config = Config(".env")  # Храните секреты в .env файле
oauth = OAuth(config)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Конфигурация Google OAuth2
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

router = APIRouter()


# Маршрут для начала авторизации
@router.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_auth_callback")  # Callback URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


# Маршрут для обработки ответа от Google
@router.get("/auth/google/callback")
async def google_auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        # Получение токена от Google
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")  # Получение информации о пользователе

        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        # Извлечение данных пользователя
        user_email = user_info["email"]
        user_name = user_info.get("name", "Google User")

        # Проверка, существует ли пользователь
        user = db.query(User).filter(User.email == user_email).first()

        if not user:
            # Создание новой роли, если она отсутствует
            default_role = db.query(Role).filter(Role.name == "default").first()
            if not default_role:
                default_role = Role(name="default")
                db.add(default_role)
                db.commit()
                db.refresh(default_role)

            # Создаём нового пользователя
            new_user = User(
                username=user_name,
                email=user_email,
                password="oauth_dummy_password",  # Для OAuth-пользователей пароль фиктивный
                role_id=default_role.id,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user

        # Создание токенов
        access_token = create_access_token(data={"sub": user.username, "role": user.role.name})
        refresh_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(days=7))

        # Установка токенов в cookies
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, path="/refresh-token")

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error during Google auth: {str(e)}")

