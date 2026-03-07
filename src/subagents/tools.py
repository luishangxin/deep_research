"""
Subagent task tool — exposes task dispatch to the lead agent.

The lead agent uses `task_tool` to delegate sub-tasks to the SubagentPool.
It returns a JSON payload with the task_id so the main conversation can later
poll the pool for results.
"""
from __future__ import annotations

import json

from langchain_core.tools import tool

from src.subagents.pool import get_pool


@tool
def task_tool(description: str, subagent_type: str = "general-purpose") -> str:
    """
    Dispatch a background task to the subagent pool.

    Use this tool when you need to delegate a time-consuming sub-task to
    a background worker (e.g., deep web search, code execution, data analysis)
    so the main conversation can continue.

    Args:
        description: A clear, self-contained description of the task to execute.
        subagent_type: The type of subagent to use. Supported values:
                       "general-purpose" (default), "bash", "researcher".

    Returns:
        JSON string with {"task_id": "...", "status": "pending"}.
        Use the task_id to poll for the result later.
    """
    pool = get_pool()
    task_id = pool.submit(description=description, subagent_type=subagent_type)
    return json.dumps({"task_id": task_id, "status": "pending"})


@tool
def task_status_tool(task_id: str) -> str:
    """
    Poll the status of a previously dispatched background task.

    Args:
        task_id: The task ID returned by task_tool.

    Returns:
        JSON string with the task record (status, result, error, timestamps).
    """
    pool = get_pool()
    record = pool.get_task(task_id)
    if record is None:
        return json.dumps({"error": f"Task not found: {task_id}"})
    return json.dumps({
        "task_id": record.task_id,
        "status": record.status,
        "result": record.result,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    })
