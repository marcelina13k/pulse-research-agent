Pulse — Market & Trend Intelligence Agent
Pulse is an autonomous research agent that takes any market or topic as input and produces a structured, sourced trend intelligence brief — the kind a senior analyst would write, generated in under two minutes.
It retrieves live evidence from the web, filters it for credibility, runs three sequential reasoning passes to identify and develop trends, evaluates its own output against a quality rubric, and renders a complete brief with theses, counter-signals, strategic implications, and citations.

What it produces
Each brief contains:

Executive summary with trend snapshots and a cross-cutting thesis
3–5 trend deep-dives, each with definition, drivers, evidence, counter-signals, conviction level, timeframe, key players, strategic implications, watch metrics, and sources
Cross-trend synthesis with conservative, base, and aggressive scenarios
Quality scorecard scored against an 8-dimension rubric derived from CB Insights, a16z, and Sequoia research methodology


How it works
The pipeline runs five sequential components:
> User input
> Query Decomposition    — Claude breaks the topic into 4–6 sub-questions, each mapped to a signal type
> Retrieval              — Tavily searches the web for each sub-question in parallel
> Credibility Filter     — Scores and removes low-quality sources, checks 2-signal-type minimum
> Synthesis              — 3 sequential Claude calls: identify trends → populate deep-dives → cross-trend synthesis
> Evaluation             — Claude scores the brief against the quality rubric
> Output                 — Rendered markdown brief + raw JSON saved to /logs
> A trend is only included if it is supported by at least two independent signal types. Counter-signals are mandatory for every trend. Strategic implications are tailored to the audience specified at input.

Stack

Python — pipeline orchestration
Claude API (claude-sonnet-4-20250514) — query decomposition, synthesis, evaluation
Tavily API — web retrieval, purpose-built for AI agents
Streamlit — browser interface
JSON — local logging of all runs


Setup
1. Clone the repo and create a virtual environment
bash git clone https://github.com/yourname/pulse.git
cd pulse
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
3. Install dependencies
bash pip install anthropic tavily-python requests python-dotenv streamlit
4. Add your API keys
Create a .env file in the project root:
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
Get keys at:

Anthropic: console.anthropic.com
Tavily: tavily.com — free tier, 1000 searches/month

4. Run the app
bash streamlit run app.py
Opens at http://localhost:8501.

Running individual components
Each file can be run directly for testing:
bashpython input_handler.py          # test input validation
python query_decomposition.py    # test Claude decomposition
python retrieval.py              # test Tavily retrieval
python credibility_filter.py     # test filtering and signal check
python synthesis.py              # test full synthesis pipeline
python evaluation.py             # test end-to-end with scoring
python output_formatter.py       # test full pipeline + save brief

Output
Briefs are saved to /logs as both .json (raw structured data) and .md (rendered brief) with a timestamp and topic slug in the filename. The markdown file can be opened in any markdown viewer or imported into Notion, Confluence, or similar tools.

Known limitations

Retrieval is Tavily only. NewsAPI free tier restricts the /everything endpoint to paid plans and was removed. Can be re-added on a paid plan as a secondary source.
Reddit (PRAW) is not currently integrated. Planned for v2 to add practitioner sentiment signal.
Key players sections are sometimes thin on startup names depending on what Tavily surfaces. A Crunchbase or PitchBook integration would improve this.
The credibility domain blocklist is manually maintained. Expanding it improves filter quality.
