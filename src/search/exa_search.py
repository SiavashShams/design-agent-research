from typing import Any, Dict, List

import httpx

from src.utils.config import get_search_timeout_seconds


EXA_ENDPOINT = "https://api.exa.ai/search"


def search_exa(api_key: str, query: str, num_results: int = 8) -> List[Dict[str, Any]]:
    """Call Exa search API and return normalized results.

    Returns a list of dicts with keys: title, url, snippet (if available).
    """

    headers = {"x-api-key": api_key}
    payload = {"query": query, "numResults": num_results}

    with httpx.Client(timeout=get_search_timeout_seconds()) as client:
        resp = client.post(EXA_ENDPOINT, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("results") or data.get("documents") or []
    normalized: List[Dict[str, Any]] = []
    for it in items:
        title = it.get("title") or it.get("id") or "Untitled"
        url = it.get("url") or it.get("link")
        snippet = it.get("text") or it.get("snippet")
        if url:
            normalized.append({"title": title, "url": url, "snippet": snippet})
    return normalized


