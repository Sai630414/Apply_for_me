from typing import Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse


class GoogleAuthRequest(BaseModel):
    id_token: str


class DevLoginRequest(BaseModel):
    email: EmailStr = "saikondareddypala@gmail.com"
    name: str = "Sai Konda Reddy"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

