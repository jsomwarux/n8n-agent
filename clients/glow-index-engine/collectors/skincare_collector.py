"""Brave Search data collector for skincare products."""

import asyncio
import logging
from urllib.parse import quote_plus

import httpx

from config import BRAVE_API_KEY, BRAVE_SEARCH_URL

logger = logging.getLogger(__name__)


def _build_queries(product_name: str, brand: str) -> list[str]:
    """Build 5 Brave search queries per spec."""
    return [
        f"{product_name} {brand} ingredients INCI",
        f"{product_name} {brand} review reddit skincare",
        f"{product_name} {brand} dermatologist review",
        f"{product_name} dupe alternative cheaper",
        f"{product_name} {brand} controversy ingredient concern",
    ]


async def _search_brave(client: httpx.AsyncClient, query: str) -> dict:
    """Execute a single Brave search. Returns {query, snippets, error}."""
    try:
        resp = await client.get(
            BRAVE_SEARCH_URL,
            params={"q": query, "count": 5},
            headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("web", {}).get("results", [])
        snippets = [
            {"title": r.get("title", ""), "description": r.get("description", ""), "url": r.get("url", "")}
            for r in results
        ]
        return {"query": query, "snippets": snippets, "error": None}
    except Exception as e:
        logger.warning(f"Brave search failed for '{query}': {e}")
        return {"query": query, "snippets": [], "error": str(e)}


async def collect_research(product_name: str, brand: str) -> dict:
    """Run 5 Brave searches in parallel. Returns {research_data, queries_succeeded, total_snippets, passed_gate}."""
    queries = _build_queries(product_name, brand)
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_search_brave(client, q) for q in queries])

    queries_succeeded = sum(1 for r in results if r["snippets"])
    total_snippets = sum(len(r["snippets"]) for r in results)
    passed_gate = queries_succeeded >= 3 and total_snippets >= 5

    # Format research data for prompt injection
    lines = ["=== RESEARCH DATA (verified from web) ==="]
    for r in results:
        lines.append(f"\nQuery: {r['query']}")
        if r["error"]:
            lines.append(f"  [Search failed: {r['error']}]")
        elif not r["snippets"]:
            lines.append("  [No results]")
        else:
            for s in r["snippets"]:
                lines.append(f"  - {s['title']}: {s['description']}")
                lines.append(f"    URL: {s['url']}")

    return {
        "research_data": "\n".join(lines),
        "queries_succeeded": queries_succeeded,
        "total_snippets": total_snippets,
        "passed_gate": passed_gate,
        "raw_results": results,
    }
