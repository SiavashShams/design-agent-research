from typing import Dict, List


AUTHORITY_DOMAINS = {
    "nngroup.com": 3.0,
    "alistapart.com": 2.0,
    "smashingmagazine.com": 2.0,
    "web.dev": 3.0,
    "developer.mozilla.org": 3.0,
    "w3.org": 3.0,
    "lawsofux.com": 2.0,
    "baymard.com": 2.5,
}


def _domain(url: str) -> str:
    try:
        return url.split("//", 1)[-1].split("/", 1)[0].lower()
    except Exception:
        return ""


def dedup_and_rank(candidates: List[Dict]) -> List[Dict]:
    seen_urls = set()
    pruned: List[Dict] = []
    for c in candidates:
        url = c.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        d = _domain(url)
        authority = 0.0
        for dom, weight in AUTHORITY_DOMAINS.items():
            if d.endswith(dom):
                authority = max(authority, weight)
        c["score"] = authority
        pruned.append(c)

    pruned.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return pruned


