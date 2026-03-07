"""
Jina AI web fetch tool for the lead agent.

Uses the Jina Reader API (r.jina.ai) to fetch and parse web pages into
clean markdown/text suitable for LLM consumption.

No API key is required for basic usage at r.jina.ai.
"""
from __future__ import annotations

import json
import os

from langchain_core.tools import tool

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


JINA_READER_BASE = "https://r.jina.ai/"
JINA_API_KEY = os.environ.get("JINA_API_KEY", "")


@tool
def web_fetch_tool(url: str, timeout: int = 10) -> str:
    """
    Fetch the content of a webpage using Jina AI Reader and return it as text.

    Jina Reader strips ads, navigation, and boilerplate — returning clean
    article/document text that LLMs can process efficiently.

    Args:
        url: The URL to fetch.
        timeout: HTTP timeout in seconds (default: 10).

    Returns:
        Page content as plain text, or a JSON error payload.
    """
    if not _HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx package not installed"})

    reader_url = f"{JINA_READER_BASE}{url}"
    headers = {
        "Accept": "text/plain",
        "X-Return-Format": "text",
    }
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(reader_url, headers=headers)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException:
        return json.dumps({"error": f"Timeout fetching {url}"})
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}: {url}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})
