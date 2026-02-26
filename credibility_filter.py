# credibility_filter.py
# Takes the raw evidence list from retrieval and does three things:
# 1. Scores each result for source credibility
# 2. Filters out low-quality sources
# 3. Checks that enough signal diversity exists to meet the
#    2-signal-type minimum before passing evidence to synthesis

from collections import defaultdict

# Sources we explicitly downweight — market research aggregators
# that produce SEO content rather than real signal
LOW_CREDIBILITY_DOMAINS = [
    "grandviewresearch.com",
    "fortunebusinessinsights.com",
    "precedenceresearch.com",
    "marketsandmarkets.com",
    "mordorintelligence.com",
    "alliedmarketresearch.com",
    "businessresearchinsights.com",
    "imarcgroup.com",
    "globenewswire.com",  # mostly press releases
    "prnewswire.com",     # press releases
    "businesswire.com",   # press releases
    "metatechinsights.com",
    "cathaycapital.com",
]

# Sources we explicitly upweight — these carry real signal
HIGH_CREDIBILITY_DOMAINS = [
    "nejm.org",
    "nature.com",
    "science.org",
    "thelancet.com",
    "jamanetwork.com",
    "statnews.com",
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "techcrunch.com",
    "fierce healthcare",
    "modernhealthcare.com",
    "healthaffairs.org",
    "fda.gov",
    "cms.gov",
    "nih.gov",
    "crunchbase.com",
    "pitchbook.com",
]


def score_result(result: dict) -> int:
    """
    Scores a single evidence result from 0-10.
    Higher score = more credible and useful.
    Results scoring below 3 get filtered out.
    """
    score = 5  # start at neutral

    source_url = result.get("url", "").lower()
    source_name = result.get("source", "").lower()

    # Check against low credibility domains
    for domain in LOW_CREDIBILITY_DOMAINS:
        if domain in source_url:
            score -= 4
            break

    # Check against high credibility domains
    for domain in HIGH_CREDIBILITY_DOMAINS:
        if domain in source_url or domain in source_name:
            score += 3
            break

    # Reward results that have a publication date
    if result.get("published_date"):
        score += 1

    # Reward results with a meaningful excerpt
    excerpt = result.get("excerpt", "")
    if len(excerpt) > 100:
        score += 1
    if len(excerpt) < 20:
        score -= 2

    # Reward results with a real title
    title = result.get("title", "")
    if len(title) > 10:
        score += 1

    # Cap score between 0 and 10
    return max(0, min(10, score))


def filter_evidence(evidence: list[dict], min_score: int = 3) -> list[dict]:
    """
    Scores all evidence and removes results below the minimum score.
    Returns filtered list with scores attached to each result.
    """
    scored = []
    for result in evidence:
        score = score_result(result)
        result["credibility_score"] = score
        if score >= min_score:
            scored.append(result)

    return scored


def check_signal_diversity(evidence: list[dict]) -> dict:
    """
    Checks how many distinct signal types are present in the
    filtered evidence. Returns a report showing which signal
    types have coverage and whether the 2-signal minimum is met.

    This is the gate before synthesis — if we don't have at least
    2 signal types with evidence, we flag it rather than
    producing a brief with weak foundations.
    """
    signal_counts = defaultdict(int)
    for result in evidence:
        signal_counts[result["signal_type"]] += 1

    signals_with_coverage = {
        signal: count
        for signal, count in signal_counts.items()
        if count > 0
    }

    return {
        "signal_counts": dict(signal_counts),
        "signals_with_coverage": signals_with_coverage,
        "distinct_signal_types": len(signals_with_coverage),
        "meets_minimum": len(signals_with_coverage) >= 2,
        "total_evidence": len(evidence)
    }


def run_credibility_filter(evidence: list[dict]) -> tuple[list[dict], dict]:
    """
    Main filter function. Runs scoring, filtering, and diversity check.
    Returns the filtered evidence list and a diversity report.
    """
    print(f"\nRunning credibility filter on {len(evidence)} results...")

    # Score and filter
    filtered = filter_evidence(evidence)
    removed = len(evidence) - len(filtered)
    print(f"  Removed {removed} low-credibility results")
    print(f"  Kept {len(filtered)} results")

    # Check signal diversity
    diversity = check_signal_diversity(filtered)
    print(f"\nSignal diversity check:")
    for signal, count in diversity["signal_counts"].items():
        status = "OK" if count > 0 else "NO COVERAGE"
        print(f"  {signal}: {count} results — {status}")

    if diversity["meets_minimum"]:
        print(f"\n  PASS: {diversity['distinct_signal_types']} distinct signal types found (minimum 2 required)")
    else:
        print(f"\n  FAIL: Only {diversity['distinct_signal_types']} distinct signal type(s) found — minimum 2 required")
        print("  Brief cannot be generated with sufficient evidence depth")

    return filtered, diversity


if __name__ == "__main__":
    from input_handler import validate_input
    from query_decomposition import decompose_query
    from retrieval import retrieve_evidence

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

    # Run the filter
    filtered_evidence, diversity_report = run_credibility_filter(evidence)

    # Show what survived filtering
    print("\nSample filtered evidence (first 3):")
    print("-" * 60)
    for item in filtered_evidence[:3]:
        print(f"\nTitle:   {item['title']}")
        print(f"Source:  {item['source']}")
        print(f"Signal:  {item['signal_type']}")
        print(f"Score:   {item['credibility_score']}/10")
        print(f"Excerpt: {item['excerpt'][:150]}...")