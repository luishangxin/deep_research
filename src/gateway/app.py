"""
FastAPI Gateway Application — main entry point.

Run with: python -m src.gateway.app
Or:        uvicorn src.gateway.app:app --port 8000

This gateway provides pure RESTful endpoints for configuration and thread
management. The actual LangGraph Agent streaming is kept separate (served
by `langgraph dev` on port 2024) — the Gateway does NOT handle complex
LangGraph SSE, leaving that to Nginx to proxy directly to the Agent.

Architecture alignment with CLAUDE.md §3:
  - FastAPI (`python -m src.gateway.app`) on :8000
  - LangGraph Server (`langgraph dev`) on :2024
  - Nginx forwards /runs/** and /stream/** directly to :2024
  - Gateway handles /api/** routes only
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.gateway.routers.config import router as config_router
from src.gateway.routers.threads import router as threads_router

# --------------------------------------------------------------------------- #
# Application factory
# --------------------------------------------------------------------------- #

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DeerFlow Gateway API",
        description=(
            "RESTful gateway for DeerFlow Agent Backend. "
            "Provides configuration read-access and thread/session management. "
            "LangGraph Agent streaming is served separately on port 2024."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow all origins in dev; tighten in production
    allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(config_router)
    app.include_router(threads_router)

    # Health check
    @app.get("/health", tags=["system"])
    async def health_check() -> dict:
        return {"status": "ok", "service": "deerflow-gateway"}

    # Info
    @app.get("/", tags=["system"])
    async def root() -> dict:
        return {
            "name": "DeerFlow Gateway",
            "version": "0.1.0",
            "docs": "/docs",
            "agent_server": "http://localhost:2024",
        }

    return app


app = create_app()


# --------------------------------------------------------------------------- #
# Entry point for `python -m src.gateway.app`
# --------------------------------------------------------------------------- #

def main() -> None:
    """Run the gateway with uvicorn."""
    import uvicorn

    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", "8000"))
    reload = os.environ.get("GATEWAY_RELOAD", "false").lower() == "true"

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "src.gateway.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
