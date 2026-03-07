"""
Lead Agent Nodes — LangGraph node functions for the main StateGraph.

Nodes:
  - run_middleware: executes the middleware chain before LLM invocation
  - call_model: invokes the LLM with bound tools
  - run_tools: executes tool calls from the last AI message

Edges:
  - should_continue: decides whether to loop (tool call) or end
  - should_await_clarification: routes to END if interceptor set pending_clarification
"""
from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.state import ThreadState
from src.agents.lead_agent.middleware import run_middleware_chain


# --------------------------------------------------------------------------- #
# System Prompt Construction
# --------------------------------------------------------------------------- #

def _build_system_prompt(state: ThreadState) -> str:
    """Build the system prompt, injecting memory facts and sandbox info."""
    base_prompt = (
        "You are a powerful AI assistant with access to a local sandbox environment, "
        "web search, file operations, and background subagent workers.\n\n"
        "You can use tools to accomplish tasks. When you need clarification, use the "
        "ask_clarification tool to pause and ask the user.\n\n"
        "When delegating long-running tasks, use the task_tool to submit them to the "
        "background subagent pool and task_status_tool to poll for results.\n"
    )

    memory_facts: list[str] = state.get("memory_facts", [])
    if memory_facts:
        facts_str = "\n".join(f"- {f}" for f in memory_facts[:20] if f)
        base_prompt += f"\n## Known Facts About User\n{facts_str}\n"

    sandbox_handle = state.get("sandbox_handle")
    if sandbox_handle:
        base_prompt += f"\n## Sandbox Workdir\n{sandbox_handle}\n"

    todo_list: list[str] = state.get("todo_list", [])
    if todo_list:
        items = "\n".join(f"  [ ] {t}" for t in todo_list)
        base_prompt += f"\n## Current TODOs\n{items}\n"

    return base_prompt


# --------------------------------------------------------------------------- #
# Node: run_middleware
# --------------------------------------------------------------------------- #

def run_middleware(state: ThreadState) -> ThreadState:
    """
    Graph node: run the full middleware chain before calling the LLM.

    Returns the updated state (may include sandbox_handle, memory_facts,
    pending_clarification, and potentially trimmed messages).
    """
    return run_middleware_chain(state)


# --------------------------------------------------------------------------- #
# Node: call_model
# --------------------------------------------------------------------------- #

def call_model(state: ThreadState, config: RunnableConfig) -> ThreadState:
    """
    Graph node: invoke the LLM with the current conversation state.

    Prepends the system prompt (built dynamically from state), then calls
    the model. Tools are bound at graph-build time via the model reference
    stored in config["configurable"]["model"].
    """
    from src.agents.lead_agent.graph import _get_model  # avoid circular at module level

    model = _get_model(config)

    # Build messages with injected system prompt
    messages: list[BaseMessage] = state.get("messages", [])
    system_content = _build_system_prompt(state)
    system_msg = SystemMessage(content=system_content)

    # Prepend system message (replace existing system msgs to avoid duplicates)
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    full_messages = [system_msg] + filtered

    response: AIMessage = model.invoke(full_messages, config)
    return {"messages": [response]}


# --------------------------------------------------------------------------- #
# Node: run_tools
# --------------------------------------------------------------------------- #

def run_tools(state: ThreadState, config: RunnableConfig) -> ThreadState:
    """
    Graph node: execute all tool calls from the last AIMessage.

    Uses the ToolNode approach: gets the tool map from config, executes
    each tool call, and appends ToolMessage results.
    """
    from langchain_core.messages import ToolMessage
    from src.agents.lead_agent.graph import _get_tool_map  # avoid circular

    messages: list[BaseMessage] = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    if last_msg is None or not isinstance(last_msg, AIMessage):
        return {"messages": []}

    tool_calls = getattr(last_msg, "tool_calls", []) or []
    tool_map = _get_tool_map(config)

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


# --------------------------------------------------------------------------- #
# Conditional Edges
# --------------------------------------------------------------------------- #

def should_await_clarification(state: ThreadState) -> str:
    """
    Conditional edge after middleware: if clarification is pending, go to END.
    Otherwise proceed to call_model.
    """
    if state.get("pending_clarification"):
        return "end"
    return "call_model"


def should_continue(state: ThreadState) -> str:
    """
    Conditional edge after call_model: if the last message has tool calls,
    run them; otherwise end the turn.
    """
    messages: list[BaseMessage] = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", []):
        return "run_tools"
    return "end"
