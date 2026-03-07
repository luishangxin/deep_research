"""
Lead Agent Graph — builds the main LangGraph StateGraph.

Architecture:
    START
      │
      ▼
  [run_middleware]  ◄─── middleware chain (summarize, sandbox, memory, clarify)
      │
      ├─ pending_clarification? ──► END (await user response)
      │
      ▼
  [call_model]  ◄─────────────────────────────────────────┐
      │                                                    │
      ├─ has tool_calls? ──► [run_tools] ──────────────────┘
      │
      └─ no tool_calls? ──► END

Config system:
  - `_get_model(config)` uses the reflection factory to load the LLM.
  - `_get_tool_map(config)` builds a name→tool dict from config.yaml.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph as CompiledGraph

from src.state import ThreadState
from src.agents.lead_agent.nodes import (
    call_model,
    run_middleware,
    run_tools,
    should_await_clarification,
    should_continue,
)


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #

def _load_config() -> dict:
    """Load config.yaml once."""
    try:
        import yaml
        path = Path(os.environ.get("DEER_FLOW_CONFIG_PATH", "config.yaml"))
        return yaml.safe_load(path.read_text()) or {} if path.exists() else {}
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# Model + Tool resolution via Reflection Factory
# --------------------------------------------------------------------------- #

def _get_model(config: RunnableConfig | None = None) -> Any:
    """
    Resolve and instantiate the LLM from config.yaml using the reflection factory.

    Falls back to a lightweight ChatOpenAI default if config is missing.
    """
    from src.factory import build_from_config

    cfg = _load_config()
    models: list[dict] = cfg.get("models", [])

    # Honour model_name override from LangGraph configurable
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
            # Log but don't crash — fall through to default
            print(f"[graph] Warning: failed to build model from config: {e}")

    # Default fallback: DeepSeek via OpenAI-compatible endpoint
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("[graph] Warning: DEEPSEEK_API_KEY not set in .env — LLM calls will fail.")
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
        from langchain_core.messages import AIMessage
        return RunnableLambda(
            lambda x: AIMessage(content="[System Error] LLM not available. Please set DEEPSEEK_API_KEY in the .env file.")
        )


def _get_tool_list() -> list[BaseTool]:
    """Build the list of tools from config.yaml using the reflection factory."""
    from src.factory import resolve_class
    from src.sandbox.tools import SANDBOX_TOOLS
    from src.community.tavily.tools import web_search_tool
    from src.community.jina_ai.tools import web_fetch_tool
    from src.subagents.tools import task_tool, task_status_tool
    from src.mcp.client import get_mcp_tools

    cfg = _load_config()
    tool_configs: list[dict] = cfg.get("tools", [])

    tools: list[BaseTool] = []
    for tc in tool_configs:
        try:
            use_str = tc.get("use", "")
            tool_obj = resolve_class(use_str)
            tools.append(tool_obj)
        except Exception as e:
            print(f"[graph] Warning: could not load tool '{tc.get('name')}': {e}")

    # Always add subagent dispatch tools
    if task_tool not in tools:
        tools.append(task_tool)
    if task_status_tool not in tools:
        tools.append(task_status_tool)

    # Add MCP tools (may be empty if no servers enabled)
    tools.extend(get_mcp_tools())

    # Deduplicate by name
    seen: set[str] = set()
    unique_tools: list[BaseTool] = []
    for t in tools:
        if t.name not in seen:
            seen.add(t.name)
            unique_tools.append(t)

    return unique_tools


def _get_tool_map(config: RunnableConfig | None = None) -> dict[str, BaseTool]:
    """Return {tool_name: tool} mapping for run_tools node."""
    tools = _get_tool_list()
    return {t.name: t for t in tools}


# --------------------------------------------------------------------------- #
# ask_clarification special tool
# --------------------------------------------------------------------------- #

from langchain_core.tools import tool as _tool


@_tool
def ask_clarification(question: str) -> str:
    """
    Ask the user a clarifying question and pause the conversation.

    Use this when the user's request is ambiguous or you need more information
    before proceeding. This will immediately halt processing and surface the
    question to the user.

    Args:
        question: The clarifying question to present to the user.

    Returns:
        The question (signal to the clarification interceptor).
    """
    return question


# --------------------------------------------------------------------------- #
# Graph Builder
# --------------------------------------------------------------------------- #

def build_graph() -> CompiledGraph:
    """
    Build and compile the lead agent StateGraph.

    Returns:
        A compiled LangGraph graph ready to stream/invoke.
    """
    # Resolve tools and bind to model
    tools = _get_tool_list()
    tools.append(ask_clarification)
    tool_map = {t.name: t for t in tools}

    model_with_tools = _get_model().bind_tools(tools)

    # Wrap call_model to use the pre-built model with tools
    def _call_model_node(state: ThreadState, config: RunnableConfig) -> ThreadState:
        from langchain_core.messages import AIMessage, SystemMessage
        from src.agents.lead_agent.nodes import _build_system_prompt
        messages = state.get("messages", [])
        system_content = _build_system_prompt(state)
        system_msg = SystemMessage(content=system_content)
        filtered = [m for m in messages if not isinstance(m, SystemMessage)]
        response: AIMessage = model_with_tools.invoke([system_msg] + filtered, config)
        return {"messages": [response]}

    def _run_tools_node(state: ThreadState, config: RunnableConfig) -> ThreadState:
        from langchain_core.messages import AIMessage, ToolMessage
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None
        if last_msg is None or not isinstance(last_msg, AIMessage):
            return {"messages": []}

        tool_calls = getattr(last_msg, "tool_calls", []) or []
        tool_messages: list[ToolMessage] = []
        for tc in tool_calls:
            name = tc["name"] if isinstance(tc, dict) else tc.name
            args = tc["args"] if isinstance(tc, dict) else tc.args
            call_id = tc["id"] if isinstance(tc, dict) else tc.id
            if name in tool_map:
                try:
                    result = tool_map[name].invoke(args, config)
                except Exception as exc:
                    result = f"[tool error] {exc}"
            else:
                result = f"[error] Unknown tool: {name}"
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=call_id, name=name)
            )
        return {"messages": tool_messages}

    # Build the graph
    graph = StateGraph(ThreadState)

    # Nodes
    graph.add_node("run_middleware", run_middleware)
    graph.add_node("call_model", _call_model_node)
    graph.add_node("run_tools", _run_tools_node)

    # Entry point
    graph.add_edge(START, "run_middleware")

    # After middleware: check for pending clarification
    graph.add_conditional_edges(
        "run_middleware",
        should_await_clarification,
        {"call_model": "call_model", "end": END},
    )

    # After LLM call: check for tool calls
    graph.add_conditional_edges(
        "call_model",
        should_continue,
        {"run_tools": "run_tools", "end": END},
    )

    # After tools: loop back to middleware for next turn
    graph.add_edge("run_tools", "run_middleware")

    return graph.compile()
