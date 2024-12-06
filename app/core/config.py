from pydantic_settings import BaseSettings
from pydantic import PostgresDsn
import secrets


class Settings(BaseSettings):
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    SECRET_KEY: str = secrets.token_urlsafe(32)

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return (f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")

    class Config:
        env_file = ".env"

settings = Settings()
