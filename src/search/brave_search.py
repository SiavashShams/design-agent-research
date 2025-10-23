from typing import Any, Dict, List

import httpx

from src.utils.config import get_search_timeout_seconds


BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


def search_brave(api_key: str, query: str, count: int = 8) -> List[Dict[str, Any]]:
    """Call Brave Search API and return normalized results.

    Returns a list of dicts with keys: title, url, snippet (if available).
    """

    headers = {"X-Subscription-Token": api_key}
    params = {"q": query, "count": count}

    with httpx.Client(timeout=get_search_timeout_seconds()) as client:
        resp = client.get(BRAVE_ENDPOINT, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    web_results = (data.get("web") or {}).get("results") or []
    normalized: List[Dict[str, Any]] = []
    for it in web_results:
        title = it.get("title") or "Untitled"
        url = it.get("url")
        snippet = it.get("description")
        if url:
            normalized.append({"title": title, "url": url, "snippet": snippet})
    return normalized


