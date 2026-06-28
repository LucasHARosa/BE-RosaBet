import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator, model_serializer


class RegisterRequest(BaseModel):
    name: str
    email: str
    cpf: str
    password: str
    username: str | None = None
    phone: str | None = None
    birth_date: datetime | None = None

    @field_validator("cpf")
    @classmethod
    def cpf_only_digits(cls, v: str) -> str:
        digits = "".join(filter(str.isdigit, v))
        if len(digits) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return digits

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Nome deve ter pelo menos 3 caracteres")
        return v.strip()


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    username: str | None = None
    phone: str | None = None
    currency: str | None = None
    notification_sms: bool | None = None
    notification_email: bool | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) < 3:
            raise ValueError("Nome deve ter pelo menos 3 caracteres")
        return v.strip() if v else v


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Nova senha deve ter pelo menos 6 caracteres")
        return v


class UpdateActiveRequest(BaseModel):
    active: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    username: str
    email: str
    cpf: str
    phone: str | None = None
    birth_date: datetime | None = None
    type: str
    credits: float
    casino_credits: float
    sports_bonus: float
    retained_credit: float
    currency: str
    email_confirmed: bool
    active: bool
    notification_sms: bool
    notification_email: bool
    created_at: datetime
    token: str | None = None

    @model_serializer
    def to_frontend(self) -> dict:
        return {
            "_id": str(self.id),
            "name": self.name,
            "username": self.username,
            "email": self.email,
            "cpf": self.cpf,
            "phone": self.phone,
            "birthDate": self.birth_date.date().isoformat() if self.birth_date else None,
            "type": self.type.lower(),
            "credits": float(self.credits),
            "casino_credits": float(self.casino_credits),
            "sports_bonus": float(self.sports_bonus),
            "retained_credit": float(self.retained_credit),
            "currency": self.currency,
            "email_confirmed": self.email_confirmed,
            "active": self.active,
            "notification_sms": self.notification_sms,
            "notification_email": self.notification_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "token": self.token,
        }
