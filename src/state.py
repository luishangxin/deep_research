"""
ThreadState — extends LangGraph's AgentState with flow-specific fields.

create_react_agent requires state_schema to include `messages` and
`remaining_steps` (for recursion limit tracking). We get both by inheriting
from AgentState and adding our own extra fields.
"""
from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState


class ThreadState(AgentState):
    """
    The main state object threaded through the LangGraph StateGraph.

    Inherits from AgentState which provides:
        messages          — conversation history (append-only via add_messages)
        remaining_steps   — recursion limit counter (required by create_react_agent)

    Additional flow fields:
        thread_id         — unique identifier for this conversation thread

        sandbox_handle    — workdir path of the current LocalSandboxProvider session
        todo_list         — ordered list of task items for Plan Mode
        vision_cache      — dict[url -> base64_image] for reusing fetched images
        uploaded_files    — dict[filename -> tmp_path] for user-uploaded files

        memory_facts      — injected list of facts from memory.json
        pending_clarification — set when ask_clarification fires; blocks further calls

        _summary_context  — compressed summary from summarization middleware
    """
    # ---- Identity -----------------------------------------------------------
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

    # ---- Internal middleware scratch ----------------------------------------
    _summary_context: str | None
