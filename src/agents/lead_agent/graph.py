"""
Lead Agent Graph — built with langgraph.prebuilt.create_react_agent.

API (langgraph >= 0.3 / v2):
    create_react_agent(
        model,
        tools,
        state_schema   = ThreadState,  # our extended state
        prompt         = _build_prompt,  # dynamic system message callable
        pre_model_hook = _middleware_hook,  # runs before every LLM call
    )

The built-in ReAct loop handles the full agent ↔ tool cycle.

Middleware is split across two hooks:
  pre_model_hook  → run_middleware_chain (summarise, sandbox, memory, clarification)
  prompt          → build dynamic SystemMessage from updated state

Config system (Reflection Factory):
  - Models resolved from config.yaml via `src.factory.build_from_config`
  - Tools  resolved from config.yaml via `src.factory.resolve_class`
  - Fallback model: DeepSeek via OpenAI-compatible endpoint
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from src.state import ThreadState
from src.agents.lead_agent.middleware import run_middleware_chain


# ─────────────────────────────────────────────────────────────────────────────
# Config helper
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        import yaml
        path = Path(os.environ.get("FLOW_CONFIG_PATH", "config.yaml"))
        return yaml.safe_load(path.read_text()) or {} if path.exists() else {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Model resolution (Reflection Factory → DeepSeek fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _get_model(config=None) -> Any:
    """Resolve the LLM from config.yaml; fall back to DeepSeek endpoint."""
    from src.factory import build_from_config

    cfg = _load_config()
    models: list[dict] = cfg.get("models", [])

    model_name_override = (
        (config or {}).get("configurable", {}).get("model_name") if config else None
    )

    model_cfg: dict | None = None
    for m in models:
        if model_name_override and m.get("name") == model_name_override:
            model_cfg = m
            break
    if model_cfg is None and models:
        model_cfg = models[0]

    if model_cfg:
        try:
            return build_from_config(model_cfg)
        except Exception as e:
            print(f"[graph] Warning: failed to build model from config: {e}")

    # Fallback: DeepSeek via OpenAI-compatible endpoint
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("[graph] Warning: DEEPSEEK_API_KEY not set — LLM calls will fail.")
    from langchain_openai import ChatOpenAI
    try:
        return ChatOpenAI(
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key=api_key or "sk-placeholder",
            temperature=0,
        )
    except Exception as e:
        print(f"[graph] Warning: failed to initialize DeepSeek model: {e}")
        from langchain_core.runnables import RunnableLambda
        return RunnableLambda(
            lambda x: AIMessage(
                content="[System Error] LLM unavailable. Set DEEPSEEK_API_KEY in .env."
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tool resolution (Reflection Factory + always-on tools)
# ─────────────────────────────────────────────────────────────────────────────

def _get_tool_list() -> list[BaseTool]:
    """Resolve all tools from config.yaml; always include subagent + clarification."""
    from src.factory import resolve_class
    from src.subagents.tools import task_tool, task_status_tool
    from src.mcp.client import get_mcp_tools

    cfg = _load_config()
    tools: list[BaseTool] = []

    for tc in cfg.get("tools", []):
        try:
            tools.append(resolve_class(tc["use"]))
        except Exception as e:
            print(f"[graph] Warning: could not load tool '{tc.get('name')}': {e}")

    always_on = [task_tool, task_status_tool, ask_clarification]
    for t in always_on:
        if t not in tools:
            tools.append(t)

    tools.extend(get_mcp_tools())

    # Deduplicate by name
    seen: set[str] = set()
    return [t for t in tools if not (t.name in seen or seen.add(t.name))]


# ─────────────────────────────────────────────────────────────────────────────
# ask_clarification tool
# ─────────────────────────────────────────────────────────────────────────────

from langchain_core.tools import tool  # noqa: E402


@tool
def ask_clarification(question: str) -> str:
    """
    Ask the user a clarifying question and pause the conversation.

    Use this when the request is ambiguous or you need more information before
    proceeding. Calling this halts further processing until the user responds.

    Args:
        question: The clarifying question to present to the user.
    """
    return question


# ─────────────────────────────────────────────────────────────────────────────
# pre_model_hook — middleware chain (runs before every LLM call)
# ─────────────────────────────────────────────────────────────────────────────

def _middleware_hook(state: ThreadState) -> dict:
    """
    pre_model_hook: run the full middleware chain before every LLM invocation.

    Runs: summarise → sandbox lifecycle → memory persist → clarification intercept.

    Returns a state patch dict that LangGraph merges into the current state.
    """
    updated = run_middleware_chain(state)
    # Return only the fields that changed (as a delta dict)
    patch = {}
    for key in ("messages", "sandbox_handle", "memory_facts", "pending_clarification", "_summary_context"):
        new_val = updated.get(key)
        if new_val is not None:
            patch[key] = new_val
    return patch


# ─────────────────────────────────────────────────────────────────────────────
# prompt — dynamic system message (called before every LLM invocation)
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(state: ThreadState) -> list[BaseMessage]:
    """
    prompt callable: build a dynamic SystemMessage from the current state
    and return the final message list to send to the LLM.

    Receives the state AFTER pre_model_hook has run.
    """
    memory_facts: list[str] = state.get("memory_facts", [])
    sandbox_handle: str | None = state.get("sandbox_handle")
    todo_list: list[str] = state.get("todo_list", [])

    lines = [
        "You are a powerful AI assistant with access to a local sandbox environment, "
        "web search, file operations, and background subagent workers.",
        "",
        "## Guidelines",
        "- Use tools to accomplish tasks step by step.",
        "- When a request is ambiguous, call ask_clarification to pause and ask the user.",
        "- For long-running sub-tasks, use task_tool to dispatch them to the background pool.",
        "- Use task_status_tool to poll dispatched tasks for results.",
        "",
        "## Citation Requirements (MANDATORY)",
        "For every factual claim in a summary or report:",
        "1. Add a numbered inline Markdown link: `[n](url)` — must be clickable.",
        "2. End response with a **## References** section listing all sources.",
        "3. Always cite the source URL from web_search_tool / web_fetch_tool / PubMed results.",
        "",
        "## PubMed Usage (MANDATORY for medical / life science topics)",
        "When the query is related to medicine, biology, pharmacology, clinical research,",
        "bioinformatics, or any life-science domain, you MUST call BOTH tools in parallel:",
        "1. pubmed_search_tool — directly queries NCBI database for peer-reviewed abstracts.",
        "2. web_search_tool — searches PubMed and Google Scholar web pages for supplementary results.",
        "Do NOT skip web_search_tool even when pubmed_search_tool returns results.",
        "Calling only one of the two tools for medical topics is considered an incomplete response.",
        "After retrieving results from both tools, synthesise them and cite every source.",
    ]
    # if memory_facts:
    #     lines.append("\n## Known Facts About User")
    #     lines.extend(f"- {f}" for f in memory_facts[:20] if f)
    if sandbox_handle:
        lines.append(f"\n## Sandbox Workdir\n{sandbox_handle}")
    if todo_list:
        items = "\n".join(f"  [ ] {t}" for t in todo_list)
        lines.append(f"\n## Current TODOs\n{items}")

    system_msg = SystemMessage(content="\n".join(lines))
    messages: list[BaseMessage] = state.get("messages", [])
    # Strip any stale system messages, prepend fresh one
    non_system = [m for m in messages if not isinstance(m, SystemMessage)]
    return [system_msg] + non_system


# ─────────────────────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> CompiledStateGraph:
    """
    Build the lead agent graph using create_react_agent.

    create_react_agent provides a complete ReAct loop out-of-the-box:
        START → agent (LLM) → tools → agent → … → END

    The middleware chain runs as pre_model_hook before every LLM call.
    The system prompt is built dynamically via the prompt callable.

    Returns:
        A compiled LangGraph CompiledStateGraph, ready to stream/invoke.
    """
    return create_react_agent(
        model=_get_model(),
        tools=_get_tool_list(),
        state_schema=ThreadState,
        prompt=_build_prompt,
        pre_model_hook=_middleware_hook,
    )
