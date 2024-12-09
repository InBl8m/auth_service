from fastapi import APIRouter, Form, Request, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.api.models import User
from app.core.security import get_password_hash, verify_password
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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
    hashed_password = get_password_hash(password)
    # Сохраняем нового пользователя в базе
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return RedirectResponse("/login", status_code=303)


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Поиск пользователя в базе данных
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.hashed_password):
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("username", username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@router.get("/dashboard")
async def dashboard_page(request: Request):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username})


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("username")
    return response
