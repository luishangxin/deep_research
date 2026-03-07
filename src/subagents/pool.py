"""
SubagentPool — ThreadPoolExecutor-based pool for running background Agent tasks.

The lead agent uses the task_tool to submit sub-tasks to this pool. Each task
runs an isolated LangGraph subgraph. Progress is stored in a shared dict so the
main session can poll it (pull) or receive push notifications via SSE.
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal

TaskStatus = Literal["pending", "running", "done", "error"]

MAX_WORKERS = int(__import__("os").environ.get("SUBAGENT_POOL_SIZE", "4"))


@dataclass
class TaskRecord:
    task_id: str
    description: str
    subagent_type: str
    status: TaskStatus = "pending"
    result: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SubagentPool:
    """
    Manages a ThreadPoolExecutor for subagent task execution.

    Usage::

        pool = SubagentPool()
        task_id = pool.submit("Summarize document.pdf", "general-purpose")
        record = pool.get_task(task_id)
    """

    def __init__(self, max_workers: int = MAX_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="subagent")
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        # Optional push-notification callback: callback(task_id, record)
        self._callbacks: list[Callable[[str, TaskRecord], None]] = []

    def submit(
        self,
        description: str,
        subagent_type: str = "general-purpose",
        runner: Callable[[str, str], str] | None = None,
    ) -> str:
        """
        Submit a background task and return its task_id.

        Args:
            description: Natural language description of the task.
            subagent_type: Type of subagent to use (maps to config).
            runner: Optional override callable(description, subagent_type) -> result.
                    Defaults to _default_runner.

        Returns:
            task_id string (UUID4).
        """
        task_id = str(uuid.uuid4())
        record = TaskRecord(
            task_id=task_id,
            description=description,
            subagent_type=subagent_type,
        )
        with self._lock:
            self._tasks[task_id] = record

        fn = runner or self._default_runner
        future: Future = self._executor.submit(self._run_task, task_id, description, subagent_type, fn)
        return task_id

    def get_task(self, task_id: str) -> TaskRecord | None:
        """Return the current record for a task, or None if not found."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        """Return all task records."""
        with self._lock:
            return list(self._tasks.values())

    def register_callback(self, cb: Callable[[str, TaskRecord], None]) -> None:
        """Register a push-notification callback for task status changes."""
        self._callbacks.append(cb)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_task(
        self,
        task_id: str,
        description: str,
        subagent_type: str,
        runner: Callable[[str, str], str],
    ) -> None:
        self._update(task_id, status="running")
        try:
            result = runner(description, subagent_type)
            self._update(task_id, status="done", result=result)
        except Exception as exc:
            self._update(task_id, status="error", error=str(exc))

    def _update(self, task_id: str, **kwargs: Any) -> None:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            for k, v in kwargs.items():
                setattr(record, k, v)
            record.updated_at = datetime.utcnow().isoformat()
        # Notify push callbacks
        for cb in self._callbacks:
            try:
                cb(task_id, self._tasks[task_id])
            except Exception:
                pass

    @staticmethod
    def _default_runner(description: str, subagent_type: str) -> str:
        """
        Placeholder runner — replace with actual subgraph invocation.
        In production this would invoke a specialised LangGraph subgraph.
        """
        import time
        time.sleep(0.1)  # simulate work
        return f"[{subagent_type}] Completed: {description}"


# Global singleton pool
_pool: SubagentPool | None = None


def get_pool() -> SubagentPool:
    """Return the global SubagentPool, creating it lazily."""
    global _pool
    if _pool is None:
        _pool = SubagentPool()
    return _pool
