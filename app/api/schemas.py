from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    role: str | None = None


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True


class AddContactRequest(BaseModel):
    contact_username: str