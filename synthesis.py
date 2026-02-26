# synthesis.py
# The core reasoning layer. Takes filtered, tagged evidence and
# runs three sequential Claude API calls to produce the full
# structured brief. Each pass builds on the output of the last.
#
# Pass 1: Identify 3-5 trend candidates from evidence
# Pass 2: Populate all 10 mini-structure subsections per trend
# Pass 3: Write executive summary, cross-trend synthesis, scenarios

import json
import anthropic
from dotenv import load_dotenv
from input_handler import QueryObject, format_query_for_prompt

load_dotenv()
client = anthropic.Anthropic()


def format_evidence_for_prompt(evidence: list[dict]) -> str:
    """
    Converts the evidence list into a formatted string for
    injection into Claude prompts. Groups by signal type so
    Claude can see the evidence landscape clearly.
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in evidence:
        grouped[item["signal_type"]].append(item)

    output = []
    for signal_type, items in grouped.items():
        output.append(f"\n--- {signal_type.upper()} SIGNALS ---")
        for item in items:
            output.append(f"Title: {item['title']}")
            output.append(f"Source: {item['source']} (credibility: {item.get('credibility_score', 'N/A')}/10)")
            output.append(f"Date: {item.get('published_date', 'unknown')}")
            output.append(f"Excerpt: {item['excerpt'][:300]}")
            output.append(f"URL: {item['url']}")
            output.append("")

    return "\n".join(output)


# ─────────────────────────────────────────────────────────
# PASS 1: Trend Identification
# ─────────────────────────────────────────────────────────

def pass_1_identify_trends(
    query: QueryObject,
    evidence: list[dict]
) -> dict:
    """
    Pass 1: Claude reads all the evidence and identifies
    3-5 distinct trend candidates. Each candidate gets a
    one-line thesis and a list of supporting evidence IDs.
    Output feeds directly into Pass 2.
    """
    print("\n  Running Pass 1: Trend Identification...")

    evidence_text = format_evidence_for_prompt(evidence)

    prompt = f"""You are a senior market analyst writing a trend intelligence brief.

RESEARCH PARAMETERS:
{format_query_for_prompt(query)}

EVIDENCE CORPUS:
{evidence_text}

TASK:
Analyze the evidence above and identify exactly 3-5 distinct, meaningful trends.

REQUIREMENTS:
- Each trend must be supported by evidence from at least 2 different signal types
- Each trend must be specific and defensible — not vague ("AI is growing")
- Trends must be distinct from each other — no overlap
- Include both positive trends AND headwinds/challenges if the evidence supports them
- A trend must have real evidence behind it — do not invent trends not supported above

Return valid JSON only, no preamble, in exactly this format:
{{
  "trend_candidates": [
    {{
      "id": "trend_1",
      "name": "short trend name (5 words max)",
      "thesis": "one declarative sentence stating what is happening and why it matters",
      "primary_signal_types": ["signal_type_1", "signal_type_2"],
      "supporting_evidence_titles": ["title of evidence 1", "title of evidence 2"],
      "maturity": "weak signal OR emerging OR established",
      "initial_conviction": "low OR medium OR high"
    }}
  ]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text
    return _parse_json(raw, "Pass 1")


# ─────────────────────────────────────────────────────────
# PASS 2: Deep-Dive Population
# ─────────────────────────────────────────────────────────

def pass_2_populate_trends(
    query: QueryObject,
    evidence: list[dict],
    trend_candidates: dict
) -> dict:
    """
    Pass 2: Populates each trend one at a time to avoid
    hitting token limits. Assembles results into a single
    trends list at the end.
    """
    print("  Running Pass 2: Deep-Dive Population...")

    evidence_text = format_evidence_for_prompt(evidence)
    all_trends = []

    candidates = trend_candidates.get("trend_candidates", [])

    for i, candidate in enumerate(candidates, 1):
        print(f"    Populating trend {i}/{len(candidates)}: {candidate['name']}")

        candidate_text = json.dumps(candidate, indent=2)

        prompt = f"""You are a senior market analyst writing a trend intelligence brief.

RESEARCH PARAMETERS:
{format_query_for_prompt(query)}

TREND TO POPULATE:
{candidate_text}

EVIDENCE CORPUS:
{evidence_text}

TASK:
Populate all 10 required subsections for this single trend using the evidence provided.
Every claim must be grounded in the evidence above — do not fabricate data or statistics.
If evidence for a subsection is thin, say so explicitly rather than inventing content.

Return valid JSON only, no preamble, in exactly this format:
{{
  "id": "{candidate['id']}",
  "name": "{candidate['name']}",
  "thesis": "one declarative sentence",
  "definition_and_scope": "1-2 paragraphs defining what counts as this trend and what does not",
  "why_now": [
    "specific structural driver 1 — what has changed",
    "specific structural driver 2 — what has changed"
  ],
  "evidence_and_signals": {{
    "quantitative": ["specific data point with source", "specific data point with source"],
    "qualitative": ["specific development with source", "specific development with source"]
  }},
  "counter_signals": [
    "specific headwind or contradictory data point 1",
    "specific headwind or contradictory data point 2"
  ],
  "conviction_level": "low OR medium OR high",
  "conviction_reasoning": "one sentence explaining the conviction rating",
  "timeframe_and_maturity": {{
    "current_stage": "weak signal OR emerging OR established",
    "estimated_impact_timeframe": "e.g. 12-18 months to mainstream adoption in X segment",
    "next_stage_milestones": ["what would need to happen to advance maturity"]
  }},
  "key_players": {{
    "incumbents": ["company or institution name"],
    "startups": ["company name"],
    "infrastructure": ["company or platform name"]
  }},
  "strategic_implications": "1-3 paragraphs tailored specifically to the audience: {query.audience}",
  "watch_metrics": [
    "specific measurable indicator 1",
    "specific measurable indicator 2",
    "specific measurable indicator 3"
  ],
  "sources": [
    {{
      "title": "source title",
      "url": "source url",
      "type": "primary data OR company disclosure OR press/article OR expert commentary"
    }}
  ]
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text
        trend = _parse_json(raw, f"Pass 2 trend {i}")
        all_trends.append(trend)

    return {"trends": all_trends}


# ─────────────────────────────────────────────────────────
# PASS 3: Cross-Trend Synthesis
# ─────────────────────────────────────────────────────────

def pass_3_synthesize(
    query: QueryObject,
    populated_trends: dict
) -> dict:
    """
    Pass 3: Claude takes all the populated trend objects and
    writes the executive summary, cross-trend synthesis, and
    scenarios. This is the final assembly step.
    """
    print("  Running Pass 3: Cross-Trend Synthesis...")

    trends_text = json.dumps(populated_trends, indent=2)

    prompt = f"""You are a senior market analyst completing a trend intelligence brief.

RESEARCH PARAMETERS:
{format_query_for_prompt(query)}

FULLY POPULATED TREND SECTIONS:
{trends_text}

TASK:
Write the three synthesizing sections of the brief that sit above and across the individual trends.

Return valid JSON only, no preamble, in exactly this format:
{{
  "executive_summary": {{
    "overview_paragraph": "2-3 sentences summarizing the overall trend landscape for this topic",
    "trend_snapshots": [
      {{
        "name": "trend name",
        "thesis": "one sentence",
        "maturity": "weak signal OR emerging OR established",
        "conviction": "low OR medium OR high",
        "timeframe": "estimated timeframe"
      }}
    ],
    "cross_cutting_theme": "one paragraph on the overarching theme connecting these trends"
  }},
  "cross_trend_synthesis": {{
    "how_trends_interact": "one paragraph explaining how the identified trends reinforce or tension against each other",
    "scenarios": [
      {{
        "type": "conservative",
        "description": "what the landscape looks like if trends develop slower than expected"
      }},
      {{
        "type": "base",
        "description": "most likely outcome given current evidence"
      }},
      {{
        "type": "aggressive",
        "description": "what the landscape looks like if trends accelerate"
      }}
    ]
  }},
  "methodology": {{
    "sources_used": ["Tavily web search", "NewsAPI"],
    "signal_types_covered": ["list the signal types that had coverage"],
    "limitations": ["any notable gaps in the evidence or caveats about data quality"]
  }}
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text
    return _parse_json(raw, "Pass 3")


# ─────────────────────────────────────────────────────────
# MAIN SYNTHESIS FUNCTION
# ─────────────────────────────────────────────────────────

def run_synthesis(
    query: QueryObject,
    filtered_evidence: list[dict]
) -> dict:
    """
    Orchestrates all three passes and assembles the complete
    brief JSON. This is what gets passed to the evaluation layer.
    """
    print("\nStarting synthesis — 3 sequential Claude API calls...")

    # Pass 1 — identify trends
    candidates = pass_1_identify_trends(query, filtered_evidence)
    print(f"  Found {len(candidates.get('trend_candidates', []))} trend candidates")

    # Pass 2 — populate each trend (passes candidates as context)
    populated = pass_2_populate_trends(query, filtered_evidence, candidates)
    print(f"  Populated {len(populated.get('trends', []))} trend deep-dives")

    # Pass 3 — synthesize across trends (passes populated trends as context)
    synthesis = pass_3_synthesize(query, populated)
    print("  Cross-trend synthesis complete")

    # Assemble the complete brief
    complete_brief = {
        "query": {
            "topic": query.topic,
            "audience": query.audience,
            "geography": query.geography,
            "time_horizon": query.time_horizon
        },
        "executive_summary": synthesis.get("executive_summary", {}),
        "methodology": synthesis.get("methodology", {}),
        "trends": populated.get("trends", []),
        "cross_trend_synthesis": synthesis.get("cross_trend_synthesis", {}),
    }

    return complete_brief


def _parse_json(raw: str, pass_name: str) -> dict:
    """
    Safely parses JSON from Claude's response.
    Handles cases where Claude adds preamble despite instructions.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end != 0:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"{pass_name} returned invalid JSON. Raw response:\n{raw[:500]}")


if __name__ == "__main__":
    from input_handler import validate_input
    from query_decomposition import decompose_query
    from retrieval import retrieve_evidence
    from credibility_filter import run_credibility_filter

    query = validate_input(
        topic="AI adoption in healthcare diagnostics",
        audience="investor",
        geography="north america",
        time_horizon="12 months"
    )

    print("Decomposing query...")
    plan = decompose_query(query)

    print("Retrieving evidence...")
    evidence = retrieve_evidence(plan)

    print("Filtering evidence...")
    filtered, diversity = run_credibility_filter(evidence)

    if not diversity["meets_minimum"]:
        print("Not enough signal diversity — cannot synthesize")
        exit(1)

    # Run synthesis
    brief = run_synthesis(query, filtered)

    # Print a preview of the output
    print("\n" + "=" * 60)
    print("BRIEF PREVIEW")
    print("=" * 60)

    exec_summary = brief.get("executive_summary", {})
    print(f"\nOverview: {exec_summary.get('overview_paragraph', '')}")

    print(f"\nTrends identified: {len(brief.get('trends', []))}")
    for trend in brief.get("trends", []):
        print(f"\n  {trend['name']}")
        print(f"  Thesis: {trend['thesis']}")
        print(f"  Maturity: {trend.get('timeframe_and_maturity', {}).get('current_stage', 'N/A')}")
        print(f"  Conviction: {trend.get('conviction_level', 'N/A')}")

    print("\nSynthesis complete. Full brief JSON ready for evaluation layer.")