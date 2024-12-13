from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi import APIRouter, Form, Request, Depends, HTTPException, status, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.db import SessionLocal
from app.api.models import User, Role, Contact
from app.api.schemas import Token, AddContactRequest
from app.api.google_auth import router as google_auth_router


router = APIRouter()
router.include_router(google_auth_router, tags=["google_auth"])
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
        # Перенаправляем на dashboard для шаблонов FastApi
        # response = RedirectResponse(url="/dashboard", status_code=302)
        response = JSONResponse(content={"message": "Login successful"})
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        response.set_cookie("refresh_token", new_refresh_token, httponly=True, path="/refresh-token")
        return response

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


def get_user_and_contact_by_username(current_user: dict, contact_username: str, db: Session):
    # Получаем пользователя по текущему токену
    user = db.query(User).filter(User.username == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Current user not found")

    # Получаем контакт по имени
    contact = db.query(User).filter(User.username == contact_username).first()
    if not contact:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем, что контакт существует в базе
    existing_contact = db.query(Contact).filter(Contact.user_id == user.id, Contact.contact_id == contact.id).first()

    return user, contact, existing_contact


@router.post("/add-contact")
async def add_contact(
    request: AddContactRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact_username = request.contact_username
    if contact_username == current_user["sub"]:
        raise HTTPException(status_code=400, detail="You cannot add yourself as a contact")

    # Получаем текущего пользователя и целевого контакта
    user, contact, existing_contact = get_user_and_contact_by_username(current_user, contact_username, db)

    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact already exists")

    # Добавляем новый контакт с confirmed=0
    new_contact = Contact(user_id=user.id, contact_id=contact.id, confirmed=0)
    db.add(new_contact)
    db.commit()

    # Проверяем, есть ли запись, где contact.id -> user.id с confirmed=0
    reciprocal_contact = (
        db.query(Contact)
        .filter(Contact.user_id == contact.id, Contact.contact_id == user.id, Contact.confirmed == 0)
        .first()
    )

    if reciprocal_contact:
        # Если такая запись есть, обновляем обе записи на confirmed=1
        new_contact.confirmed = 1
        reciprocal_contact.confirmed = 1
        db.commit()
        return {"message": "Contact confirmed from both sides!"}

    return {"message": "Contact added successfully, waiting for confirmation from the other side."}


@router.get("/pending-requests")
async def pending_requests(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Получаем текущего пользователя
    user = db.query(User).filter(User.username == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Находим все запросы, где текущий пользователь является contact_id и статус не подтверждён
    pending = (
        db.query(User, Contact)
        .join(Contact, User.id == Contact.user_id)
        .filter(Contact.contact_id == user.id, Contact.confirmed == 0)
        .all()
    )

    # Формируем список запросов
    pending_list = [
        {
            "id": requester[0].id,  # Данные пользователя, который отправил запрос
            "username": requester[0].username,
            "request_id": requester[1].id  # ID связи в таблице Contact
        }
        for requester in pending
    ]

    return {"pending_requests": pending_list}


@router.delete("/remove-contact")
async def remove_contact(
    contact_username: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Используем вспомогательную функцию
    user, contact, existing_contact = get_user_and_contact_by_username(current_user, contact_username, db)

    if not existing_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Удаляем запись текущего пользователя
    db.delete(existing_contact)

    # Удаляем запись контакта, если существует
    reciprocal_contact = db.query(Contact).filter(
        Contact.user_id == contact.id,
        Contact.contact_id == user.id,
    ).first()

    if reciprocal_contact:
        db.delete(reciprocal_contact)

    db.commit()

    return {"message": f"Contact with username {contact_username} removed successfully for both users"}


@router.get("/search-user")
async def search_users(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Получаем всех пользователей, соответствующих запросу
    users = db.query(User).filter(User.username.ilike(f"%{query}%")).all()
    # Получаем текущего пользователя
    user = db.query(User).filter(User.username == current_user["sub"]).first()
    # Получаем список контактов текущего пользователя
    contacts = db.query(Contact).filter(Contact.user_id == user.id).all()
    contact_ids = [contact.contact_id for contact in contacts]
    # Исключаем текущего пользователя и уже добавленных контактов
    filtered_users = [
        {"id": user.id, "username": user.username}
        for user in users
        if user and user.username != current_user["sub"] and user.id not in contact_ids
    ]

    return filtered_users


@router.get("/user-info")
async def user_info(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    contacts = db.query(User, Contact).join(Contact,
                                            User.id == Contact.contact_id).filter(Contact.user_id == user.id).all()
    contact_list = [
        {
            "id": contact[0].id,
            "username": contact[0].username,
            "confirmed": contact[1].confirmed
        }
        for contact in contacts
    ]

    return {"username": user.username, "role": user.role.name, "contacts": contact_list}


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
