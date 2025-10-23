from typing import List, Tuple


ACCESSIBILITY_KEYWORDS = [
    "wcag",
    "accessibility",
    "aria",
    "contrast",
    "keyboard",
    "screen reader",
]
FEASIBILITY_KEYWORDS = [
    "feasibility",
    "browser support",
    "performance",
    "container queries",
    "supports",
]
INSPIRATION_KEYWORDS = [
    "examples",
    "inspiration",
    "gallery",
    "show me",
    "visual",
]


def classify_query(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ACCESSIBILITY_KEYWORDS):
        return "accessibility"
    if any(k in q for k in FEASIBILITY_KEYWORDS):
        return "feasibility"
    if any(k in q for k in INSPIRATION_KEYWORDS):
        return "inspiration"
    return "pattern"


def generate_search_variants(question: str, classification: str) -> List[str]:
    base = question.strip()
    variants: List[str] = [base]

    if classification == "pattern":
        variants.append(f"best practices {base}")
        variants.append(f"common pitfalls {base}")
        variants.append(f"2024 2025 {base}")
    elif classification == "accessibility":
        variants.append(f"wcag {base}")
        variants.append(f"aria {base}")
        variants.append(f"keyboard navigation {base}")
    elif classification == "inspiration":
        variants.append(f"examples {base}")
        variants.append(f"ui inspiration {base}")
        variants.append(f"design patterns {base}")
    elif classification == "feasibility":
        variants.append(f"browser support {base}")
        variants.append(f"performance {base}")
        variants.append(f"mdn {base}")

    # Deduplicate variants while preserving order
    seen = set()
    deduped: List[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped[:6]


def enhance(question: str) -> Tuple[str, List[str]]:
    classification = classify_query(question)
    return classification, generate_search_variants(question, classification)


