# Design Research Agent — Architecture

This document explains the system design, pipeline, major components, trade‑offs, and extension points of the Design Research Agent. It is written for engineers and reviewers evaluating code quality, performance, reliability, and product fit for the assignment.

---

## Goals and Non‑Goals

### Goals
- Answer design questions across four query types: pattern, accessibility, inspiration, feasibility
- Return original synthesis (not copy‑paste), with citations and concrete examples
- Provide actionable best practices and considerations (trade‑offs, performance, browser support, accessibility)
- Run on a single machine, stateless, with typical queries completing in < 120 seconds
- Degrade gracefully under partial failure and surface useful partial results

---

## High‑Level Overview

```
User Query
  ↓
Query Enhancement (classification + variants)
  ↓
Multi‑Source Search (Exa + optional Brave)
  ↓
Deduplicate & Rank (authority weights)
  ↓
Parallel Extraction (Jina Reader + primary image)
  ↓
LLM Synthesis (JSON‑only prompt)
  ↓
Pydantic Validation (DesignResearchResponse)
  ↓
UI Render (citations, images, considerations)
  ↓
Optional LLM Evaluation (scores + critique)
```

The orchestration is synchronous and stateless; all external calls are wrapped with timeouts. Results are streamed to the UI during analysis for good perceived performance.

---

## Tech Stack
- Language/runtime: Python 3.12
- UI: Streamlit
- HTTP client: `httpx`
- Content extraction: Jina Reader proxy (`https://r.jina.ai/{url}`), `lxml` HTML parsing for images
- Search providers: Exa (semantic), Brave (web) — both optional behind environment keys
- LLM providers: OpenAI GPT‑5 (primary), Claude Sonnet 4.5 (optional)
- Validation: Pydantic v2 models
- Concurrency: `ThreadPoolExecutor` for parallel I/O
- Config: `.env` via `python-dotenv`

Environment variables are listed and validated in `src/utils/config.py`. The app fails fast with a clear error if required keys are missing.

---

## Repository Layout (selected)

```
design-agent-research/
├── app.py                          # Streamlit UI
├── src/
│   ├── agent/
│   │   ├── orchestrator.py         # Main orchestration pipeline
│   │   ├── query_enhancer.py       # Classification and query variant generation
│   │   └── prompts.py              # JSON‑only synthesis prompt
│   ├── search/
│   │   ├── exa_search.py           # Exa API wrapper
│   │   ├── brave_search.py         # Brave Search API wrapper
│   │   └── deduplicator.py         # Dedup + authority ranking
│   ├── extract/
│   │   ├── jina_extractor.py       # Clean text extraction (Jina Reader)
│   │   ├── image_extractor.py      # Primary image heuristics (og:image → <img>)
│   │   └── parallel_extractor.py   # Threaded multi‑URL extraction
│   ├── llm/
│   │   ├── openai_client.py        # GPT‑5 client (stream + non‑stream)
│   │   └── claude_client.py        # Claude Sonnet 4.5 client (stream + non‑stream)
│   ├── schemas/
│   │   ├── requests.py             # AgentRequest
│   │   └── responses.py            # DesignResearchResponse + submodels
│   ├── evaluation/
│   │   ├── evaluator.py            # LLM‑based evaluator (streaming)
│   │   └── prompts.py              # Evaluation prompt builder
│   ├── schemas/
│   │   ├── requests.py             # AgentRequest
│   │   ├── responses.py            # DesignResearchResponse + submodels
│   │   └── evaluation_schema.py    # EvaluationResult model
│   └── utils/
│       ├── config.py               # Env, timeouts, tunables
│       ├── pipeline_logger.py      # Structured stage logging
│       └── json_utils.py           # Robust JSON object coercion
└── docs/                           # This file + detailed notes
```

---

## Data Contracts (Pydantic v2)

Input (`src/schemas/requests.py`):
- `AgentRequest` — `question: str`, `max_results: int = 10`, `include_images: bool = True`

Output (`src/schemas/responses.py`):
- `DesignResearchResponse` with:
  - `summary: str`
  - `best_practices: list[str]`
  - `examples: list[Example]` where `Example` has `title`, `url`, optional `description`, `image_url`, `source_domain`
  - `considerations: Considerations` with `tradeoffs`, `accessibility`, `performance`, `browser_support`
  - `sources: list[Source]` with `title`, `url`, optional `publisher`, `publish_date`, `relevance_score`

The UI renders exactly this structure and adds linkified citations in text (`[n]` → nth source URL).

---

## Orchestration Pipeline

The pipeline is implemented in `src/agent/orchestrator.py` and is responsible for end‑to‑end execution.

1. Logging + runtime checks
- Keys validated with `assert_required_keys()` from `utils/config.py`
- `pipeline_logger` collects stage events for debugging

2. Query enhancement (`agent/query_enhancer.py`)
- Lightweight classification: `pattern | accessibility | inspiration | feasibility`
- Keyword‑based routing (e.g., WCAG → accessibility; browser support → feasibility)
- Generates 3–6 variants per class (e.g., add `wcag`, `aria` for accessibility; `mdn`, `browser support` for feasibility)

3. Multi‑source search (`search/exa_search.py`, `search/brave_search.py`)
- Each variant queries Exa; Brave is optional via a UI flag
- Timeouts enforced (`HTTP_TIMEOUT_SEARCH`)
- Normalized results: `title`, `url`, `snippet`

4. Deduplicate & rank (`search/deduplicator.py`)
- Exact URL deduplication
- Domain authority weights (e.g., `developer.mozilla.org`, `w3.org`, `web.dev`, `nngroup.com`, `baymard.com`)
- Results sorted by authority score (simple, transparent heuristic for MVP)

5. Extraction (`extract/parallel_extractor.py`)
- Threaded pool to fetch top K ranked URLs
- Content via Jina Reader proxy (`jina_extractor.fetch_with_jina`)
- Primary image via `image_extractor.extract_primary_image_debug()` with priority:
  1) `og:image` / Twitter card → 2) first suitable `<img>`
- All outbound requests have `HTTP_TIMEOUT_FETCH`

6. Prompt construction (`agent/prompts.py`)
- JSON‑only instruction: model must return one object that validates against `DesignResearchResponse`
- Includes compact JSON schema (+ grounded text excerpts) to reduce hallucinations
- Enforces bracketed citations `[n]` mapped to the `sources` list

7. LLM Synthesis (`llm/openai_client.py` | `llm/claude_client.py`)
- Streamed generation preferred for responsive UI; falls back to non‑stream
- Progress bar advances using expected character counts

8. Validation & enrichment
- Response coerced with `json_utils.coerce_json_object()`
- Pydantic validation to ensure contract compliance
- If images were extracted and an example has `null` `image_url`, the orchestrator fills from our extraction map when possible

9. UI rendering (`app.py`)
- Staged progress: Search → Extracting information → Analysis → Done
- Sections: Summary, Best Practices, Examples (with images), Considerations, Sources
- Citations in text are linkified to the corresponding source URLs
- Optional: evaluator run with streaming progress per sub‑score

---

## Configuration and Tunables (`src/utils/config.py`)
- `EXA_RESULTS_PER_VARIANT`, `BRAVE_RESULTS_PER_VARIANT`
- Ranking limits: `MIN_RANKED_RESULTS`, `MAX_RANKED_RESULTS`
- Extraction: `EXTRACT_TOP_K`, `PARALLEL_MAX_WORKERS`
- Timeouts: `HTTP_TIMEOUT_SEARCH` (default 20s), `HTTP_TIMEOUT_FETCH` (default 45s)
- Prompt excerpt cap: `PROMPT_EXCERPT_MAX_CHARS`

Defaults are chosen to keep typical runs below 120 seconds while maintaining quality.

---

## Error Handling & Resilience
- Defensive try/except around all network calls; clear warnings rather than crashes
- Timeouts on every HTTP request (search, fetch)
- Graceful degradation: if one provider fails, continue with remaining results
- Validation errors caught and surfaced with actionable messages in the UI
- Logging provides stage‑level breadcrumbs for debugging

---

## Performance Characteristics
- Parallel extraction yields significant speedups for K≥4 URLs
- Streaming synthesis improves perceived performance; progress advances with token counts
- Ranked‑source extraction caps total fetched pages to reduce I/O and LLM prompt size
- Typical end‑to‑end time: 45–60s; worst cases (network variability): within 120s

Further optimization ideas:
- Caching frequently used sources
- Async HTTP for search/extract (aiohttp) if concurrency warrants
- Incremental synthesis (LLM consumes in batches) for very large prompts

---

## Quality Strategy (MVP)
- Prefer authority sources (W3C, MDN, NN/g, Baymard, web.dev)
- Simple domain‑authority ranking keeps behavior predictable and explainable
- Image selection prioritizes `og:image` and sufficiently large DOM images
- Schema‑enforced output reduces hallucinations and ensures structured results
- Optional evaluator highlights synthesis quality and citation gaps

Known trade‑offs for MVP:
- No semantic dedup across near‑duplicates
- Some inspiration queries may surface third‑party articles; manual curation may still help
- Paywalled pages may block high‑quality images; the app shows text‑only in those cases

---

## Limitations and Risks
- Some quantitative claims in sources may be unverified; agent does not currently fact‑check statistics
- Image extraction depends on publisher markup; not all pages expose `og:image` or permissive assets
- Browser support percentages are not computed from live telemetry; they rely on cited sources

---

## Extension Points
- Search: add provider modules to `src/search/` and merge into orchestrator
- Ranking: extend `deduplicator.py` to include recency, query‑term overlap, or blocklists
- Extraction: add DOM scraping fallback and richer metadata (publish date, author)
- Image: add srcset parsing and intrinsic size estimation; whitelist canonical product domains
- Synthesis: few‑shot examples per query type, or ensemble prompts
- Evaluation: rule‑based checks in addition to LLM evaluator (e.g., URL validity, image presence)
- UI: filtering (show examples with images only), export to JSON/Markdown

---

## Rationale Summary
- Favor explainable heuristics over complex ranking for MVP
- Streamlit UI for fast, clear iteration and progress visibility
- Jina Reader for reliable text extraction across many sites
- GPT‑5 for synthesis due to strong JSON adherence and synthesis skills
- Pydantic schemas to guarantee contract and simplify UI rendering

