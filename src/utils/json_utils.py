import json


def coerce_json_object(raw: str) -> dict:
    """Attempt to coerce an LLM string into a JSON object.

    Strategy:
      - Trim whitespace
      - If extra text surrounds JSON, slice between first '{' and last '}'
      - Try json.loads
      - If that fails, remove a couple common trailing-comma artifacts and retry
    Raises json.JSONDecodeError if still invalid.
    """

    raw_stripped = (raw or "").strip()
    if not raw_stripped.startswith("{") or not raw_stripped.endswith("}"):
        start = raw_stripped.find("{")
        end = raw_stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_stripped = raw_stripped[start : end + 1]

    try:
        return json.loads(raw_stripped)
    except json.JSONDecodeError:
        cleaned = raw_stripped.replace(",\n\n", "\n\n").replace(",\n \n", "\n \n")
        return json.loads(cleaned)


