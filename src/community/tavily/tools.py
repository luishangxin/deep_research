"""
Tavily web search tool for the lead agent.

Requires TAVILY_API_KEY environment variable to be set.
Falls back to a stub error if the key is missing.
"""
from __future__ import annotations

import json
import os

from langchain_core.tools import tool

try:
    from tavily import TavilyClient
    _TAVILY_AVAILABLE = True
except ImportError:
    _TAVILY_AVAILABLE = False
    TavilyClient = None  # type: ignore


@tool
def web_search_tool(query: str, max_results: int = 5) -> str:
    """
    Search the web using Tavily and return structured results.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default: 5).

    Returns:
        JSON string of search results, each with title, url, and content.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set"})
    if not _TAVILY_AVAILABLE:
        return json.dumps({"error": "tavily-python package not installed"})

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
            })
        return json.dumps({
            "query": query,
            "answer": response.get("answer", ""),
            "results": results,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
