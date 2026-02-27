# app.py
# Streamlit interface for Pulse.
# Provides the input form, live progress display,
# and rendered brief output in one page.

import streamlit as st
import json
from datetime import datetime

from input_handler import validate_input, VALID_AUDIENCES, VALID_GEOGRAPHIES, VALID_TIME_HORIZONS
from query_decomposition import decompose_query
from retrieval import retrieve_evidence
from credibility_filter import run_credibility_filter
from synthesis import run_synthesis
from evaluation import evaluate_brief
from output_formatter import format_brief_as_markdown, save_brief

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Pulse — Trend Intelligence",
    page_icon="◎",
    layout="wide"
)

# ── Header ────────────────────────────────────────────────
st.title("◎ Pulse")
st.caption("Market & Trend Intelligence Agent")
st.divider()

# ── Input form ────────────────────────────────────────────
with st.form("query_form"):
    st.subheader("Research Parameters")

    topic = st.text_input(
        "Topic or market to research",
        placeholder="e.g. AI adoption in healthcare diagnostics",
        help="Be specific. The more focused your topic, the higher signal quality."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        audience = st.selectbox(
            "Your audience",
            options=VALID_AUDIENCES,
            help="Strategic implications will be tailored to this audience."
        )

    with col2:
        geography = st.selectbox(
            "Geography",
            options=VALID_GEOGRAPHIES
        )

    with col3:
        time_horizon = st.selectbox(
            "Time horizon",
            options=VALID_TIME_HORIZONS,
            index=1  # default to 12 months
        )

    submitted = st.form_submit_button(
        "Generate Brief",
        type="primary",
        use_container_width=True
    )

# ── Pipeline execution ────────────────────────────────────
if submitted:
    if not topic.strip():
        st.error("Please enter a topic to research.")
        st.stop()

    # Validate input
    try:
        query = validate_input(topic, audience, geography, time_horizon)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.divider()

    # Progress container — shows live updates as pipeline runs
    progress_container = st.container()

    with progress_container:
        st.subheader("Generating brief...")

        # Step indicators
        step1 = st.status("Step 1: Decomposing query into research sub-questions...", expanded=False)
        step2 = st.status("Step 2: Retrieving evidence from web sources...", expanded=False)
        step3 = st.status("Step 3: Filtering and scoring evidence...", expanded=False)
        step4 = st.status("Step 4: Running synthesis — 3 Claude API calls...", expanded=False)
        step5 = st.status("Step 5: Evaluating brief quality...", expanded=False)

        brief = None
        error_occurred = False

        # Step 1 — Query decomposition
        with step1:
            try:
                plan = decompose_query(query)
                sub_q_count = len(plan.get("sub_questions", []))
                st.write(f"Generated {sub_q_count} research sub-questions")
                for sq in plan.get("sub_questions", []):
                    st.write(f"- **{sq['signal_type']}**: {sq['question'][:80]}...")
                step1.update(
                    label=f"Step 1: Query decomposed into {sub_q_count} sub-questions ✓",
                    state="complete"
                )
            except Exception as e:
                step1.update(label=f"Step 1: Failed — {str(e)}", state="error")
                error_occurred = True

        # Step 2 — Retrieval
        if not error_occurred:
            with step2:
                try:
                    evidence = retrieve_evidence(plan)
                    st.write(f"Retrieved {len(evidence)} results from Tavily")
                    step2.update(
                        label=f"Step 2: Retrieved {len(evidence)} evidence items ✓",
                        state="complete"
                    )
                except Exception as e:
                    step2.update(label=f"Step 2: Failed — {str(e)}", state="error")
                    error_occurred = True

        # Step 3 — Credibility filter
        if not error_occurred:
            with step3:
                try:
                    filtered, diversity = run_credibility_filter(evidence)
                    st.write(f"Kept {len(filtered)} results after credibility filtering")
                    st.write(f"Signal types covered: {', '.join(diversity['signals_with_coverage'].keys())}")

                    if not diversity["meets_minimum"]:
                        step3.update(
                            label="Step 3: Failed — insufficient signal diversity",
                            state="error"
                        )
                        st.error(
                            "Not enough distinct signal types found to generate a reliable brief. "
                            "Try a more specific topic or broader time horizon."
                        )
                        error_occurred = True
                    else:
                        step3.update(
                            label=f"Step 3: {len(filtered)} results across {diversity['distinct_signal_types']} signal types ✓",
                            state="complete"
                        )
                except Exception as e:
                    step3.update(label=f"Step 3: Failed — {str(e)}", state="error")
                    error_occurred = True

        # Step 4 — Synthesis
        if not error_occurred:
            with step4:
                try:
                    st.write("Pass 1: Identifying trend candidates...")
                    brief = run_synthesis(query, filtered)
                    trend_count = len(brief.get("trends", []))
                    st.write(f"Pass 2: Populated {trend_count} trend deep-dives")
                    st.write("Pass 3: Cross-trend synthesis complete")
                    step4.update(
                        label=f"Step 4: Synthesized {trend_count} trends ✓",
                        state="complete"
                    )
                except Exception as e:
                    step4.update(label=f"Step 4: Failed — {str(e)}", state="error")
                    error_occurred = True

        # Step 5 — Evaluation
        if not error_occurred and brief:
            with step5:
                try:
                    scores = evaluate_brief(brief)
                    overall = scores.get("overall_score", "N/A")
                    status = "PASSED" if not scores.get("hard_fail_triggered") else "FAILED"
                    st.write(f"Overall score: {overall}/5")
                    st.write(f"Status: {status}")
                    brief["evaluation"] = scores
                    step5.update(
                        label=f"Step 5: Quality score {overall}/5 — {status} ✓",
                        state="complete"
                    )
                except Exception as e:
                    step5.update(label=f"Step 5: Failed — {str(e)}", state="error")
                    error_occurred = True

    # ── Output ────────────────────────────────────────────
    if brief and not error_occurred:
        st.divider()

        # Save brief to logs
        md_path = save_brief(brief)

        # Summary metrics row
        trends = brief.get("trends", [])
        evaluation = brief.get("evaluation", {})
        overall_score = evaluation.get("overall_score", "N/A")
        status = "PASSED" if not evaluation.get("hard_fail_triggered") else "FAILED"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Trends identified", len(trends))
        m2.metric("Evidence items", len(filtered))
        m3.metric("Quality score", f"{overall_score}/5")
        m4.metric("Brief status", status)

        st.divider()

        # Tabs — Brief and Raw JSON
        tab1, tab2, tab3 = st.tabs(["Brief", "Evaluation Scorecard", "Raw JSON"])

        with tab1:
            markdown = format_brief_as_markdown(brief)
            st.markdown(markdown)

            # Download button
            st.download_button(
                label="Download brief as markdown",
                data=markdown,
                file_name=f"pulse_brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )

        with tab2:
            scores_data = evaluation.get("scores", {})
            for dimension, data in scores_data.items():
                score = data.get("score", 0)
                reasoning = data.get("reasoning", "")
                col_a, col_b = st.columns([1, 4])
                with col_a:
                    # Color code the score
                    if score >= 4:
                        st.success(f"{score}/5")
                    elif score == 3:
                        st.warning(f"{score}/5")
                    else:
                        st.error(f"{score}/5")
                with col_b:
                    st.write(f"**{dimension.replace('_', ' ').title()}**")
                    st.caption(reasoning)

            st.divider()
            st.write(f"**Overall: {overall_score}/5 — {status}**")

            if evaluation.get("top_strength"):
                st.success(f"Top strength: {evaluation['top_strength']}")
            if evaluation.get("top_improvement"):
                st.info(f"Top improvement: {evaluation['top_improvement']}")

        with tab3:
            st.json(brief)