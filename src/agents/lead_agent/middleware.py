"""
Middleware Chain — executed before every LLM invocation in the lead agent.

Each middleware function takes and returns a ThreadState. They are chained
sequentially in the `run_middleware_chain` function called by the graph node.

Order of execution (matches CLAUDE.md spec):
  1. summarization_middleware  — context compression / anti-overflow
  2. sandbox_lifecycle_middleware — lock sandbox handle for this turn
  3. memory_persist_middleware — async background memory Facts extraction
  4. clarification_interceptor — detect & short-circuit ask_clarification
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from src.state import ThreadState
from src.sandbox.local import LocalSandboxProvider

# --------------------------------------------------------------------------- #
# Config helpers
# --------------------------------------------------------------------------- #

def _get_config() -> dict:
    """Load config.yaml lazily."""
    try:
        import yaml
        config_path = Path(os.environ.get("DEER_FLOW_CONFIG_PATH", "config.yaml"))
        if config_path.exists():
            return yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        pass
    return {}


# --------------------------------------------------------------------------- #
# 1. Summarization / Anti-Overflow Middleware
# --------------------------------------------------------------------------- #

MAX_MESSAGES_BEFORE_SUMMARY = 20  # configurable via config.yaml

def summarization_middleware(state: ThreadState) -> ThreadState:
    """
    Detect when message history is getting long and inject a compressed
    summary in place of older messages, preventing token overflow.

    If the conversation has more than MAX_MESSAGES_BEFORE_SUMMARY messages,
    trim the oldest messages and prepend a [Summary] system message.
    """
    messages: list[BaseMessage] = state.get("messages", [])

    cfg = _get_config()
    summ_cfg = cfg.get("summarization", {})
    if not summ_cfg.get("enabled", True):
        return state

    keep_n = summ_cfg.get("keep", {}).get("value", 10)
    trigger_msgs = None
    for trigger in summ_cfg.get("trigger", []):
        if trigger.get("type") == "messages":
            trigger_msgs = trigger.get("value", MAX_MESSAGES_BEFORE_SUMMARY)
            break
    trigger_limit = trigger_msgs or MAX_MESSAGES_BEFORE_SUMMARY

    if len(messages) <= trigger_limit:
        return state

    # Split: old messages to summarize + recent messages to keep
    old_messages = messages[:-keep_n]
    recent_messages = messages[-keep_n:]

    # Build a simple extractive summary from old messages
    summary_lines = []
    for m in old_messages:
        role = getattr(m, "type", "unknown")
        content = m.content if isinstance(m.content, str) else str(m.content)
        summary_lines.append(f"[{role}]: {content[:200]}")

    summary_text = (
        f"[CONVERSATION SUMMARY — {len(old_messages)} earlier messages]\n"
        + "\n".join(summary_lines[:10])  # keep summary itself brief
    )
    summary_msg = SystemMessage(content=summary_text)
    return {**state, "messages": [summary_msg] + recent_messages}


# --------------------------------------------------------------------------- #
# 2. Sandbox Lifecycle Middleware
# --------------------------------------------------------------------------- #

def sandbox_lifecycle_middleware(state: ThreadState) -> ThreadState:
    """
    Ensure the sandbox for this session is initialized and the thread-local
    handle is set before any tool can touch the filesystem.

    Stores the sandbox workdir path in state["sandbox_handle"] for observability.
    """
    thread_id = state.get("thread_id") or str(threading.get_ident())

    # Create or retrieve the sandbox for this session
    sandbox = LocalSandboxProvider(thread_id=thread_id)
    LocalSandboxProvider.set_current(sandbox)

    return {**state, "sandbox_handle": sandbox.get_workdir()}


# --------------------------------------------------------------------------- #
# 3. Memory Persist Middleware
# --------------------------------------------------------------------------- #

MEMORY_PATH = Path(os.environ.get("MEMORY_PATH", "memory.json"))
_memory_lock = threading.Lock()


def _extract_and_persist_facts(messages: list[BaseMessage]) -> None:
    """
    Background coroutine: extract key facts from the last user/assistant
    exchange and append them to memory.json.

    This is a lightweight heuristic extractor. In production, hook in an
    actual LLM call here for proper fact extraction.
    """
    if not messages:
        return

    facts = []
    for m in messages[-4:]:  # look at recent context
        content = m.content if isinstance(m.content, str) else str(m.content)
        if len(content) > 20:
            # Very simple: pull key sentences containing factual signals
            for line in content.split(". "):
                if any(kw in line.lower() for kw in ["is", "are", "was", "has", "user", "name", "prefer"]):
                    facts.append(line.strip()[:200])
                    if len(facts) >= 3:
                        break

    if not facts:
        return

    with _memory_lock:
        try:
            memory: dict[str, Any] = {}
            if MEMORY_PATH.exists():
                memory = json.loads(MEMORY_PATH.read_text())
            existing: list = memory.get("facts", [])
            for f in facts:
                if f not in existing:
                    existing.append({"fact": f, "ts": datetime.utcnow().isoformat()})
            # Enforce max_facts
            cfg = _get_config()
            max_facts = cfg.get("memory", {}).get("max_facts", 100)
            memory["facts"] = existing[-max_facts:]
            MEMORY_PATH.write_text(json.dumps(memory, indent=2, ensure_ascii=False))
        except Exception:
            pass  # Never block the main flow due to memory errors


def memory_persist_middleware(state: ThreadState) -> ThreadState:
    """
    Trigger background fact extraction from recent conversation.

    The extraction runs in a daemon thread so it never blocks the main
    LLM call. Also injects previously stored facts into state.
    """
    messages: list[BaseMessage] = state.get("messages", [])

    cfg = _get_config()
    mem_cfg = cfg.get("memory", {})
    if not mem_cfg.get("enabled", True):
        return state

    # Fire-and-forget: background thread
    t = threading.Thread(
        target=_extract_and_persist_facts,
        args=(messages,),
        daemon=True,
    )
    t.start()

    # Inject existing facts into state for the LLM to use
    memory_facts: list[str] = []
    if MEMORY_PATH.exists():
        try:
            memory = json.loads(MEMORY_PATH.read_text())
            max_inject = mem_cfg.get("max_facts", 20)
            for entry in memory.get("facts", [])[-max_inject:]:
                if isinstance(entry, dict):
                    memory_facts.append(entry.get("fact", ""))
                else:
                    memory_facts.append(str(entry))
        except Exception:
            pass

    return {**state, "memory_facts": memory_facts}


# --------------------------------------------------------------------------- #
# 4. Clarification Interceptor
# --------------------------------------------------------------------------- #

ASK_CLARIFICATION_TOOL_NAME = "ask_clarification"


def clarification_interceptor(state: ThreadState) -> ThreadState:
    """
    Check if the last AIMessage contains an ask_clarification tool call.

    If it does, extract the question from the tool call, set
    state["pending_clarification"], and signal the graph to route to END.
    This halts further LLM processing until the user responds.
    """
    messages: list[BaseMessage] = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    for tc in tool_calls:
        name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
        if name == ASK_CLARIFICATION_TOOL_NAME:
            args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            question = args.get("question", "Could you please clarify?")
            return {**state, "pending_clarification": question}

    return state


# --------------------------------------------------------------------------- #
# Chain runner
# --------------------------------------------------------------------------- #

_MIDDLEWARE_CHAIN = [
    summarization_middleware,
    sandbox_lifecycle_middleware,
    memory_persist_middleware,
    clarification_interceptor,
]


def run_middleware_chain(state: ThreadState) -> ThreadState:
    """
    Execute all middleware functions sequentially.

    Each middleware receives the state produced by the previous one.
    This is called as the first node in the LangGraph StateGraph before
    any LLM invocation.
    """
    for mw in _MIDDLEWARE_CHAIN:
        state = mw(state)
    return state
