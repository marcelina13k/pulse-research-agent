# retrieval.py
# Takes the research plan from query_decomposition and executes
# parallel searches across Tavily and NewsAPI for each sub-question.
# Returns a list of tagged, structured evidence objects ready
# for the credibility filter.

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# Instantiate Tavily client
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search_tavily(search_query: str, signal_type: str) -> list[dict]:
    """
    Searches Tavily for a given query.
    Returns a list of structured result objects.
    Tavily is our primary source — it's purpose-built for
    AI agents and returns clean excerpts with metadata.
    """
    try:
        response = tavily_client.search(
            query=search_query,
            search_depth="advanced",
            max_results=5
        )

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "excerpt": r.get("content", ""),
                "source": r.get("url", "").split("/")[2] if r.get("url") else "",
                "published_date": r.get("published_date", ""),
                "signal_type": signal_type,
                "retrieval_source": "tavily"
            })
        return results

    except Exception as e:
        # If Tavily fails we log the error and return empty list
        # rather than crashing the whole pipeline
        print(f"  Tavily error for '{search_query}': {e}")
        return []


def search_newsapi(search_query: str, signal_type: str, days_back: int = 90) -> list[dict]:
    """
    Searches NewsAPI for recent news articles.
    days_back controls how far back to search — default 90 days.
    """
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "q": search_query,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": 5,  # top 5 results per query
        "apiKey": NEWS_API_KEY
    }

    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)

        # raise_for_status() throws an error if the HTTP response
        # code is 4xx or 5xx — catches bad API keys, rate limits etc
        response.raise_for_status()
        data = response.json()

        results = []
        for article in data.get("articles", []):
            # Skip articles with removed content
            if article.get("title") == "[Removed]":
                continue

            results.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "excerpt": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "published_date": article.get("publishedAt", ""),
                "signal_type": signal_type,
                "retrieval_source": "newsapi"
            })
        return results

    except Exception as e:
        print(f"  NewsAPI error for '{search_query}': {e}")
        return []


def retrieve_evidence(research_plan: dict) -> list[dict]:
    """
    Main retrieval function. Takes the research plan from
    query_decomposition and runs searches for every sub-question
    across both Tavily and NewsAPI.

    Returns a flat list of all evidence objects — every result
    from every source for every sub-question combined.
    This gets passed to the credibility filter next.
    """
    all_evidence = []

    print(f"\nRunning retrieval for {len(research_plan['sub_questions'])} sub-questions...")

    for i, sq in enumerate(research_plan["sub_questions"], 1):
        print(f"\n  [{i}/{len(research_plan['sub_questions'])}] {sq['signal_type'].upper()}: {sq['search_query']}")

        # Search Tavily
        print(f"    Searching Tavily...")
        tavily_results = search_tavily(sq["search_query"], sq["signal_type"])
        print(f"    Got {len(tavily_results)} results from Tavily")
        all_evidence.extend(tavily_results)


    print(f"\nTotal evidence collected: {len(all_evidence)} results")
    return all_evidence


def print_evidence_summary(evidence: list[dict]):
    """
    Prints a summary of what was retrieved, grouped by signal type.
    Useful for debugging and understanding what the filter will work with.
    """
    from collections import Counter
    signal_counts = Counter(e["signal_type"] for e in evidence)
    source_counts = Counter(e["retrieval_source"] for e in evidence)

    print("\nEvidence summary:")
    print("  By signal type:")
    for signal, count in signal_counts.most_common():
        print(f"    {signal}: {count} results")
    print("  By source:")
    for source, count in source_counts.most_common():
        print(f"    {source}: {count} results")


if __name__ == "__main__":
    from input_handler import validate_input
    from query_decomposition import decompose_query

    # Build query and decompose it
    query = validate_input(
        topic="AI adoption in healthcare diagnostics",
        audience="investor",
        geography="north america",
        time_horizon="12 months"
    )

    print("Decomposing query...")
    plan = decompose_query(query)
    print(f"Got {len(plan['sub_questions'])} sub-questions")

    # Run retrieval
    evidence = retrieve_evidence(plan)
    print_evidence_summary(evidence)

    # Print first 3 results so you can see what the data looks like
    print("\nSample evidence (first 3 results):")
    print("-" * 60)
    for item in evidence[:3]:
        print(f"\nTitle:   {item['title']}")
        print(f"Source:  {item['source']} via {item['retrieval_source']}")
        print(f"Signal:  {item['signal_type']}")
        print(f"Date:    {item['published_date']}")
        print(f"Excerpt: {item['excerpt'][:150]}...")