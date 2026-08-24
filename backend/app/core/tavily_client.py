import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logger = logging.getLogger(__name__)
TAVILY_URL = "https://api.tavily.com/search"


def tavily_api_key() -> str:
    return (os.getenv("TAVILY_API_KEY") or "").strip()


def has_tavily() -> bool:
    return bool(tavily_api_key())


def search(
    query: str,
    *,
    max_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    key = tavily_api_key()
    if not key or not (query or "").strip():
        return []
    payload: Dict[str, Any] = {
        "api_key": key,
        "query": query.strip()[:400],
        "search_depth": "basic",
        "max_results": max(1, min(int(max_results), 8)),
        "include_answer": False,
        "include_raw_content": False,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    try:
        res = requests.post(
            TAVILY_URL,
            json=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=12,
        )
        res.raise_for_status()
        data = res.json()
    except Exception as exc:
        logger.warning("Tavily search failed for %s: %s", query, exc)
        return []
    out = []
    for row in data.get("results") or []:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        out.append(
            {
                "title": row.get("title") or "",
                "url": row.get("url") or "",
                "snippet": row.get("content") or "",
                "score": float(row.get("score") or 0),
            }
        )
    return out
