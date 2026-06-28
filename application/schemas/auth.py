from pydantic import BaseModel

from application.schemas.client import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user: UserResponse


class RegisterResponse(BaseModel):
    token: str
