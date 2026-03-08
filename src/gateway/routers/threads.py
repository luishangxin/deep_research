"""
Threads Router — CRUD endpoints for conversation threads.

Threads represent individual conversation sessions. In the full flow
architecture, actual message streaming is handled by the LangGraph Server
directly (via Nginx proxy), so the Gateway only manages session metadata.

GET    /api/threads           — list all threads (metadata only)
POST   /api/threads           — create a new thread
GET    /api/threads/{id}      — get thread metadata + task list
DELETE /api/threads/{id}      — delete a thread and its sandbox
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/threads", tags=["threads"])


# --------------------------------------------------------------------------- #
# In-memory store (replace with persistent store in production)
# --------------------------------------------------------------------------- #

_threads: dict[str, dict[str, Any]] = {}


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class CreateThreadRequest(BaseModel):
    title: str = Field(default="New Thread", description="Human-readable thread title")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = {}
    task_count: int = 0


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("", response_model=list[ThreadResponse])
async def list_threads() -> list[ThreadResponse]:
    """List all conversation threads."""
    return [
        ThreadResponse(
            id=t["id"],
            title=t["title"],
            created_at=t["created_at"],
            updated_at=t["updated_at"],
            metadata=t.get("metadata", {}),
            task_count=len(t.get("tasks", [])),
        )
        for t in sorted(_threads.values(), key=lambda x: x["created_at"], reverse=True)
    ]


@router.post("", response_model=ThreadResponse, status_code=201)
async def create_thread(body: CreateThreadRequest) -> ThreadResponse:
    """Create a new conversation thread."""
    thread_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    _threads[thread_id] = {
        "id": thread_id,
        "title": body.title,
        "created_at": now,
        "updated_at": now,
        "metadata": body.metadata,
        "tasks": [],
    }
    return ThreadResponse(
        id=thread_id,
        title=body.title,
        created_at=now,
        updated_at=now,
        metadata=body.metadata,
        task_count=0,
    )


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str) -> ThreadResponse:
    """Get metadata for a specific thread."""
    thread = _threads.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
    return ThreadResponse(
        id=thread["id"],
        title=thread["title"],
        created_at=thread["created_at"],
        updated_at=thread["updated_at"],
        metadata=thread.get("metadata", {}),
        task_count=len(thread.get("tasks", [])),
    )


@router.delete("/{thread_id}", status_code=204)
async def delete_thread(thread_id: str) -> None:
    """Delete a thread and clean up its sandbox directory."""
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")

    # Clean up sandbox
    try:
        from src.sandbox.local import LocalSandboxProvider, SANDBOX_BASE
        import shutil
        sandbox_dir = SANDBOX_BASE / thread_id
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir, ignore_errors=True)
    except Exception:
        pass

    del _threads[thread_id]
