# input_handler.py
# This is the entry point of the system. It takes raw user input,
# validates it, and builds a structured query object that every
# downstream component will use.

from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class QueryObject:
    topic: str
    audience: str
    geography: str
    time_horizon: str
    raw_input: str

# These are the valid options for audience and geography.
# Keeping them explicit means the system always knows what
# context to apply when generating strategic implications.
VALID_AUDIENCES = [
    "founder",
    "investor",
    "product team",
    "analyst",
    "general"
]

VALID_GEOGRAPHIES = [
    "global",
    "north america",
    "europe",
    "asia pacific",
    "latin america"
]

VALID_TIME_HORIZONS = [
    "6 months",
    "12 months",
    "24 months",
    "3-5 years"
]

def validate_input(
    topic: str,
    audience: str = "general",
    geography: str = "global",
    time_horizon: str = "12 months"
) -> QueryObject:
    """
    Validates user input and returns a structured QueryObject.
    Raises a ValueError with a clear message if anything is invalid.
    """

    # Strip whitespace and check the topic isn't empty
    topic = topic.strip()
    if not topic:
        raise ValueError("Topic cannot be empty. Please enter a market or trend to research.")

    if len(topic) < 5:
        raise ValueError("Topic is too short. Please be more specific.")

    if len(topic) > 200:
        raise ValueError("Topic is too long. Please keep it under 200 characters.")

    # Normalize to lowercase for comparison
    audience = audience.lower().strip()
    if audience not in VALID_AUDIENCES:
        raise ValueError(f"Audience must be one of: {', '.join(VALID_AUDIENCES)}")

    geography = geography.lower().strip()
    if geography not in VALID_GEOGRAPHIES:
        raise ValueError(f"Geography must be one of: {', '.join(VALID_GEOGRAPHIES)}")

    time_horizon = time_horizon.lower().strip()
    if time_horizon not in VALID_TIME_HORIZONS:
        raise ValueError(f"Time horizon must be one of: {', '.join(VALID_TIME_HORIZONS)}")

    # Build and return the structured query object
    return QueryObject(
        topic=topic,
        audience=audience,
        geography=geography,
        time_horizon=time_horizon,
        raw_input=topic
    )


def format_query_for_prompt(query: QueryObject) -> str:
    """
    Converts the QueryObject into a formatted string that gets
    injected into Claude prompts downstream. Every Claude call
    will use this to maintain consistent context.
    """
    return f"""
Topic: {query.topic}
Audience: {query.audience}
Geography: {query.geography}
Time horizon: {query.time_horizon}
""".strip()


# This block only runs if you execute this file directly —
# not when it gets imported by other files. Use it to test.
if __name__ == "__main__":
    # Test with a valid input
    try:
        query = validate_input(
            topic="AI adoption in healthcare diagnostics",
            audience="investor",
            geography="north america",
            time_horizon="12 months"
        )
        print("Query object created successfully:")
        print(f"  Topic: {query.topic}")
        print(f"  Audience: {query.audience}")
        print(f"  Geography: {query.geography}")
        print(f"  Time horizon: {query.time_horizon}")
        print()
        print("Formatted for prompt:")
        print(format_query_for_prompt(query))

    except ValueError as e:
        print(f"Validation error: {e}")

    # Test with an invalid input to make sure validation works
    print()
    print("Testing invalid audience:")
    try:
        bad_query = validate_input(
            topic="AI in healthcare",
            audience="CEO",  # not in valid list
        )
    except ValueError as e:
        print(f"Caught expected error: {e}")