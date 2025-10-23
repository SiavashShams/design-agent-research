import os
import time
from typing import Dict, List, Callable, Optional
from dotenv import load_dotenv

from src.schemas.requests import AgentRequest
from src.schemas.responses import DesignResearchResponse
from src.agent.query_enhancer import enhance
from src.search.exa_search import search_exa
from src.search.brave_search import search_brave
from src.search.deduplicator import dedup_and_rank
from src.extract.jina_extractor import fetch_with_jina
from src.extract.image_extractor import extract_primary_image
from src.extract.parallel_extractor import extract_content_parallel
from src.agent.prompts import build_prompt
from src.llm.openai_client import OpenAILLM
from src.llm.claude_client import ClaudeLLM
from src.utils.config import (
    get_runtime_options,
    assert_required_keys,
    get_exa_results_per_variant,
    get_brave_results_per_variant,
    get_min_ranked_results,
    get_max_ranked_results,
    get_extract_top_k,
    get_parallel_max_workers,
)
from src.utils.pipeline_logger import get_logger, reset_logger
from src.utils.json_utils import coerce_json_object

# Ensure .env variables are loaded for non-Streamlit runs (e.g., python -c)
load_dotenv()


def _select_llm() -> object:
    llm_provider, _ = get_runtime_options()
    if llm_provider == "GPT-5":
        return OpenAILLM()
    if llm_provider == "Claude Sonnet 4.5":
        return ClaudeLLM()
    raise ValueError("Unsupported LLM provider")


def run(
    request: AgentRequest,
    enable_logging: bool = True,
    parallel_fetch: bool = True,
    progress_cb: Optional[Callable[[str, float], None]] = None,
    expected_analysis_chars: int = 6000,
) -> DesignResearchResponse:
    """
    Run the full orchestration pipeline with optional detailed logging.
    
    Args:
        request: The agent request with query and options
        enable_logging: Whether to enable detailed pipeline logging
        parallel_fetch: Whether to fetch content in parallel (much faster)
    
    Returns:
        Validated DesignResearchResponse
    """
    # Reset and get logger
    reset_logger()
    logger = get_logger(enabled=enable_logging)
    start_time = time.time()
    
    # Fail fast on missing keys even for programmatic calls
    llm_provider, enable_brave = get_runtime_options()
    assert_required_keys(llm_provider, enable_brave)

    # STAGE 1: Log user query
    logger.log_user_query(request.question, request.max_results, request.include_images)

    # STAGE 2: Query enhancement
    classification, variants = enhance(request.question)
    logger.log_query_enhancement(classification, variants)

    # STAGE 3: Multi-source search
    if progress_cb:
        try:
            progress_cb("search", 0.05)
        except Exception:
            pass
    exa_key = os.getenv("EXA_API_KEY")
    results: List[Dict] = []
    exa_count = 0
    
    exa_per_variant = min(get_exa_results_per_variant(), request.max_results)
    for v in variants:
        exa_results = search_exa(exa_key, v, num_results=exa_per_variant)
        results.extend(exa_results)
        exa_count += len(exa_results)

    # Optionally add Brave
    brave_count = 0
    if enable_brave:
        brave_key = os.getenv("BRAVE_API_KEY")
        brave_per_variant = min(get_brave_results_per_variant(), request.max_results)
        for v in variants:
            brave_results = search_brave(brave_key, v, count=brave_per_variant)
            results.extend(brave_results)
            brave_count += len(brave_results)

    sample_urls = [r.get("url") for r in results[:5]]
    logger.log_search_results(exa_count, brave_count, len(results), sample_urls)

    # STAGE 4: Dedup and rank
    before_dedup = len(results)
    min_rank = get_min_ranked_results()
    max_rank = get_max_ranked_results()
    ranked = dedup_and_rank(results)[: max(min_rank, min(max_rank, request.max_results))]
    logger.log_dedup_and_rank(before_dedup, len(ranked), ranked)
    if progress_cb:
        try:
            progress_cb("extract", 0.33)
        except Exception:
            pass

    # STAGE 5: Extract content
    if parallel_fetch:
        # Parallel extraction (much faster for multiple URLs)
        extracted = extract_content_parallel(
            ranked[: get_extract_top_k()],
            include_images=request.include_images,
            max_workers=get_parallel_max_workers(),
        )
    else:
        extracted: List[Dict] = []
        for r in ranked[: get_extract_top_k()]:
            url = r["url"]
            content = fetch_with_jina(url).get("content")
            image_url = extract_primary_image(url) if request.include_images else None
            extracted.append({
                "title": r.get("title"),
                "url": url,
                "content": content,
                "image_url": image_url,
            })
    
    logger.log_extraction(extracted)
    if progress_cb:
        try:
            progress_cb("analysis", 0.66)
        except Exception:
            pass

    # STAGE 6: Build prompt and synthesize
    prompt = build_prompt(request.question, classification, ranked, extracted)
    
    llm = _select_llm()
    raw = ""
    if progress_cb is not None:
        # Stream the progress
        try:
            progress_cb("analysis", 0.7)
        except Exception:
            pass
        accumulated = 0
        try:
            for chunk in llm.synthesize_stream(prompt):
                if not chunk:
                    continue
                raw += chunk
                accumulated += len(chunk)
                if progress_cb is not None and expected_analysis_chars > 0:
                    frac = min(0.90, 0.70 + (accumulated / expected_analysis_chars) * 0.20)
                    try:
                        progress_cb("analysis", frac)
                    except Exception:
                        pass
        except Exception:
            # Fallback to non-streaming if provider does not support stream
            # Sometimes openai does not support stream
            raw = llm.synthesize(prompt)
    else:
        raw = llm.synthesize(prompt)
    
    # Log LLM input and output in preview
    logger.log_llm_synthesis(
        prompt_preview=prompt,
        prompt_length=len(prompt),
        raw_response=raw,
        llm_provider=llm_provider,
    )
    
    # STAGE 7: Parse JSON response
    # Some providers may include stray text; attempt to locate the JSON object
    data = coerce_json_object(raw)

    # STAGE 8: Pydantic validation
    response = DesignResearchResponse(**data)
    if progress_cb:
        try:
            progress_cb("analysis", 0.9)
        except Exception:
            pass
    
    response_summary = {
        "classification": response.query_classification,
        "summary": response.summary,
        "best_practices_count": len(response.best_practices),
        "examples_count": len(response.examples),
        "sources_count": len(response.sources),
        "has_considerations": bool(response.considerations)
    }
    logger.log_validation(success=True, response_summary=response_summary)

    # Enrich missing example images from our extraction when include_images is true
    if request.include_images and response.examples:
        # Build a lookup map from URL to image_url we extracted
        url_to_img = {e["url"]: e.get("image_url") for e in extracted if e.get("image_url")}
        updated_examples = []
        for ex in response.examples:
            if not ex.image_url:
                img = url_to_img.get(str(ex.url))
                if img:
                    ex.image_url = img
            updated_examples.append(ex)
        response.examples = updated_examples
    
    # STAGE 9: Complete
    total_time = time.time() - start_time
    logger.log_completion(total_time)
    if progress_cb:
        try:
            progress_cb("done", 1.0)
        except Exception:
            pass
    
    return response


