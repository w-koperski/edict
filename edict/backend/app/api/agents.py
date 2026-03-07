"""Agents API — Agent configuration and status queries."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("edict.api.agents")
router = APIRouter()

# Agent metadata (corresponds to SOUL.md in agents/ directory)
AGENT_META = {
    "zaochao": {"name": "Zaochao (Court Convener)", "role": "Court assembly and agenda management", "icon": "🏛️"},
    "shangshu": {"name": "Grand Secretary", "role": "Overall coordination and task oversight", "icon": "📜"},
    "zhongshu": {"name": "Zhongshu", "role": "Drafting edicts and planning", "icon": "✍️"},
    "menxia": {"name": "Menxia", "role": "Review and veto", "icon": "🔍"},
    "libu": {"name": "Libu_hr (Personnel Ministry)", "role": "Personnel and organizational management", "icon": "👤"},
    "hubu": {"name": "Hubu (Finance Ministry)", "role": "Finance and resource management", "icon": "💰"},
    "gongbu": {"name": "Gongbu (Engineering Ministry)", "role": "Engineering and technical implementation", "icon": "🔧"},
    "xingbu": {"name": "Xingbu (Justice Ministry)", "role": "Compliance and quality review", "icon": "⚖️"},
    "bingbu": {"name": "Bingbu (Military Ministry)", "role": "Security and emergency response", "icon": "🛡️"},
}


@router.get("")
async def list_agents():
    """List all available Agents."""
    agents = []
    for agent_id, meta in AGENT_META.items():
        agents.append({
            "id": agent_id,
            **meta,
        })
    return {"agents": agents}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Get Agent details."""
    meta = AGENT_META.get(agent_id)
    if not meta:
        return {"error": f"Agent '{agent_id}' not found"}, 404

    # Try to read SOUL.md
    soul_path = Path(__file__).parents[4] / "agents" / agent_id / "SOUL.md"
    soul_content = ""
    if soul_path.exists():
        soul_content = soul_path.read_text(encoding="utf-8")[:2000]

    return {
        "id": agent_id,
        **meta,
        "soul_preview": soul_content,
    }


@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """Get Agent runtime configuration."""
    config_path = Path(__file__).parents[4] / "data" / "agent_config.json"
    if not config_path.exists():
        return {"agent_id": agent_id, "config": {}}

    try:
        configs = json.loads(config_path.read_text(encoding="utf-8"))
        agent_config = configs.get(agent_id, {})
        return {"agent_id": agent_id, "config": agent_config}
    except (json.JSONDecodeError, IOError):
        return {"agent_id": agent_id, "config": {}}
