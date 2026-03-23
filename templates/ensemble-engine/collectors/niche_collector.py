"""Niche data collector — Brave Search + optional Firecrawl scrape.

CUSTOMIZE THIS FILE for your niche:
1. Update _build_brave_queries() with 6 domain-specific search queries
2. Update _scrape_detail_page() with your niche's detail page sources (if any)
3. Rename this file to match your niche (e.g. crypto_collector.py, restaurant_collector.py)
4. Update the import in pipeline/stage1_collect.py to match

The glow-index version searches for: INCI ingredients, Reddit reviews, dermatologist opinions,
dupes/alternatives, safety controversies, and clinical evidence. Replace with your niche equivalents.
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import quote_plus

import httpx

from config import BRAVE_API_KEY, BRAVE_SEARCH_URL, FIRECRAWL_API_KEY

logger = logging.getLogger(__name__)

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"


def _build_brave_queries(product_name: str, brand: str) -> list:
    """6 targeted Brave queries — each hits a specific knowledge domain.

    REPLACE these with your niche-specific queries. Examples:

    For crypto:
      - CoinGecko/CoinMarketCap data
      - Reddit community sentiment
      - On-chain analytics
      - Tokenomics analysis
      - Team/development activity
      - Recent news/controversies

    For restaurants:
      - Yelp/Google reviews
      - Health inspection records
      - Menu and pricing data
      - Chef background
      - Recent press/reviews
      - Competitor comparison
    """
    return [
        {
            "key": "official_data",
            "query": f'"{product_name}" {brand} official specifications data',
            "purpose": "Official product/item data from authoritative sources",
        },
        {
            "key": "community_reviews",
            "query": f'"{product_name}" {brand} site:reddit.com review',
            "purpose": "Community sentiment and real user reviews",
        },
        {
            "key": "expert_analysis",
            "query": f'"{product_name}" {brand} expert analysis review professional',
            "purpose": "Professional/expert opinions and analysis",
        },
        {
            "key": "alternatives",
            "query": f'"{product_name}" alternative competitor comparison "better than" OR "similar to"',
            "purpose": "Competing products and alternatives at similar price",
        },
        {
            "key": "controversies",
            "query": f'"{product_name}" {brand} issue problem controversy concern',
            "purpose": "Known issues, controversies, or red flags",
        },
        {
            "key": "evidence",
            "query": f'{brand} "{product_name}" evidence data benchmark test',
            "purpose": "Hard data, benchmarks, or test results",
        },
    ]


async def _search_brave(client: httpx.AsyncClient, query_obj: dict, count: int = 5) -> dict:
    """Execute a single Brave search."""
    try:
        resp = await client.get(
            BRAVE_SEARCH_URL,
            params={"q": query_obj["query"], "count": count},
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
        return {"key": query_obj["key"], "purpose": query_obj["purpose"], "query": query_obj["query"], "snippets": snippets, "error": None}
    except Exception as e:
        logger.warning(f"Brave search failed for '{query_obj['key']}': {e}")
        return {"key": query_obj["key"], "purpose": query_obj["purpose"], "query": query_obj["query"], "snippets": [], "error": str(e)}


async def _scrape_detail_page(brave_results: list) -> dict:
    """Optional: scrape a detail page for deeper data (like ingredient lists, spec sheets).

    CUSTOMIZE: add your niche's authoritative data sources.
    If your niche doesn't need Firecrawl scraping, return the empty fallback.

    The glow-index version scrapes INCIDecoder/COSDNA for full ingredient lists.
    """
    # Example: scrape the first relevant result from official_data query
    official_result = next((r for r in brave_results if r["key"] == "official_data"), None)
    if not official_result or not official_result["snippets"]:
        return {"source": None, "url": None, "content": None, "error": "No official_data results"}

    # Try scraping the first result
    for snippet in official_result["snippets"]:
        url = snippet.get("url", "")
        if url:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        FIRECRAWL_URL,
                        headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"},
                        json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                        timeout=20.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    markdown = (data.get("data", {}) or {}).get("markdown", "") or ""
                    if len(markdown) > 200:
                        logger.info(f"Detail page scraped: {url}")
                        return {"source": "detail-page", "url": url, "content": markdown[:2500], "error": None}
            except Exception as e:
                logger.warning(f"Firecrawl scrape failed: {e}")

    return {"source": None, "url": None, "content": None, "error": "No scrapeable detail page found"}


async def collect_research(product_name: str, brand: str, price_usd: Optional[float] = None) -> dict:
    """Run Brave searches + optional detail scrape concurrently.

    Returns {research_data, queries_succeeded, total_snippets, passed_gate, ingredient_source}
    """
    queries = _build_brave_queries(product_name, brand)

    async with httpx.AsyncClient() as client:
        brave_results = await asyncio.gather(*[_search_brave(client, q) for q in queries])

    detail_result = await _scrape_detail_page(list(brave_results))

    queries_succeeded = sum(1 for r in brave_results if r["snippets"])
    total_snippets = sum(len(r["snippets"]) for r in brave_results)
    passed_gate = queries_succeeded >= 3 and total_snippets >= 5

    lines = ["=== RESEARCH DATA (verified from web) ===\n"]

    if detail_result.get("content"):
        lines.append("--- DETAILED DATA ---")
        lines.append(f"Source: {detail_result['source']} ({detail_result['url']})")
        lines.append(detail_result["content"])
    else:
        lines.append("[Detail page scrape unavailable — models should use training knowledge, flag confidence lower]")
    lines.append("")

    if price_usd:
        lines.append("--- PRICE CONTEXT ---")
        lines.append(f"Current price: ${price_usd:.2f}")
        lines.append("")

    for r in brave_results:
        lines.append(f"--- {r['purpose'].upper()} ---")
        if r["error"] and not r["snippets"]:
            lines.append(f"  [Search failed: {r['error']}]")
        elif not r["snippets"]:
            lines.append("  [No results]")
        else:
            for s in r["snippets"]:
                lines.append(f"  * {s['title']}: {s['description']}")
                lines.append(f"    {s['url']}")
        lines.append("")

    return {
        "research_data": "\n".join(lines),
        "queries_succeeded": queries_succeeded,
        "total_snippets": total_snippets,
        "passed_gate": passed_gate,
        "ingredient_source": detail_result.get("source"),
        "raw_results": brave_results,
    }
