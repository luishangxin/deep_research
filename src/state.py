"""
ThreadState — extends LangGraph's AgentState with DeerFlow-specific fields.
"""
from __future__ import annotations

from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ThreadState(TypedDict, total=False):
    """
    The main state object threaded through the LangGraph StateGraph.

    Core fields:
        messages          — conversation history (append-only via add_messages)
        thread_id         — unique identifier for this conversation thread

    Sandbox fields:
        sandbox_handle    — opaque ID of the current LocalSandboxProvider session

    Plan fields:
        todo_list         — ordered list of task items for Plan Mode

    Vision fields:
        vision_cache      — dict[url -> base64_image] for reusing fetched images

    File upload fields:
        uploaded_files    — dict[filename -> tmp_path] for user-uploaded files

    Memory fields:
        memory_facts      — injected list of facts from memory.json
        pending_clarification — set when ask_clarification tool fires; blocks
                               further LLM calls until user responds

    Middleware scratch fields:
        _summary_context  — compressed summary injected by summarization middleware
    """

    # ---- Core ---------------------------------------------------------------
    messages: Annotated[list, add_messages]
    thread_id: str

    # ---- Sandbox ------------------------------------------------------------
    sandbox_handle: str | None

    # ---- Plan Mode ----------------------------------------------------------
    todo_list: list[str]

    # ---- Vision Cache -------------------------------------------------------
    vision_cache: dict[str, str]

    # ---- File Uploads -------------------------------------------------------
    uploaded_files: dict[str, str]

    # ---- Memory -------------------------------------------------------------
    memory_facts: list[str]
    pending_clarification: str | None

    # ---- Internal middleware scratch -----------------------------------------
    _summary_context: str | None
