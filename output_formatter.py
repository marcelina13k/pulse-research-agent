# output_formatter.py
# Takes the complete brief JSON (with evaluation scores attached)
# and renders it as a clean, readable markdown document.
# This is what the user actually reads — everything before this
# has been pipeline infrastructure.

import json
from datetime import datetime
from pathlib import Path


def format_brief_as_markdown(brief: dict) -> str:
    """
    Converts the structured brief JSON into a formatted
    markdown document following the spec's section order.
    """
    lines = []
    query = brief.get("query", {})
    exec_summary = brief.get("executive_summary", {})
    methodology = brief.get("methodology", {})
    trends = brief.get("trends", [])
    synthesis = brief.get("cross_trend_synthesis", {})
    evaluation = brief.get("evaluation", {})

    # ── Cover & Metadata ──────────────────────────────────
    lines.append("# PULSE — Market & Trend Intelligence Brief")
    lines.append("")
    lines.append(f"**Topic:** {query.get('topic', '')}")
    lines.append(f"**Audience:** {query.get('audience', '').title()}")
    lines.append(f"**Geography:** {query.get('geography', '').title()}")
    lines.append(f"**Time Horizon:** {query.get('time_horizon', '')}")
    lines.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Executive Summary ─────────────────────────────────
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(exec_summary.get("overview_paragraph", ""))
    lines.append("")

    # Trend snapshot table
    snapshots = exec_summary.get("trend_snapshots", [])
    if snapshots:
        lines.append("### Trend Snapshot")
        lines.append("")
        lines.append("| Trend | Thesis | Maturity | Conviction | Timeframe |")
        lines.append("|-------|--------|----------|------------|-----------|")
        for snap in snapshots:
            lines.append(
                f"| {snap.get('name', '')} "
                f"| {snap.get('thesis', '')} "
                f"| {snap.get('maturity', '')} "
                f"| {snap.get('conviction', '')} "
                f"| {snap.get('timeframe', '')} |"
            )
        lines.append("")

    cross_cutting = exec_summary.get("cross_cutting_theme", "")
    if cross_cutting:
        lines.append(f"**Cross-cutting theme:** {cross_cutting}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # ── Methodology ───────────────────────────────────────
    lines.append("## Methodology & Signals Used")
    lines.append("")
    sources = methodology.get("sources_used", [])
    if sources:
        lines.append(f"**Sources:** {', '.join(sources)}")
        lines.append("")
    signal_types = methodology.get("signal_types_covered", [])
    if signal_types:
        lines.append(f"**Signal types:** {', '.join(signal_types)}")
        lines.append("")
    limitations = methodology.get("limitations", [])
    if limitations:
        lines.append("**Limitations:**")
        for lim in limitations:
            lines.append(f"- {lim}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # ── Trend Overview Table ──────────────────────────────
    lines.append("## Trend Overview")
    lines.append("")
    lines.append("| # | Trend | Maturity | Conviction | Primary Driver | Strategic Note |")
    lines.append("|---|-------|----------|------------|----------------|----------------|")
    for i, trend in enumerate(trends, 1):
        maturity = trend.get("timeframe_and_maturity", {}).get("current_stage", "")
        why_now = trend.get("why_now", [""])
        primary_driver = why_now[0][:60] + "..." if why_now and len(why_now[0]) > 60 else (why_now[0] if why_now else "")
        lines.append(
            f"| {i} "
            f"| {trend.get('name', '')} "
            f"| {maturity} "
            f"| {trend.get('conviction_level', '')} "
            f"| {primary_driver} "
            f"| — |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Per-Trend Deep Dives ──────────────────────────────
    lines.append("## Trend Deep Dives")
    lines.append("")

    for i, trend in enumerate(trends, 1):
        lines.append(f"### {i}. {trend.get('name', '')}")
        lines.append("")
        lines.append(f"> {trend.get('thesis', '')}")
        lines.append("")

        # Definition & scope
        lines.append("**Definition & Scope**")
        lines.append("")
        lines.append(trend.get("definition_and_scope", ""))
        lines.append("")

        # Why now
        why_now = trend.get("why_now", [])
        if why_now:
            lines.append("**Why Now**")
            lines.append("")
            for driver in why_now:
                lines.append(f"- {driver}")
            lines.append("")

        # Evidence & signals
        evidence = trend.get("evidence_and_signals", {})
        lines.append("**Evidence & Signals**")
        lines.append("")
        quant = evidence.get("quantitative", [])
        if quant:
            lines.append("*Quantitative:*")
            for item in quant:
                lines.append(f"- {item}")
            lines.append("")
        qual = evidence.get("qualitative", [])
        if qual:
            lines.append("*Qualitative:*")
            for item in qual:
                lines.append(f"- {item}")
            lines.append("")

        # Counter-signals
        counter = trend.get("counter_signals", [])
        if counter:
            lines.append("**Counter-Signals & Risks**")
            lines.append("")
            for item in counter:
                lines.append(f"- {item}")
            lines.append("")

        # Conviction
        lines.append(
            f"**Conviction:** {trend.get('conviction_level', '').upper()} — "
            f"{trend.get('conviction_reasoning', '')}"
        )
        lines.append("")

        # Timeframe & maturity
        tfm = trend.get("timeframe_and_maturity", {})
        lines.append("**Timeframe & Maturity**")
        lines.append("")
        lines.append(f"- Current stage: {tfm.get('current_stage', '')}")
        lines.append(f"- Estimated impact: {tfm.get('estimated_impact_timeframe', '')}")
        milestones = tfm.get("next_stage_milestones", [])
        if milestones:
            lines.append("- Next stage requires:")
            for m in milestones:
                lines.append(f"  - {m}")
        lines.append("")

        # Key players
        players = trend.get("key_players", {})
        lines.append("**Key Players**")
        lines.append("")
        incumbents = players.get("incumbents", [])
        startups = players.get("startups", [])
        infrastructure = players.get("infrastructure", [])
        if incumbents:
            lines.append(f"- Incumbents: {', '.join(incumbents)}")
        if startups:
            lines.append(f"- Startups: {', '.join(startups)}")
        if infrastructure:
            lines.append(f"- Infrastructure: {', '.join(infrastructure)}")
        lines.append("")

        # Strategic implications
        lines.append("**Strategic Implications**")
        lines.append("")
        lines.append(trend.get("strategic_implications", ""))
        lines.append("")

        # Watch metrics
        metrics = trend.get("watch_metrics", [])
        if metrics:
            lines.append("**Watch Metrics**")
            lines.append("")
            for metric in metrics:
                lines.append(f"- {metric}")
            lines.append("")

        # Sources
        sources = trend.get("sources", [])
        if sources:
            lines.append("**Sources**")
            lines.append("")
            for source in sources:
                source_type = source.get("type", "")
                title = source.get("title", "")
                url = source.get("url", "")
                lines.append(f"- [{title}]({url}) — *{source_type}*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # ── Cross-Trend Synthesis ─────────────────────────────
    lines.append("## Cross-Trend Synthesis")
    lines.append("")
    lines.append(synthesis.get("how_trends_interact", ""))
    lines.append("")

    scenarios = synthesis.get("scenarios", [])
    if scenarios:
        lines.append("### Scenarios")
        lines.append("")
        for scenario in scenarios:
            lines.append(f"**{scenario.get('type', '').title()}**")
            lines.append("")
            lines.append(scenario.get("description", ""))
            lines.append("")

    lines.append("---")
    lines.append("")

    # ── Evaluation Scorecard ──────────────────────────────
    if evaluation:
        lines.append("## Quality Scorecard")
        lines.append("")
        scores = evaluation.get("scores", {})
        lines.append("| Dimension | Score | Notes |")
        lines.append("|-----------|-------|-------|")
        for dim, data in scores.items():
            score = data.get("score", "")
            reasoning = data.get("reasoning", "")
            lines.append(f"| {dim.replace('_', ' ').title()} | {score}/5 | {reasoning} |")
        lines.append("")
        lines.append(f"**Overall: {evaluation.get('overall_score', '')}/5**")
        lines.append("")
        status = "PASSED" if not evaluation.get("hard_fail_triggered") else "FAILED"
        lines.append(f"**Status: {status}**")
        lines.append("")

    return "\n".join(lines)


def save_brief(brief: dict, output_dir: str = "logs") -> str:
    """
    Saves both the raw JSON and the rendered markdown brief
    to the logs folder. Returns the path to the markdown file.
    """
    Path(output_dir).mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_slug = brief.get("query", {}).get("topic", "brief").replace(" ", "_")[:30]
    base_name = f"{timestamp}_{topic_slug}"

    # Save raw JSON
    json_path = f"{output_dir}/{base_name}.json"
    with open(json_path, "w") as f:
        json.dump(brief, f, indent=2)

    # Save rendered markdown
    md_path = f"{output_dir}/{base_name}.md"
    markdown = format_brief_as_markdown(brief)
    with open(md_path, "w") as f:
        f.write(markdown)

    print(f"\nBrief saved:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")

    return md_path


if __name__ == "__main__":
    from input_handler import validate_input
    from query_decomposition import decompose_query
    from retrieval import retrieve_evidence
    from credibility_filter import run_credibility_filter
    from synthesis import run_synthesis
    from evaluation import evaluate_brief, print_eval_results

    query = validate_input(
        topic="electric vehicle battery technology",
        audience="general",
        geography="global",
        time_horizon="12 months"
    )

    print("Running full pipeline...")
    plan = decompose_query(query)
    evidence = retrieve_evidence(plan)
    filtered, diversity = run_credibility_filter(evidence)

    if not diversity["meets_minimum"]:
        print("Insufficient signal diversity — cannot generate brief")
        exit(1)

    brief = run_synthesis(query, filtered)
    scores = evaluate_brief(brief)
    print_eval_results(scores)

    brief["evaluation"] = scores

    # Save and render
    md_path = save_brief(brief)

    # Print the full markdown to terminal so you can see it
    print("\n" + "=" * 60)
    print("RENDERED BRIEF")
    print("=" * 60)
    markdown = format_brief_as_markdown(brief)
    print(markdown)