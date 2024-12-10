from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi import APIRouter, Form, Request, Depends, HTTPException, status, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.db import SessionLocal
from app.api.models import User, Role
from app.api.schemas import Token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(request: Request):
    # Извлекаем токен из куки
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found in cookies",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Декодируем токен
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# Dependency для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def handle_registration(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Проверка наличия роли "default"
    default_role = db.query(Role).filter(Role.name == "default").first()
    if not default_role:
        # Если роль не существует, создаём её
        default_role = Role(name="default")
        db.add(default_role)
        db.commit()
        db.refresh(default_role)

    # Хэширование пароля
    hashed_password = hash_password(password)

    # Создание нового пользователя с ролью по умолчанию
    new_user = User(username=username, email=email, password=hashed_password, role_id=default_role.id)
    db.add(new_user)
    db.commit()

    return RedirectResponse("/login", status_code=303)


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password):
        access_token = create_access_token(data={"sub": user.username, "role": user.role.name})
        new_refresh_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(days=7))
        response = RedirectResponse(url="/dashboard", status_code=302)  # для шаблонов
        # response = JSONResponse(content={"message": "Login successful"})
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        response.set_cookie("refresh_token", new_refresh_token, httponly=True, path="/refresh-token")
        return response

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.get("/dashboard")
async def dashboard_page(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": current_user["sub"]})


@router.get("/debug-token")
async def debug_token(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return {"error": "Token not found in cookies"}
    try:
        payload = decode_access_token(token)
        return {"token": token, "payload": payload}
    except Exception as e:
        return {"error": "Invalid token", "details": str(e)}


@router.post("/refresh-token")
async def refresh_token_handler(refresh_token: str = Cookie(None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    payload = decode_access_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(data={"sub": payload["sub"]}, expires_delta=timedelta(minutes=15))

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    # Удаляем токен из куки
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/refresh-token")
    return response
