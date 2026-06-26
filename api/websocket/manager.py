import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Rastreia conexões WebSocket abertas por canal:
    - events_subs: clientes que consomem a lista geral de eventos (canal events_sports)
    - markets_subs: clientes que acompanham mercados de um evento específico (canal events_sports_markets)
    """

    def __init__(self):
        self.events_subs: set[WebSocket] = set()
        self.markets_subs: dict[str, set[WebSocket]] = {}

    # ── events_sports ──────────────────────────────────────────────────────────

    def add_events_sub(self, ws: WebSocket) -> None:
        self.events_subs.add(ws)

    def remove_events_sub(self, ws: WebSocket) -> None:
        self.events_subs.discard(ws)

    async def broadcast_events(self, data: str) -> None:
        dead: set[WebSocket] = set()
        for ws in self.events_subs:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.events_subs.discard(ws)

    # ── events_sports_markets ──────────────────────────────────────────────────

    def add_market_sub(self, ws: WebSocket, enet_code: str) -> None:
        self.markets_subs.setdefault(enet_code, set()).add(ws)

    def remove_market_sub(self, ws: WebSocket, enet_code: str) -> None:
        if enet_code in self.markets_subs:
            self.markets_subs[enet_code].discard(ws)

    def remove_all_market_subs(self, ws: WebSocket) -> None:
        for subs in self.markets_subs.values():
            subs.discard(ws)

    async def broadcast_to_market(self, enet_code: str, data: str) -> None:
        dead: set[WebSocket] = set()
        for ws in self.markets_subs.get(enet_code, set()):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        if enet_code in self.markets_subs:
            for ws in dead:
                self.markets_subs[enet_code].discard(ws)


manager = ConnectionManager()
