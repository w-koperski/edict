"""Edict Backend — FastAPI application entry point.

Lifespan management:
- startup: connect to Redis Event Bus, initialize database
- shutdown: close connections

Routes:
- /api/tasks — task CRUD
- /api/agents — Agent info
- /api/events — event queries
- /api/admin — admin operations
- /ws — WebSocket real-time push
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .services.event_bus import get_event_bus
from .api import tasks, agents, events, admin, websocket
from .api import legacy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("edict")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    settings = get_settings()
    log.info(f"🏛️ Edict Backend starting on port {settings.port}...")

    # Connect to Event Bus
    bus = await get_event_bus()
    log.info("✅ Event Bus connected")

    yield

    # Cleanup
    await bus.close()
    log.info("Edict Backend shutdown complete")


app = FastAPI(
    title="Edict Three Departments & Six Ministries",
    description="Event-driven AI Agent collaboration platform",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(legacy.router, prefix="/api/tasks", tags=["legacy"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "engine": "edict"}


@app.get("/api")
async def api_root():
    return {
        "name": "Edict Three Departments & Six Ministries API",
        "version": "2.0.0",
        "endpoints": {
            "tasks": "/api/tasks",
            "agents": "/api/agents",
            "events": "/api/events",
            "admin": "/api/admin",
            "websocket": "/ws",
            "health": "/health",
        },
    }
