"""WebSocket endpoint — real-time event push to the frontend.

Replaces the old architecture's 5-second HTTP polling with:
- Client WebSocket connection
- Server subscribes to Redis Pub/Sub channels
- Real-time event push (state changes, Agent thought streams, heartbeats, etc.)
"""

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..services.event_bus import get_event_bus

log = logging.getLogger("edict.ws")
router = APIRouter()

# Active connection management
_connections: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Main WebSocket endpoint — pushes all events."""
    await ws.accept()
    _connections.add(ws)
    log.info(f"WebSocket connected. Total: {len(_connections)}")

    # Create a separate Redis Pub/Sub connection
    settings = get_settings()
    pubsub_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = pubsub_redis.pubsub()

    # Subscribe to all edict channels
    await pubsub.psubscribe("edict:pubsub:*")

    try:
        # Concurrent: listen on Redis Pub/Sub + client messages
        await asyncio.gather(
            _relay_events(pubsub, ws),
            _handle_client_messages(ws),
        )
    except WebSocketDisconnect:
        log.info("WebSocket disconnected")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        _connections.discard(ws)
        await pubsub.punsubscribe("edict:pubsub:*")
        await pubsub_redis.aclose()
        log.info(f"WebSocket cleaned up. Remaining: {len(_connections)}")


async def _relay_events(pubsub, ws: WebSocket):
    """Receive events from Redis Pub/Sub and push to WebSocket."""
    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            channel = message["channel"]
            data = message["data"]

            # Extract topic name
            topic = channel.replace("edict:pubsub:", "") if channel.startswith("edict:pubsub:") else channel

            try:
                event_data = json.loads(data) if isinstance(data, str) else data
                await ws.send_json({
                    "type": "event",
                    "topic": topic,
                    "data": event_data,
                })
            except Exception as e:
                log.warning(f"Failed to relay event: {e}")
                break


async def _handle_client_messages(ws: WebSocket):
    """Handle messages sent by the client (heartbeat, subscription filtering, etc.)."""
    while True:
        try:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
            elif msg_type == "subscribe":
                # Frontend can request to subscribe to specific topics only (future extension)
                topics = data.get("topics", [])
                log.debug(f"Client subscribe request: {topics}")
                await ws.send_json({"type": "subscribed", "topics": topics})
            else:
                log.debug(f"Unknown client message: {msg_type}")

        except WebSocketDisconnect:
            raise
        except Exception:
            break


@router.websocket("/ws/task/{task_id}")
async def task_websocket(ws: WebSocket, task_id: str):
    """Single-task WebSocket — only pushes events related to a specific task."""
    await ws.accept()
    _connections.add(ws)

    settings = get_settings()
    pubsub_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = pubsub_redis.pubsub()
    await pubsub.psubscribe("edict:pubsub:*")

    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                data = message["data"]
                try:
                    event_data = json.loads(data) if isinstance(data, str) else data
                    payload = event_data.get("payload", {})
                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    # Only forward events related to this task
                    if payload.get("task_id") == task_id:
                        topic = message["channel"].replace("edict:pubsub:", "")
                        await ws.send_json({
                            "type": "event",
                            "topic": topic,
                            "data": event_data,
                        })
                except Exception:
                    continue
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(ws)
        await pubsub.punsubscribe("edict:pubsub:*")
        await pubsub_redis.aclose()


async def broadcast(event: dict):
    """Broadcast an event to all connected WebSocket clients (for internal server-side calls)."""
    dead = set()
    for ws in _connections:
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)
    _connections -= dead
