### The Full System — 6 Components
1. Input Handler
The entry point. Accepts a topic string plus optional parameters: audience type (founder / investor / product team / analyst), geography (default: global), time horizon (default: 12-24 months). Validates input and constructs a structured query object that gets passed downstream. This is also where you'd eventually add a Streamlit UI form.

2. Query Decomposition Layer
Takes the structured query object and uses Claude to break it into 4-6 focused research sub-questions. For a topic like "AI in healthcare diagnostics," this produces sub-questions like: what is the current funding activity, what products have launched in the last 12 months, what are practitioners saying, what regulatory moves are happening, what are the technical bottlenecks. Each sub-question maps to a specific signal type. This decomposition is what makes the retrieval targeted rather than just throwing the raw topic at a search API.

3. Multi-Source Retrieval Layer
This is the most complex component. For each sub-question, the agent runs parallel searches across multiple tools:
- Tavily API — purpose-built for AI agents, returns clean structured results with source metadata, free tier available
- NewsAPI — recent news articles with date filtering, free tier availabl
- Reddit API (PRAW) — community signal, practitioner sentiment, early adoption discussion

Each tool returns results as structured objects: title, URL, date, source type, excerpt. A credibility filter runs after retrieval — downweighting low-quality sources, filtering results older than your time horizon, and tagging each result by signal type (funding / product launch / regulatory / adoption / sentiment). Results that don't meet the 2-signal-type minimum per trend candidate get flagged.

4. Synthesis & Reasoning Layer
The core Claude prompt. Takes all retrieved, filtered, tagged evidence and reasons across it to produce the structured brief. This is not one big prompt — it's sequenced. First pass: identify 3-5 trend candidates from the evidence. Second pass: for each candidate, populate all 10 mini-structure subsections. Third pass: write the cross-trend synthesis and scenarios. Each pass is a separate Claude call with the output of the previous pass included as context. This sequencing is important — one giant prompt produces worse output than structured stepwise reasoning.

5. Evaluation Layer
After synthesis, a separate Claude call acts as the evaluator. It receives the completed brief and scores it against your 8-dimension rubric, returning a JSON object with a score per dimension and brief reasoning for each score. Any hard-fail dimension (signal quality, uncertainty handling, source transparency) below 3 triggers a flag. You log the scores alongside the brief. This is what you run against your 10-query benchmark set during iteration.

6. Output Formatter & Interface
Takes the structured JSON output from synthesis and renders it into a clean markdown brief. Streamlit provides the UI: input form, live progress display showing which component is running, and the final rendered brief with expandable source citations. Everything gets logged to a local JSON file — input, intermediate outputs, eval scores, timestamp — for your observability layer.

### Data Flow
User Input
    ↓
Input Handler → structured query object
    ↓
Query Decomposition → 4-6 sub-questions with signal type mapping
    ↓
Multi-Source Retrieval → parallel searches across Tavily + NewsAPI + Reddit
    ↓
Credibility Filter → tagged, scored evidence objects
    ↓
Signal Sufficiency Check → drop candidates below 2-signal threshold
    ↓
Synthesis Layer (3 sequential Claude calls) → structured brief JSON
    ↓
Evaluation Layer → rubric scores JSON
    ↓
Output Formatter → rendered markdown brief
    ↓
Streamlit UI + local log file

### Tech Stack

Python — orchestration layer
LangChain — agent framework, tool binding, prompt chaining
Claude API (claude-sonnet) — query decomposition, synthesis, evaluation
Tavily API — primary web search tool
Streamlit — frontend interface
JSON files — local logging and run history (no database needed)


### Key Design Decisions Worth Documenting

1. Why sequential Claude calls instead of one prompt? Single large prompts produce inconsistent structure and the model loses focus across 10 subsections per trend. Breaking into passes — identify candidates, then populate each, then synthesize across — produces more reliable output and makes it easier to debug which step is failing.
2. Why Tavily over raw Google Search API? Tavily is purpose-built for LLM agents — it returns clean structured excerpts with metadata rather than raw HTML, handles deduplication, and has better signal-to-noise for factual research queries. The free tier is sufficient for development.
3. Why Reddit via PRAW? Practitioner communities on Reddit (r/medicine, r/MachineLearning, r/investing, etc.) carry early-adoption signal that doesn't show up in press releases or funding databases for months. It's the qualitative counterweight to the quantitative funding/news signals.
4. Why log everything locally? Observability is the only way to improve the system systematically. Without logs you're guessing what's failing. With logs you can look at a bad output and trace exactly which retrieval step returned low-quality results or which synthesis pass dropped a key piece of evidence.

