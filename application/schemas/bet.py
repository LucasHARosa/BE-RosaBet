import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_serializer, model_validator


class BetItemRequest(BaseModel):
    enet_code: str
    market_id: int = 0
    odd_id: str = ""
    option_id: str
    quotation: float
    is_live: bool = False
    specifier: dict | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, v: dict) -> dict:
        # frontend sends "oddId" instead of "odd_id"
        if "oddId" in v and not v.get("odd_id"):
            v["odd_id"] = v["oddId"]
        # derive market_id from odd_id ("186::1" → 186) if not provided
        if not v.get("market_id") and v.get("odd_id"):
            try:
                v["market_id"] = int(str(v["odd_id"]).split("::")[0])
            except (ValueError, IndexError):
                v["market_id"] = 0
        return v


class BetRequest(BaseModel):
    value: float
    spend_from: str = "credits"
    accept_all_changes: bool = False
    only_accept_high: bool = False
    sports: list[BetItemRequest]

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, v: dict) -> dict:
        if "accept_all_odds_change" in v:
            v.setdefault("accept_all_changes", v["accept_all_odds_change"])
        if "only_accept_high_odds_change" in v:
            v.setdefault("only_accept_high", v["only_accept_high_odds_change"])
        # "wallet" is the frontend alias for the "credits" column on the User model
        if v.get("spend_from") == "wallet":
            v["spend_from"] = "credits"
        return v


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
