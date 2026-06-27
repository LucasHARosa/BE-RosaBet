from datetime import datetime
from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    value: float = Field(..., gt=0)


class DepositResponse(BaseModel):
    id: str
    type: str
    status: str
    value: float
    bonus: float
    qr_code: str | None
    qr_code_image: str | None
    expiration_date: datetime | None
    confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WelcomeVerificationResponse(BaseModel):
    is_first_deposit: bool
    bonus_percentage: int
    bonus_max_value: float
