from sqlmodel import Session, select
from passlib.context import CryptContext
from app.models import User, UserCreate
from sqlalchemy.exc import IntegrityError


# Инициализация контекста для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.exec(select(User).where(User.email == email)).first()


def create_user(db: Session, user_create: UserCreate) -> User:
    hashed_password = pwd_context.hash(user_create.password)
    db_user = User(email=user_create.email, hashed_password=hashed_password, is_superuser=user_create.is_superuser)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise ValueError("User with this email already exists.")
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user and pwd_context.verify(password, user.hashed_password):
        return user
    return None
