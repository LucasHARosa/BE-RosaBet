from pydantic import BaseModel


class CasinoGameResponse(BaseModel):
    active: bool
    demo: bool
    desktop_id: str
    game_code: str
    game_image: str | None
    highlights: bool
    mobile_id: str
    name: str
    news: str | None
    on_the_rise: str | None
    provider: str
    type: str

    model_config = {"from_attributes": True}


class CasinoHighlightsResponse(BaseModel):
    amountGames: int
    label: str
    data: list[CasinoGameResponse]


class GameUrlRequest(BaseModel):
    symbol: str


class GameUrlResponse(BaseModel):
    gameURL: str
