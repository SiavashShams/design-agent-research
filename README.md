# Design Research Agent

An AI assistant that helps product managers and designers make informed UI/UX decisions. It searches authoritative sources, extracts content, and synthesizes actionable recommendations with citations and examples. 

---

## Features
- Multi‑source search (Exa + optional Brave)
- Clean extraction via Jina Reader, parallel fetching for speed
- Synthesis with GPT‑5 or Claude Sonnet 4.5 (structured JSON output)
- Examples with image enrichment when available
- Built‑in evaluator that scores responses and provides critique
- Streamlit UI with staged progress: Search → Extract → Analyze → Done

---

## Quick Start

### 1) Clone and create a virtual environment
```bash
git clone <https://github.com/SiavashShams/design-agent-research.git
cd design-agent-research
python3 -m venv myenv
source myenv/bin/activate   # Windows: myenv\Scripts\activate
```

### 2) Install requirements
```bash
pip install -r requirements.txt
```

### 3) Set environment variables
Create a `.env` file in the project root with your API keys:

```bash
OPENAI_API_KEY=sk-...
EXA_API_KEY=...
BRAVE_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
JINA_API_KEY=
```

### 4) Run the app
```bash
streamlit run app.py
```

Open `http://localhost:8501`, enter a query (e.g., “Best practices for mobile tab vs hamburger navigation in 2025”), enable images, and click “Run research”. Optionally click “Evaluate response” to see a quality score and critique.

---

## Notes
- Typical query time: 80-100 seconds 
- Authority sources prioritized (W3C, MDN, NN/g, etc.)

For a deeper dive, see `docs/ARCHITECTURE.md` and `examples/README.md`.
