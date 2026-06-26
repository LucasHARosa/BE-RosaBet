import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.websocket.manager import manager
from application.use_cases.sport.get_open_events import GetOpenEventsUseCase, event_to_game_props
from infrastructure.database.session import AsyncSessionLocal
import infrastructure.repositories.event_repository as event_repo

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_all_events_json() -> str:
    async with AsyncSessionLocal() as db:
        events = await event_repo.get_open_events(db)
    return json.dumps([event_to_game_props(e) for e in events], ensure_ascii=False)


async def _get_event_json(enet_code: str) -> str | None:
    async with AsyncSessionLocal() as db:
        event = await event_repo.get_by_enet_code(db, enet_code)
    if not event:
        return None
    return json.dumps(event_to_game_props(event), ensure_ascii=False)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = Query(...),
):
    await websocket.accept()

    if channel == "events_sports":
        await _handle_events_sports(websocket)

    elif channel == "events_sports_markets":
        await _handle_events_markets(websocket)

    elif channel == "properties":
        await _handle_properties(websocket)

    elif channel == "highlights":
        await _handle_highlights(websocket)

    else:
        await websocket.close(code=1008, reason=f"Canal desconhecido: {channel}")


async def _handle_events_sports(ws: WebSocket) -> None:
    """
    Canal events_sports: envia GameProps[] imediatamente ao conectar.
    Atualizações chegam via Redis → ConnectionManager.broadcast_events().
    """
    manager.add_events_sub(ws)
    try:
        data = await _get_all_events_json()
        await ws.send_text(data)

        # mantém a conexão aberta; desconexão lança WebSocketDisconnect
        while True:
            await asyncio.sleep(30)
            # heartbeat — reenvia estado atual para clientes que ficam muito tempo sem update
            data = await _get_all_events_json()
            await ws.send_text(data)

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.remove_events_sub(ws)


async def _handle_events_markets(ws: WebSocket) -> None:
    """
    Canal events_sports_markets: cliente envia "insert|enet_code|sr:match:10001"
    para se inscrever. Atualizações chegam via Redis → manager.broadcast_to_market().

    Protocolo (socket.ts):
      - "insert|key|value"  → inscreve no evento
      - "delete|key|value"  → cancela inscrição
      - "OK"                → confirmação (ignorar)
    """
    try:
        while True:
            raw = await ws.receive_text()

            if raw == "OK":
                continue

            parts = raw.split("|")
            if len(parts) != 3:
                continue

            action, key, value = parts

            if key != "enet_code":
                continue

            enet_code = value

            if action == "insert":
                manager.add_market_sub(ws, enet_code)
                data = await _get_event_json(enet_code)
                if data:
                    await ws.send_text(f"[{data}]")

            elif action == "delete":
                manager.remove_market_sub(ws, enet_code)

    except WebSocketDisconnect:
        pass
    finally:
        manager.remove_all_market_subs(ws)


async def _handle_properties(ws: WebSocket) -> None:
    """Canal properties: informa status da conexão do servidor."""
    try:
        await ws.send_text(json.dumps([{"connection_down": False}]))
        while True:
            await asyncio.sleep(60)
            await ws.send_text(json.dumps([{"connection_down": False}]))
    except (WebSocketDisconnect, Exception):
        pass


async def _handle_highlights(ws: WebSocket) -> None:
    """Canal highlights: retorna lista de destaques (stub — implementado na Fase 9)."""
    try:
        await ws.send_text(json.dumps([]))
        while True:
            await asyncio.sleep(60)
    except (WebSocketDisconnect, Exception):
        pass
