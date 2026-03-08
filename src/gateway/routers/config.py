"""
Config Router — read-only endpoints for runtime configuration.

GET /api/config    — full config.yaml content
GET /api/models    — list of configured LLM models
GET /api/tools     — list of configured tools with groups
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["config"])


def _load_config() -> dict:
    """Load and return the parsed config.yaml."""
    try:
        import yaml
        path = Path(os.environ.get("FLOW_CONFIG_PATH", "config.yaml"))
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
    except ImportError:
        raise HTTPException(status_code=500, detail="PyYAML not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config error: {e}")
    return {}


class ModelInfo(BaseModel):
    name: str
    display_name: str
    supports_thinking: bool = False
    supports_vision: bool = False


class ToolInfo(BaseModel):
    name: str
    group: str | None = None
    use: str


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Return the full parsed configuration."""
    return _load_config()


@router.get("/models", response_model=list[ModelInfo])
async def get_models() -> list[ModelInfo]:
    """Return the list of available LLM models."""
    cfg = _load_config()
    models = cfg.get("models", [])
    return [
        ModelInfo(
            name=m.get("name", ""),
            display_name=m.get("display_name", m.get("name", "")),
            supports_thinking=m.get("supports_thinking", False),
            supports_vision=m.get("supports_vision", False),
        )
        for m in models
    ]


@router.get("/tools", response_model=list[ToolInfo])
async def get_tools() -> list[ToolInfo]:
    """Return the list of configured tools."""
    cfg = _load_config()
    tools = cfg.get("tools", [])
    return [
        ToolInfo(
            name=t.get("name", ""),
            group=t.get("group"),
            use=t.get("use", ""),
        )
        for t in tools
    ]
