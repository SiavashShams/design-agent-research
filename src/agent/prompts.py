import json
from typing import List, Dict
from src.schemas.responses import DesignResearchResponse
from src.utils.config import get_prompt_excerpt_max_chars

# Use if you want to limit the LLM's context
def _truncate(text: str, max_chars: int | None = None) -> str:
    if max_chars is None:
        max_chars = get_prompt_excerpt_max_chars()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def build_prompt(
    question: str,
    classification: str,
    ranked_sources: List[Dict],
    extracted_sources: List[Dict],
) -> str:
    """Constructs the synthesis prompt with ranked sources.

    The LLM must produce a valid JSON object matching DesignResearchResponse.
    """

    schema_json = DesignResearchResponse.model_json_schema()
    compact_schema = json.dumps(schema_json, separators=(",", ":"))

    lines: List[str] = []
    lines.append("You will produce a single JSON object only. No markdown or prose.")
    lines.append("The JSON must follow the DesignResearchResponse schema shown below.")
    lines.append("")
    lines.append(f"Question: {question}")
    lines.append(f"Query classification: {classification}")
    lines.append("")
    lines.append("Ranked sources (title | url):")
    for s in ranked_sources:
        title = s.get("title") or "Untitled"
        url = s.get("url") or ""
        lines.append(f"- {title} | {url}")
    lines.append("")
    lines.append("Source content excerpts (use these for grounding; do not fabricate):")
    for src in extracted_sources:
        title = src.get("title") or "Untitled"
        url = src.get("url") or ""
        content = src.get("content") or ""
        lines.append(f"- {title} | {url}")
        if content:
            lines.append(content)
        lines.append("")
    lines.append("JSON Schema (Pydantic v2 compatible):")
    lines.append(compact_schema)
    lines.append("")
    lines.append("Instructions:")
    lines.append("- Synthesize, don't summarize.")
    lines.append("- Provide 5-10 best_practices, actionable and specific.")
    lines.append("- Include 3-6 examples with working URLs; images optional.")
    lines.append(
        "- considerations must include tradeoffs, accessibility (cite WCAG where relevant), performance, browser_support."
    )
    lines.append("- When citing accessibility, include exact WCAG 2.2 criterion IDs where applicable.")
    lines.append("- If an example has a known image, set examples[].image_url to that URL; otherwise null.")
    lines.append("- Ensure every citation in text maps to a listed source URL.")
    lines.append("- Include inline bracket citations like [n] that reference the sources list (1-based index).")
    lines.append("- Add citations after claims (stats, dates, support, quotes); do not invent indices.")
    lines.append("- Output strictly valid JSON. Do not wrap in code fences.")
    return "\n".join(lines)


