import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BetItemRequest(BaseModel):
    enet_code: str
    market_id: int
    odd_id: str
    option_id: str
    quotation: float
    is_live: bool = False
    specifier: dict | None = None


class BetRequest(BaseModel):
    value: float
    spend_from: str = "credits"
    accept_all_changes: bool = False
    only_accept_high: bool = False
    sports: list[BetItemRequest]


class BetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    enet_code: str
    market_id: int
    odd_id: str
    option_id: str
    quotation: float
    is_live: bool
    status: str


class BetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str | None
    status: str
    value: float
    return_value: float
    extracted_quotation: float
    spend_from: str | None
    type: str
    qtt_sports: int
    created_at: datetime
    items: list[BetItemResponse]
