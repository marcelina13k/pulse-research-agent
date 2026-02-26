# query_decomposition.py
# Takes the QueryObject from input_handler and uses Claude to break
# the topic into 4-6 focused research sub-questions, each mapped
# to a specific signal type. The output is a structured research
# plan that tells the retrieval layer exactly what to look for.

import json
import anthropic
import os
from dotenv import load_dotenv
from input_handler import QueryObject, format_query_for_prompt

load_dotenv()

# Instantiate the Anthropic client once at the module level.
client = anthropic.Anthropic()

# These are the valid signal types from our spec.
# Every sub-question must map to one of these so the retrieval
# layer knows which tool to use and how to tag results.
SIGNAL_TYPES = [
    "funding",           # investment activity, deal flow, valuations
    "product_launch",    # new products, features, company announcements
    "regulatory",        # policy changes, government moves, compliance shifts
    "adoption",          # usage metrics, market penetration, customer growth
    "sentiment",         # practitioner opinions, community discussion
    "exec_language"      # what executives are saying in earnings calls, interviews
]


def build_decomposition_prompt(query: QueryObject) -> str:
    """
    Builds the prompt that asks Claude to decompose the topic
    into focused research sub-questions.
    """
    return f"""You are a senior market research analyst designing a research plan for a trend intelligence brief.

Your task is to decompose the following research topic into exactly 4-6 focused sub-questions that together will provide comprehensive coverage of the trend landscape.

RESEARCH PARAMETERS:
{format_query_for_prompt(query)}

SIGNAL TYPES AVAILABLE:
- funding: investment activity, deal flow, valuations, investor interest
- product_launch: new products, features, partnerships, company announcements  
- regulatory: policy changes, government moves, compliance shifts, legal developments
- adoption: usage metrics, market penetration, customer growth, deployment evidence
- sentiment: practitioner opinions, community discussion, expert commentary
- exec_language: what executives say in earnings calls, interviews, conferences

REQUIREMENTS:
1. Each sub-question must be specific and searchable — not vague
2. Each sub-question must map to exactly one signal type
3. Together the sub-questions must cover at least 3 different signal types
4. Sub-questions must be tailored to the geography and time horizon specified
5. Sub-questions should surface both positive signals AND potential headwinds

Return your response as valid JSON only, with no explanation or preamble, in exactly this format:
{{
  "topic": "{query.topic}",
  "sub_questions": [
    {{
      "question": "the specific research question",
      "signal_type": "one of the signal types listed above",
      "search_query": "a short optimized search query for this question (max 8 words)",
      "rationale": "one sentence explaining why this question matters for the brief"
    }}
  ]
}}"""


def decompose_query(query: QueryObject) -> dict:
    """
    Calls Claude to decompose the topic into sub-questions.
    Returns the parsed research plan as a dictionary.
    """
    prompt = build_decomposition_prompt(query)

    # We use claude-sonnet-4-20250514 as the model throughout.
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    raw_response = message.content[0].text

    # Claude should return pure JSON based on our prompt instructions.
    # We parse it here and validate the structure before returning.
    try:
        research_plan = json.loads(raw_response)
    except json.JSONDecodeError:
        # If Claude added any preamble despite instructions, try to
        # extract just the JSON portion
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start != -1 and end != 0:
            research_plan = json.loads(raw_response[start:end])
        else:
            raise ValueError(f"Claude returned invalid JSON: {raw_response}")

    # Validate that the response has the structure we expect
    if "sub_questions" not in research_plan:
        raise ValueError("Research plan missing sub_questions field")

    for sq in research_plan["sub_questions"]:
        if sq["signal_type"] not in SIGNAL_TYPES:
            raise ValueError(f"Invalid signal type returned: {sq['signal_type']}")

    return research_plan


def print_research_plan(plan: dict):
    """
    Prints the research plan in a readable format for debugging.
    """
    print(f"\nResearch Plan for: {plan['topic']}")
    print(f"Sub-questions generated: {len(plan['sub_questions'])}")
    print("-" * 60)
    for i, sq in enumerate(plan["sub_questions"], 1):
        print(f"\n{i}. {sq['question']}")
        print(f"   Signal type:  {sq['signal_type']}")
        print(f"   Search query: {sq['search_query']}")
        print(f"   Rationale:    {sq['rationale']}")


if __name__ == "__main__":
    from input_handler import validate_input

    # Build a test query
    query = validate_input(
        topic="AI adoption in healthcare diagnostics",
        audience="investor",
        geography="north america",
        time_horizon="12 months"
    )

    print("Sending to Claude for decomposition...")
    plan = decompose_query(query)
    print_research_plan(plan)