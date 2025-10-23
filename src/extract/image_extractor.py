from typing import Optional, List, Tuple

import httpx
from lxml import html
from urllib.parse import urljoin

from src.utils.config import get_fetch_timeout_seconds


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

ALLOWED_EXTS = (".jpg", ".jpeg", ".png", ".webp")
BLOCKLIST_SUBSTRINGS = (
    "logo",
    "favicon",
    "sprite",
    "icon",
    "avatar",
    "badge",
    "masthead",
    "placeholder",
)
SKIP_IMAGE_DOMAINS = (
    "developer.mozilla.org",
    "w3.org",
    "web.dev",
)
MIN_DIMENSION = 120


def _first_non_empty(values: list[str]) -> Optional[str]:
    for v in values:
        if v and v.strip():
            return v.strip()
    return None


def _absolutize(base_url: str, maybe_relative_url: str) -> str:
    return urljoin(base_url, maybe_relative_url)


def _domain_of(url: str) -> str:
    try:
        return url.split("//", 1)[-1].split("/", 1)[0].lower()
    except Exception:
        return ""


def _is_blocked(url: str) -> bool:
    dom = _domain_of(url)
    if any(dom.endswith(d) for d in SKIP_IMAGE_DOMAINS):
        return True
    lower = url.lower()
    if any(substr in lower for substr in BLOCKLIST_SUBSTRINGS):
        return True
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTS):
        return True
    return False


def _parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _score_candidate(url: str, from_meta: bool, dims: Tuple[Optional[int], Optional[int]]) -> int:
    if _is_blocked(url):
        return -10
    width, height = dims
    size_score = 0
    for dim in (width, height):
        if dim is not None:
            if dim >= 600:
                size_score = max(size_score, 3)
            elif dim >= 300:
                size_score = max(size_score, 2)
            elif dim >= MIN_DIMENSION:
                size_score = max(size_score, 1)
    meta_bonus = 3 if from_meta else 0
    return meta_bonus + size_score


def _fetch_html_direct(page_url: str, timeout: float) -> Optional[str]:
    """Fetch HTML directly; returns None on 403/401/429 or network errors."""
    try:
        with httpx.Client(
            timeout=timeout, headers=DEFAULT_HEADERS, follow_redirects=True
        ) as client:
            resp = client.get(page_url)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 401, 429):
            return None
        raise
    except httpx.HTTPError:
        return None


def _fetch_html_via_jina(page_url: str, timeout: float) -> Optional[str]:
    """Fetch HTML via Jina Reader proxy to bypass bot blocking."""
    try:
        proxy = f"https://r.jina.ai/{page_url}"
        with httpx.Client(timeout=timeout, headers=DEFAULT_HEADERS) as client:
            resp = client.get(proxy)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPError:
        return None


def extract_primary_image(page_url: str) -> Optional[str]:
    """Attempt to extract a representative image URL from a page.

    Prefers Open Graph/Twitter card images, falls back to the first <img>.
    Returns an absolute URL or None.
    """

    timeout = get_fetch_timeout_seconds()

    content = _fetch_html_direct(page_url, timeout)
    if content is None:
        content = _fetch_html_via_jina(page_url, timeout)
    if content is None:
        return None

    doc = html.fromstring(content)

    candidates: List[Tuple[str, bool, Tuple[Optional[int], Optional[int]]]] = []

    # Meta candidates
    meta_values = [
        doc.xpath('string(//meta[@property="og:image:secure_url"]/@content)') or None,
        doc.xpath('string(//meta[@property="og:image"]/@content)') or None,
        doc.xpath('string(//meta[@name="og:image"]/@content)') or None,
        doc.xpath('string(//meta[@property="twitter:image"]/@content)') or None,
        doc.xpath('string(//meta[@name="twitter:image"]/@content)') or None,
        doc.xpath('string(//link[@rel="image_src"]/@href)') or None,
    ]
    for m in [mv for mv in meta_values if mv]:
        candidates.append((_absolutize(page_url, m), True, (None, None)))

    # <img> candidates (gather a few, with dimensions when available)
    imgs = doc.xpath('//img[@src]')[:10]
    for img in imgs:
        src = img.get("src")
        if not src:
            continue
        width = _parse_int(img.get("width"))
        height = _parse_int(img.get("height"))
        candidates.append((_absolutize(page_url, src), False, (width, height)))

    # Score and select
    best_url: Optional[str] = None
    best_score = -999
    for url, from_meta, dims in candidates:
        score = _score_candidate(url, from_meta, dims)
        if score > best_score:
            best_score = score
            best_url = url

    return best_url if best_score >= 1 else None


def extract_primary_image_debug(page_url: str) -> Tuple[Optional[str], str, Tuple[Optional[int], Optional[int]]]:
    """Debug variant that returns image URL, source type, and dims.

    Returns
    -------
    (image_url, source_type, (width, height))
      - source_type: "meta" | "dom" | "none"
      - dims only available for DOM-sourced <img> when width/height attributes exist
    """

    timeout = get_fetch_timeout_seconds()

    content = _fetch_html_direct(page_url, timeout)
    if content is None:
        content = _fetch_html_via_jina(page_url, timeout)
    if content is None:
        return None, "none", (None, None)

    doc = html.fromstring(content)

    meta_values = [
        doc.xpath('string(//meta[@property="og:image:secure_url"]/@content)') or None,
        doc.xpath('string(//meta[@property="og:image"]/@content)') or None,
        doc.xpath('string(//meta[@name="og:image"]/@content)') or None,
        doc.xpath('string(//meta[@property="twitter:image"]/@content)') or None,
        doc.xpath('string(//meta[@name="twitter:image"]/@content)') or None,
        doc.xpath('string(//link[@rel="image_src"]/@href)') or None,
    ]
    # Prefer meta if present
    for m in [mv for mv in meta_values if mv]:
        url = _absolutize(page_url, m)
        if _score_candidate(url, True, (None, None)) >= 1:
            return url, "meta", (None, None)

    # Fallback to first suitable <img>
    imgs = doc.xpath('//img[@src]')[:10]
    for img in imgs:
        src = img.get("src")
        if not src:
            continue
        width = _parse_int(img.get("width"))
        height = _parse_int(img.get("height"))
        url = _absolutize(page_url, src)
        if _score_candidate(url, False, (width, height)) >= 1:
            return url, "dom", (width, height)

    return None, "none", (None, None)


