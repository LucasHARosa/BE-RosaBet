import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_serializer


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

    @model_serializer
    def to_frontend(self) -> dict:
        return {
            "_id": str(self.id),
            "event": self.enet_code,
            "market": str(self.market_id),
            "selection": self.option_id,
            "odd": float(self.quotation),
            "is_live": self.is_live,
            "status": self.status,
        }


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

    @model_serializer
    def to_frontend(self) -> dict:
        return {
            "_id": str(self.id),
            "code": self.code,
            "status": self.status,
            "amount": float(self.value),
            "total_odd": float(self.extracted_quotation),
            "potential_gain": float(self.return_value),
            "spend_from": self.spend_from,
            "type": self.type,
            "qtt_sports": self.qtt_sports,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "selections": [item.model_dump() for item in self.items],
        }
