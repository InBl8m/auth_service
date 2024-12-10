from sqlalchemy.orm import Session
from app.api.models import User
from app.core.security import hash_password


# Создание нового пользователя
def create_user(db: Session, username: str, email: str, password: str):
    hashed_password = hash_password(password)
    db_user = User(username=username, email=email, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# Получение пользователя по имени пользователя
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


# Получение пользователя по ID
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


# Проверка наличия пользователя по email
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


# Обновление информации о пользователе
def update_user(db: Session, user_id: int, username: str, email: str, password: str):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.username = username
        db_user.email = email
        db_user.password = hash_password(password)  # Обновляем пароль
        db.commit()
        db.refresh(db_user)
        return db_user
    return None


# Удаление пользователя
def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return db_user
    return None
