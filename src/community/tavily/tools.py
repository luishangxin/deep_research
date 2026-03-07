"""
Tavily web search tool for the lead agent.

Search scope is restricted to PubMed and Google Scholar to ensure
results come from peer-reviewed / academic sources.

Requires TAVILY_API_KEY environment variable to be set.
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


# Restrict search to academic / peer-reviewed sources only
_INCLUDE_DOMAINS = [
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "scholar.google.com",
]


@tool
def web_search_tool(query: str, max_results: int = 10) -> str:
    """
    Search PubMed and Google Scholar using Tavily and return structured results.

    Search scope is restricted to:
    - pubmed.ncbi.nlm.nih.gov
    - pmc.ncbi.nlm.nih.gov  (PubMed Central full-text)
    - scholar.google.com

    Args:
        query: The search query string. Use academic terms; MeSH terms work well
               for medical topics (e.g., "BRAF V600E mutation melanoma treatment").
        max_results: Maximum number of results to return (default: 10, max: 20).

    Returns:
        JSON string with query, an AI-generated answer summary, and a list of
        results (title, url, content snippet, relevance score).
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set"})
    if not _TAVILY_AVAILABLE:
        return json.dumps({"error": "tavily-python package not installed"})

    max_results = min(max(1, max_results), 20)
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
            include_domains=_INCLUDE_DOMAINS,
        )
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
            }
            for r in response.get("results", [])
        ]
        return json.dumps({
            "query": query,
            "search_domains": _INCLUDE_DOMAINS,
            "answer": response.get("answer", ""),
            "results": results,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
