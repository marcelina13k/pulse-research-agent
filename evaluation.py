# evaluation.py
# Takes the completed brief JSON from synthesis and scores it
# against the 8-dimension quality rubric from the spec.
# Returns a scores object with per-dimension ratings and
# hard-fail flags. This is also what you run against your
# benchmark set during iteration.

import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()


# The 3 dimensions where a score below 3 fails the entire brief
HARD_FAIL_DIMENSIONS = [
    "signal_quality",
    "uncertainty_handling",
    "source_transparency"
]


def build_eval_prompt(brief: dict) -> str:
    """
    Builds the evaluation prompt. The evaluator Claude call
    receives the full brief and the rubric and returns scores.
    """
    brief_text = json.dumps(brief, indent=2)

    return f"""You are a senior research quality analyst evaluating a market trend intelligence brief.

Score the following brief on each of the 8 dimensions below using a 1-5 scale.
Be critical and honest — a score of 5 should be genuinely hard to earn.

SCORING RUBRIC:

1. scope_and_focus (1-5)
   5: Clear domain, geography, horizon. Trends are coherent and non-overlapping.
   3: Domain defined but some overlap or gaps between trends.
   1: Vague scope with random topics.

2. signal_quality (1-5) *** HARD FAIL IF BELOW 3 ***
   5: Every trend backed by 2+ independent signal types with explicit sourcing.
   3: Some data but mostly one-dimensional or unstructured.
   1: Purely anecdotal — news fragments presented as trends.

3. structure_and_readability (1-5)
   5: All 10 mini-structure subsections present and consistently populated.
   3: Basic sections present but inconsistent across trends.
   1: No consistent structure.

4. uncertainty_handling (1-5) *** HARD FAIL IF BELOW 3 ***
   5: Explicit counter-signals, conviction levels, and scenario ranges for every trend.
   3: Mentions risks qualitatively but no conviction levels.
   1: Only upside presented; ignores conflicting data.

5. actionability (1-5)
   5: Concrete implications by audience with specific suggested actions.
   3: Some generic implications with minimal guidance.
   1: No practical implications.

6. source_transparency (1-5) *** HARD FAIL IF BELOW 3 ***
   5: Every quantitative claim has a traceable source; per-trend source list present.
   3: Some references but inconsistent.
   1: No sources.

7. depth (1-5)
   5: All 10 per-trend subsections fully populated with substance.
   3: Most subsections present but some thin.
   1: Multiple subsections missing.

8. original_synthesis (1-5)
   5: Connects non-obvious dots; cross-trend section adds genuine insight beyond individual trends.
   3: Mostly restates known themes but organized clearly.
   1: Simply rephrases headlines.

BRIEF TO EVALUATE:
{brief_text}

Return valid JSON only, no preamble, in exactly this format:
{{
  "scores": {{
    "scope_and_focus": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "signal_quality": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "structure_and_readability": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "uncertainty_handling": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "actionability": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "source_transparency": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "depth": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }},
    "original_synthesis": {{
      "score": 1-5,
      "reasoning": "one sentence explaining this score"
    }}
  }},
  "overall_score": "average of all 8 scores rounded to 1 decimal",
  "hard_fail_triggered": true or false,
  "hard_fail_dimensions": ["list any hard-fail dimensions that scored below 3"],
  "top_strength": "the single strongest aspect of this brief in one sentence",
  "top_improvement": "the single most important thing to improve in one sentence"
}}"""


def evaluate_brief(brief: dict) -> dict:
    """
    Runs the evaluation Claude call and returns the scores object.
    """
    print("\nRunning evaluation...")

    prompt = build_eval_prompt(brief)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text

    try:
        scores = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end != 0:
            scores = json.loads(raw[start:end])
        else:
            raise ValueError(f"Evaluator returned invalid JSON: {raw[:300]}")

    return scores


def print_eval_results(scores: dict):
    """
    Prints evaluation results in a readable format.
    """
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    score_data = scores.get("scores", {})

    for dimension, data in score_data.items():
        score = data.get("score", "N/A")
        reasoning = data.get("reasoning", "")
        is_hard_fail = dimension in HARD_FAIL_DIMENSIONS
        hard_fail_marker = " ***" if is_hard_fail else ""
        status = ""
        if is_hard_fail and isinstance(score, int) and score < 3:
            status = " HARD FAIL"

        print(f"\n  {dimension.replace('_', ' ').upper()}{hard_fail_marker}: {score}/5{status}")
        print(f"  {reasoning}")

    print(f"\n  OVERALL SCORE: {scores.get('overall_score', 'N/A')}/5")

    if scores.get("hard_fail_triggered"):
        print(f"\n  BRIEF STATUS: FAILED")
        print(f"  Failed dimensions: {', '.join(scores.get('hard_fail_dimensions', []))}")
    else:
        print(f"\n  BRIEF STATUS: PASSED")

    print(f"\n  Top strength: {scores.get('top_strength', '')}")
    print(f"  Top improvement: {scores.get('top_improvement', '')}")


if __name__ == "__main__":
    from input_handler import validate_input
    from query_decomposition import decompose_query
    from retrieval import retrieve_evidence
    from credibility_filter import run_credibility_filter
    from synthesis import run_synthesis

    query = validate_input(
        topic="AI adoption in healthcare diagnostics",
        audience="investor",
        geography="north america",
        time_horizon="12 months"
    )

    print("Running full pipeline...")
    plan = decompose_query(query)
    evidence = retrieve_evidence(plan)
    filtered, diversity = run_credibility_filter(evidence)

    if not diversity["meets_minimum"]:
        print("Insufficient signal diversity")
        exit(1)

    brief = run_synthesis(query, filtered)
    scores = evaluate_brief(brief)
    print_eval_results(scores)

    # Attach scores to brief for logging
    brief["evaluation"] = scores
    print("\nEvaluation complete. Brief ready for output formatter.")