from typing import Dict, Optional

import httpx

from src.utils.config import get_fetch_timeout_seconds


def fetch_with_jina(url: str) -> Dict[str, Optional[str]]:
    """Fetch cleaned content through Jina Reader.

    Returns a dict with keys: title, content. Metadata extraction can be
    extended later as needed.
    """

    # Jina Reader proxy endpoint returns readable content of the target URL.
    proxy = f"https://r.jina.ai/{url}"
    with httpx.Client(timeout=get_fetch_timeout_seconds()) as client:
        resp = client.get(proxy)
        resp.raise_for_status()
        text = resp.text

    # Title cannot be reliably parsed without HTML; many Jina outputs start
    # with the title line; we keep it simple here and leave title None.
    return {"title": None, "content": text}


