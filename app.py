import re
from typing import Optional, List

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from src.agent import orchestrator
from src.schemas.requests import AgentRequest
from src.schemas.responses import DesignResearchResponse, Source
from src.utils.config import (
    assert_required_keys,
    set_runtime_options,
)
from src.evaluation.evaluator import evaluate_response_stream
from src.app.ui import (
    Settings,
    get_settings,
    make_progress_cb,
    linkify_citations,
    render_summary,
    render_best_practices,
    render_examples,
    render_considerations,
    render_sources,
    render_evaluation_ui,
)


load_dotenv()

def _run_research(question: str, settings: Settings, progress_cb) -> Optional[DesignResearchResponse]:
    """Run the full pipeline and return a response or None on error."""
    request = AgentRequest(
        question=question.strip(),
        max_results=settings.max_results,
        include_images=settings.include_images,
    )
    try:
        return orchestrator.run(
            request,
            enable_logging=settings.enable_logging,
            parallel_fetch=True,
            progress_cb=progress_cb,
            expected_analysis_chars=6000,
        )
    except NotImplementedError:
        st.error("Backend pipeline is not implemented yet. Please implement orchestrator.run().")
        return None
    except ValidationError as v_err:
        st.error(f"Validation error: {v_err}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None


"""Evaluation UI lives in src.app.ui.render_evaluation_ui."""


def _validate_keys_or_error(llm_provider: str, enable_brave: bool) -> bool:
    try:
        assert_required_keys(llm_provider, enable_brave)
        return True
    except ValueError as e:
        st.error(str(e))
        return False


def main() -> None:
    st.set_page_config(page_title="Design Research Agent", layout="wide")
    st.title("Design Research Agent")
    st.caption("Searching → Fetching content → Analyzing → Done")

    settings = get_settings()

    question = st.text_area("Enter your design research question", height=120, placeholder="e.g., What are best practices for mobile navigation patterns in 2024?")

    run_clicked = st.button("Run research")

    if run_clicked:
        if not question or len(question.strip()) < 5:
            st.warning("Please enter a longer question (≥ 5 characters).")
            return

        # Configure runtime and validate keys
        set_runtime_options(settings.provider_code, settings.enable_brave)
        if not _validate_keys_or_error(settings.provider_code, settings.enable_brave):
            return

        # Custom progress bar for search → extract → analysis → done
        st.subheader("Progress")
        progress_container = st.container()
        progress_cb = make_progress_cb(progress_container)

        # Run search → fetch → analyze
        result = _run_research(question, settings, progress_cb)
        if result is None:
            return

        # Persist latest result and query for evaluation step
        st.session_state["last_query"] = question.strip()
        st.session_state["last_response"] = result
        st.session_state.pop("last_evaluation", None)

    # Always render the latest response
    last_response: Optional[DesignResearchResponse] = st.session_state.get("last_response")
    if last_response is not None:
        render_summary(last_response)
        render_best_practices(last_response)
        render_examples(last_response)
        render_considerations(last_response)
        render_sources(last_response)

        st.divider()
        render_evaluation_ui(
            last_query=st.session_state.get("last_query", ""),
            last_response=last_response,
            evaluator_provider=settings.evaluator_provider,
        )


if __name__ == "__main__":
    main()


