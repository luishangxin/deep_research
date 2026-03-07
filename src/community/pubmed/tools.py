"""
PubMed tools — search and fetch article metadata via NCBI E-utilities.

Two tools are provided:

pubmed_search_tool(query, max_results)
    → Search PubMed by keyword/query, returns list of PMIDs + titles + abstracts.

pubmed_fetch_tool(pmids)
    → Fetch full title + abstract for one or more specific PMIDs.

Uses NCBI E-utilities (free, no API key required for ≤3 req/s).
Set NCBI_API_KEY in .env to raise the limit to 10 req/s.

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from typing import Any

from langchain_core.tools import tool

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


# ─── NCBI base URLs ─────────────────────────────────────────────────────────

_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_ESEARCH_URL = f"{_EUTILS_BASE}/esearch.fcgi"
_EFETCH_URL  = f"{_EUTILS_BASE}/efetch.fcgi"
_ESUMMARY_URL = f"{_EUTILS_BASE}/esummary.fcgi"

_NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
_RATE_LIMIT_SLEEP = 0.34 if _NCBI_API_KEY else 0.34  # stay under 3 req/s without key


def _ncbi_params(**kwargs: Any) -> dict:
    """Build common NCBI params dict, injecting API key if available."""
    params = {"db": "pubmed", "retmode": "json", **kwargs}
    if _NCBI_API_KEY:
        params["api_key"] = _NCBI_API_KEY
    return params


def _get(url: str, params: dict, timeout: int = 15) -> dict | str:
    """GET request with rate limiting; returns parsed JSON or raw text."""
    time.sleep(_RATE_LIMIT_SLEEP)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            return r.json()
        return r.text


def _parse_efetch_xml(xml_text: str) -> list[dict]:
    """Parse PubMed efetch XML (retmode=xml) into a list of article dicts."""
    root = ET.fromstring(xml_text)
    articles = []
    for article_node in root.iter("PubmedArticle"):
        pmid_node = article_node.find(".//PMID")
        pmid = pmid_node.text if pmid_node is not None else ""

        # Title
        title_node = article_node.find(".//ArticleTitle")
        title = "".join(title_node.itertext()) if title_node is not None else ""

        # Abstract (may have multiple AbstractText sections)
        abstract_parts = []
        for at in article_node.findall(".//AbstractText"):
            label = at.get("Label")
            text = "".join(at.itertext())
            if label:
                abstract_parts.append(f"**{label}**: {text}")
            else:
                abstract_parts.append(text)
        abstract = "\n".join(abstract_parts)

        # Journal + year
        journal_node = article_node.find(".//Journal/Title")
        journal = journal_node.text if journal_node is not None else ""
        year_node = article_node.find(".//PubDate/Year")
        year = year_node.text if year_node is not None else ""

        # Authors (last name + initials)
        authors = []
        for auth in article_node.findall(".//Author")[:5]:  # max 5
            ln = auth.find("LastName")
            ini = auth.find("Initials")
            if ln is not None:
                authors.append(f"{ln.text} {ini.text if ini is not None else ''}".strip())
        if len(article_node.findall(".//Author")) > 5:
            authors.append("et al.")

        articles.append({
            "pmid": pmid,
            "title": title.strip(),
            "abstract": abstract.strip(),
            "journal": journal,
            "year": year,
            "authors": authors,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return articles


# ─── Tools ──────────────────────────────────────────────────────────────────

@tool
def pubmed_search_tool(query: str, max_results: int = 10) -> str:
    """
    Search PubMed and return article titles, abstracts, and links.

    Searches the PubMed database using NCBI E-utilities.  Results include:
    - PMID (PubMed ID)
    - Title
    - Abstract
    - Journal name and publication year
    - Authors (up to 5)
    - Direct link to the PubMed article page (clickable URL)

    Always include the article URL in your response so the user can click
    through to the original source.

    Args:
        query: PubMed search query. Supports MeSH terms, boolean operators
               (AND, OR, NOT), field tags (e.g. [Title], [Author]), etc.
               Example: "GLP-1 receptor agonist weight loss[Title]"
        max_results: Maximum number of articles to return (default: 10, max: 50).

    Returns:
        JSON string with a list of article dicts, each containing pmid, title,
        abstract, journal, year, authors, and url.
    """
    if not _HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx not installed"})

    max_results = min(max(1, max_results), 50)
    try:
        # Step 1: Search — get PMIDs
        search_data = _get(_ESEARCH_URL, _ncbi_params(
            term=query,
            retmax=max_results,
            sort="relevance",
        ))
        if isinstance(search_data, str):
            return json.dumps({"error": "Unexpected response from esearch"})

        pmids: list[str] = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return json.dumps({"query": query, "results": [], "count": 0})

        # Step 2: Fetch full records
        fetch_text = _get(_EFETCH_URL, {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
            **({"api_key": _NCBI_API_KEY} if _NCBI_API_KEY else {}),
        })
        if not isinstance(fetch_text, str):
            return json.dumps({"error": "Unexpected efetch response type"})

        articles = _parse_efetch_xml(fetch_text)
        return json.dumps({
            "query": query,
            "count": len(articles),
            "results": articles,
        }, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.request.url}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool
def pubmed_fetch_tool(pmids: list[str]) -> str:
    """
    Fetch title and abstract for one or more specific PubMed IDs (PMIDs).

    Use this when you already know the PMIDs and want the full title +
    abstract without performing a new search.

    Args:
        pmids: List of PubMed IDs (strings), e.g. ["38123456", "37654321"].
               Maximum 20 PMIDs per call.

    Returns:
        JSON string with a list of article dicts (pmid, title, abstract,
        journal, year, authors, url).
    """
    if not _HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx not installed"})
    if not pmids:
        return json.dumps({"error": "No PMIDs provided"})

    pmids = pmids[:20]  # hard cap
    try:
        fetch_text = _get(_EFETCH_URL, {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
            **({"api_key": _NCBI_API_KEY} if _NCBI_API_KEY else {}),
        })
        if not isinstance(fetch_text, str):
            return json.dumps({"error": "Unexpected efetch response type"})

        articles = _parse_efetch_xml(fetch_text)
        return json.dumps({
            "count": len(articles),
            "results": articles,
        }, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}: {e.request.url}"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})
