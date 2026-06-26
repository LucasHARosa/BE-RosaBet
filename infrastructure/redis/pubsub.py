import asyncio
import json
import logging

from infrastructure.redis.client import get_redis

logger = logging.getLogger(__name__)

CHANNEL_EVENTS_SPORTS = "events_sports"
CHANNEL_EVENT_PREFIX = "event:"


async def publish(channel: str, data: any) -> None:
    redis = get_redis()
    payload = json.dumps(data, ensure_ascii=False)
    await redis.publish(channel, payload)


async def start_pubsub_listener(manager) -> None:
    """
    Task de fundo que escuta todos os canais Redis e despacha para o ConnectionManager.
    - events_sports → broadcast para todos os clientes da lista de eventos
    - event:* → broadcast para clientes do canal de mercados desse evento
    """
    redis = get_redis()
    pubsub = redis.pubsub()

    await pubsub.subscribe(CHANNEL_EVENTS_SPORTS)
    await pubsub.psubscribe(f"{CHANNEL_EVENT_PREFIX}*")

    logger.info("Redis pub/sub listener iniciado")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                data = message["data"]
                await manager.broadcast_events(data)

            elif message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]
                enet_code = channel.removeprefix(CHANNEL_EVENT_PREFIX)
                await manager.broadcast_to_market(enet_code, data)

    except asyncio.CancelledError:
        logger.info("Redis pub/sub listener encerrado")
    finally:
        await pubsub.unsubscribe()
        await pubsub.punsubscribe()
        await pubsub.aclose()
