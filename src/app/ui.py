import re
from dataclasses import dataclass
from typing import List, Optional

import streamlit as st

from src.schemas.responses import DesignResearchResponse, Source
from src.evaluation.evaluator import evaluate_response_stream


@dataclass
class Settings:
    provider_code: str
    enable_brave: bool
    include_images: bool
    max_results: int
    enable_logging: bool
    evaluator_provider: str


def get_settings() -> Settings:
    with st.sidebar:
        st.header("Settings")
        llm_provider_display = st.selectbox("LLM Provider", options=["GPT-5", "Claude Sonnet 4.5"], index=0)
        enable_brave = st.checkbox("Enable Brave Search", value=False)
        include_images = st.checkbox("Include images", value=True)
        max_results = st.slider("Max results", min_value=1, max_value=12, value=10, step=1)
        st.divider()
        st.subheader("Developer Options")
        enable_logging = st.checkbox("Enable pipeline logging", value=True, help="Show detailed logs of each pipeline stage in terminal")
        evaluator_provider = st.selectbox(
            "Evaluator Provider",
            options=["GPT-5", "Claude Sonnet 4.5"],
            index=0,
            help="Provider to use when evaluating the response",
        )

    provider_code = "GPT-5" if llm_provider_display == "GPT-5" else "Claude Sonnet 4.5"
    return Settings(
        provider_code=provider_code,
        enable_brave=enable_brave,
        include_images=include_images,
        max_results=max_results,
        enable_logging=enable_logging,
        evaluator_provider=evaluator_provider,
    )


def make_progress_cb(container: "st.delta_generator.DeltaGenerator"):
    progress = container.progress(0)
    stage_text = container.empty()
    label_map = {"search": "Search", "extract": "Extracting information", "analysis": "Analysis", "done": "Done"}

    def _cb(stage: str, pct: float) -> None:
        progress.progress(min(max(pct, 0.0), 1.0))
        stage_text.write(label_map.get(stage, "Working…"))

    return _cb


def linkify_citations(text: str, sources: List[Source]) -> str:
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        num_str = match.group(1)
        try:
            idx = int(num_str) - 1
            if 0 <= idx < len(sources):
                url = str(sources[idx].url)
                return f"[{num_str}]({url})"
        except Exception:
            pass
        return match.group(0)

    linked = re.sub(r"\[([1-9]\d*)\]", repl, text)
    linked = re.sub(r"\)\[", ") [", linked)
    return linked


def render_summary(response: DesignResearchResponse) -> None:
    st.subheader("Summary")
    st.markdown(linkify_citations(response.summary, response.sources))


def render_best_practices(response: DesignResearchResponse) -> None:
    st.subheader("Best practices")
    for item in response.best_practices:
        st.markdown(f"- {linkify_citations(item, response.sources)}")


def render_examples(response: DesignResearchResponse) -> None:
    st.subheader("Examples")
    cols = st.columns(3)
    for idx, ex in enumerate(response.examples):
        with cols[idx % 3]:
            st.markdown(f"**{ex.title}**")
            if ex.description:
                st.markdown(linkify_citations(ex.description, response.sources))
            st.markdown(f"[Open]({ex.url})")
            if ex.image_url:
                st.image(str(ex.image_url), use_container_width=True)
            if ex.source_domain:
                st.caption(ex.source_domain)


def render_considerations(response: DesignResearchResponse) -> None:
    st.subheader("Considerations")
    with st.expander("Tradeoffs"):
        for t in response.considerations.tradeoffs:
            st.markdown(f"- {linkify_citations(t, response.sources)}")
    with st.expander("Accessibility"):
        for a in response.considerations.accessibility:
            st.markdown(f"- {linkify_citations(a, response.sources)}")
    with st.expander("Performance"):
        for p in response.considerations.performance:
            st.markdown(f"- {linkify_citations(p, response.sources)}")
    with st.expander("Browser support"):
        for b in response.considerations.browser_support:
            st.markdown(f"- {linkify_citations(b, response.sources)}")


def render_sources(response: DesignResearchResponse) -> None:
    st.subheader("Sources")
    for s in response.sources:
        meta = []
        if s.publisher:
            meta.append(s.publisher)
        if s.publish_date:
            meta.append(s.publish_date)
        if s.relevance_score is not None:
            meta.append(f"score {s.relevance_score:.2f}")
        meta_str = " · ".join(meta)
        st.markdown(f"- [{s.title}]({s.url}){(' — ' + meta_str) if meta_str else ''}")


def render_evaluation_ui(last_query: str, last_response: DesignResearchResponse, evaluator_provider: str) -> None:
    st.subheader("Evaluation")
    col_eval_btn, _ = st.columns([1, 3])
    with col_eval_btn:
        if st.button("Evaluate response"):
            stream_container = st.container()
            progress = stream_container.progress(0)
            status_text = stream_container.empty()
            buffer = ""
            stage_order = [
                ("relevance", "Evaluating relevance…"),
                ("synthesis_quality", "Evaluating synthesis quality…"),
                ("completeness", "Evaluating completeness…"),
                ("actionability", "Evaluating actionability…"),
                ("citations", "Evaluating citations…"),
                ("accessibility", "Evaluating accessibility…"),
                ("examples_quality", "Evaluating examples quality…"),
                ("overall_score", "Finalizing score and critique…"),
            ]
            seen_keys = set()
            status_text.write("Starting evaluation…")
            expected_chars = 5000
            accumulated = 0
            try:
                for chunk in evaluate_response_stream(
                    user_query=last_query,
                    response=last_response,
                    evaluator_provider=evaluator_provider,
                ):
                    buffer += chunk
                    accumulated += len(chunk)
                    for key, label in stage_order:
                        if key not in seen_keys and f'"{key}"' in buffer:
                            seen_keys.add(key)
                            pct = min(0.95, 0.10 + (len(seen_keys) / len(stage_order)) * 0.60)
                            progress.progress(pct)
                            status_text.write(label)
                    frac = min(0.95, 0.10 + (accumulated / expected_chars) * 0.60)
                    progress.progress(frac)
                progress.progress(1.0)
                status_text.write("Parsing results…")
                from src.utils.json_utils import coerce_json_object
                from src.schemas.evaluation_schema import EvaluationResult

                data = coerce_json_object(buffer)
                st.session_state["last_evaluation"] = EvaluationResult(**data)
                status_text.write("Evaluation complete")
            except Exception as e:
                st.error(f"Evaluation failed: {e}")

    if st.session_state.get("last_evaluation") is not None:
        evaluation = st.session_state["last_evaluation"]
        st.metric("Overall Score", f"{evaluation.overall_score:.1f}/100")
        scores = evaluation.scores
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Relevance", f"{scores.relevance.score:.1f}/10")
            st.metric("Synthesis Quality", f"{scores.synthesis_quality.score:.1f}/10")
            st.metric("Completeness", f"{scores.completeness.score:.1f}/10")
        with c2:
            st.metric("Actionability", f"{scores.actionability.score:.1f}/10")
            st.metric("Citations", f"{scores.citations.score:.1f}/10")
            st.metric("Accessibility", f"{scores.accessibility.score:.1f}/10")
            st.metric("Examples Quality", f"{scores.examples_quality.score:.1f}/10")

        if evaluation.overall_critique:
            st.markdown("**Overall critique**")
            st.write(evaluation.overall_critique)
        if evaluation.key_strengths:
            with st.expander("Key strengths"):
                for s in evaluation.key_strengths:
                    st.markdown(f"- {s}")
        if evaluation.key_weaknesses:
            with st.expander("Key weaknesses"):
                for w in evaluation.key_weaknesses:
                    st.markdown(f"- {w}")
        if evaluation.recommendations:
            with st.expander("Recommendations"):
                for r in evaluation.recommendations:
                    st.markdown(f"- {r}")
        if evaluation.query_type_appropriateness:
            st.caption(f"Query type appropriateness: {evaluation.query_type_appropriateness}")


