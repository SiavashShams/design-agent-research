import os
from typing import List, Tuple


_RUNTIME_OPTIONS: Tuple[str, bool] | None = None


def set_runtime_options(llm_provider: str, enable_brave: bool) -> None:
    """Set runtime options chosen in the UI for downstream components.

    Parameters
    ----------
    llm_provider: str
        Identifier for the LLM provider, e.g., "GPT-5" or "Claude Sonnet 4.5".
    enable_brave: bool
        Whether Brave search should be used alongside Exa.
    """

    global _RUNTIME_OPTIONS
    _RUNTIME_OPTIONS = (llm_provider, enable_brave)


def get_runtime_options() -> Tuple[str, bool]:
    """Return the currently configured runtime options.

    Returns
    -------
    Tuple[str, bool]
        (llm_provider, enable_brave)
    """

    if _RUNTIME_OPTIONS is None:
        # Default to OpenAI and Brave off if not explicitly set by UI.
        return ("GPT-5", False)
    return _RUNTIME_OPTIONS


def _present(key: str) -> bool:
    value = os.getenv(key)
    return bool(value and value.strip())


def required_keys_for(llm_provider: str, enable_brave: bool) -> List[str]:
    """List required environment variable keys for the chosen options."""

    keys: List[str] = ["EXA_API_KEY"]
    if llm_provider == "GPT-5":
        keys.append("OPENAI_API_KEY")
    elif llm_provider == "Claude Sonnet 4.5":
        keys.append("ANTHROPIC_API_KEY")
    else:
        raise ValueError(
            f"Unsupported llm_provider '{llm_provider}'. Choose 'GPT-5' or 'Claude Sonnet 4.5'."
        )
    if enable_brave:
        keys.append("BRAVE_API_KEY")
    return keys


def assert_required_keys(llm_provider: str, enable_brave: bool) -> None:
    """Fail fast if any required API key is missing.

    Raises
    ------
    ValueError
        With a clear message listing missing keys.
    """

    missing = [k for k in required_keys_for(llm_provider, enable_brave) if not _present(k)]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            "Missing required API keys: "
            f"{missing_str}. Please set them in your environment or .env file."
        )


def _float_env(key: str, default: float) -> float:
    value = os.getenv(key)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_search_timeout_seconds() -> float:
    """HTTP timeout for search providers (seconds). Default 20."""

    return _float_env("HTTP_TIMEOUT_SEARCH", 20.0)


def get_fetch_timeout_seconds() -> float:
    """HTTP timeout for content fetch (seconds). Default 45."""

    return _float_env("HTTP_TIMEOUT_FETCH", 45.0)


# ---------------------------------------------------------------------------
# Tunable pipeline constants (configurable via environment variables)
# ---------------------------------------------------------------------------

def _int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if not value:
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


# Search caps per variant (defaults preserve current behavior)
def get_exa_results_per_variant() -> int:
    return _int_env("EXA_RESULTS_PER_VARIANT", 6)


def get_brave_results_per_variant() -> int:
    return _int_env("BRAVE_RESULTS_PER_VARIANT", 8)


# Ranking caps (min/max kept from current implementation)
def get_min_ranked_results() -> int:
    return _int_env("MIN_RANKED_RESULTS", 6)


def get_max_ranked_results() -> int:
    return _int_env("MAX_RANKED_RESULTS", 8)


# Extraction limits and parallelism
def get_extract_top_k() -> int:
    return _int_env("EXTRACT_TOP_K", 10)


def get_parallel_max_workers() -> int:
    return _int_env("PARALLEL_MAX_WORKERS", 5)


# Prompt excerpt size for grounded content
def get_prompt_excerpt_max_chars() -> int:
    return _int_env("PROMPT_EXCERPT_MAX_CHARS", 1200)

