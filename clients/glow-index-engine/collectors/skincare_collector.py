"""Skincare data collector — Brave Search + Firecrawl ingredient scrape."""

import asyncio
import logging
from typing import Optional
from urllib.parse import quote_plus

import httpx

from config import BRAVE_API_KEY, BRAVE_SEARCH_URL, FIRECRAWL_API_KEY

logger = logging.getLogger(__name__)

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"

# Priority ingredient databases — tried in order, first success wins
INGREDIENT_SOURCES = [
    ("INCIDecoder",   lambda n, b: f"https://incidecoder.com/search?query={quote_plus(n + ' ' + b)}"),
    ("COSDNA",        lambda n, b: f"https://cosdna.com/eng/cosmetic.php?q={quote_plus(n + ' ' + b)}"),
    ("EWG Skin Deep", lambda n, b: f"https://www.ewg.org/skindeep/search/?search={quote_plus(n)}"),
]


def _build_brave_queries(product_name: str, brand: str) -> list:
    """6 targeted Brave queries — each hits a specific knowledge domain."""
    return [
        {
            "key": "inci_formula",
            "query": f'"{product_name}" site:incidecoder.com OR site:cosdna.com OR site:ewg.org ingredients INCI',
            "purpose": "Full ingredient list from cosmetic databases",
        },
        {
            "key": "reddit_community",
            "query": f'"{product_name}" {brand} site:reddit.com skincare review',
            "purpose": "Organic community sentiment",
        },
        {
            "key": "derm_expert",
            "query": f'"{product_name}" {brand} dermatologist esthetician review ingredients analysis',
            "purpose": "Professional opinion and ingredient critique",
        },
        {
            "key": "dupe_alternative",
            "query": f'"{product_name}" dupe alternative cheaper "same ingredients" OR "similar formula"',
            "purpose": "Formula-equivalent alternatives at lower price",
        },
        {
            "key": "controversy",
            "query": f'"{product_name}" {brand} reformulation "ingredient concern" OR "reaction" OR "controversy"',
            "purpose": "Safety flags, silent reformulations, adverse reactions",
        },
        {
            "key": "clinical_evidence",
            "query": f'{brand} "{product_name}" clinical study "clinically proven" OR "dermatologist tested" concentration',
            "purpose": "Clinical backing and active concentration claims",
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


async def _firecrawl_scrape(url: str, source_name: str) -> dict:
    """Scrape a URL via Firecrawl for ingredient data."""
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
                return {"source": source_name, "url": url, "content": markdown[:2500], "error": None}
            return {"source": source_name, "url": url, "content": None, "error": "Insufficient content"}
    except Exception as e:
        logger.warning(f"Firecrawl scrape failed for {source_name}: {e}")
        return {"source": source_name, "url": url, "content": None, "error": str(e)}


async def _scrape_ingredients_from_brave(brave_results: list) -> dict:
    """Use Brave inci_formula results to find a direct product URL, then Firecrawl it.
    
    Preferred over scraping search pages — gets the actual ingredient list, not nav links.
    """
    inci_result = next((r for r in brave_results if r["key"] == "inci_formula"), None)
    if not inci_result or not inci_result["snippets"]:
        return {"source": None, "url": None, "content": None, "error": "No inci_formula Brave results"}

    # Priority: incidecoder product page > cosdna > ewg
    priority_domains = ["incidecoder.com/products/", "cosdna.com/cosmetic/", "ewg.org/skindeep/products/"]
    for domain in priority_domains:
        for snippet in inci_result["snippets"]:
            url = snippet.get("url", "")
            if domain in url:
                source_name = domain.split(".")[0].replace("www.", "")
                result = await _firecrawl_scrape(url, source_name)
                if result["content"]:
                    logger.info(f"Ingredient data found via direct scrape: {url}")
                    return result

    # Fallback: try the first result regardless of domain
    for snippet in inci_result["snippets"]:
        url = snippet.get("url", "")
        if url and any(d in url for d in ["incidecoder", "cosdna", "ewg.org", "paulaschoice", "skincarisma"]):
            result = await _firecrawl_scrape(url, "ingredient-db")
            if result["content"]:
                return result

    return {"source": None, "url": None, "content": None, "error": "No scrapeable ingredient page found in Brave results"}


async def collect_research(product_name: str, brand: str, price_usd: Optional[float] = None) -> dict:
    """Run Brave searches + Firecrawl ingredient scrape concurrently.

    Returns {research_data, queries_succeeded, total_snippets, passed_gate, ingredient_source}
    """
    queries = _build_brave_queries(product_name, brand)

    # Step 1: Run all Brave searches in parallel
    async with httpx.AsyncClient() as client:
        brave_results = await asyncio.gather(*[_search_brave(client, q) for q in queries])

    # Step 2: Use inci_formula Brave results to find direct product URL, then Firecrawl it
    ingredient_result = await _scrape_ingredients_from_brave(list(brave_results))

    queries_succeeded = sum(1 for r in brave_results if r["snippets"])
    total_snippets = sum(len(r["snippets"]) for r in brave_results)
    passed_gate = queries_succeeded >= 3 and total_snippets >= 5

    # Format research data for prompt injection
    lines = ["=== RESEARCH DATA (verified from web) ===\n"]

    # Ingredient section first — most critical for scoring
    lines.append("--- INGREDIENT DATABASE ---")
    if ingredient_result["content"]:
        lines.append(f"Source: {ingredient_result['source']} ({ingredient_result['url']})")
        lines.append(ingredient_result["content"])
    else:
        lines.append("[Ingredient database scrape unavailable — use training knowledge for INCI, flag confidence lower]")
    lines.append("")

    # Price context
    if price_usd:
        lines.append("--- PRICE CONTEXT ---")
        lines.append(f"Current retail price: ${price_usd:.2f}")
        lines.append("")

    # Brave results by domain
    for r in brave_results:
        lines.append(f"--- {r['purpose'].upper()} ---")
        if r["error"] and not r["snippets"]:
            lines.append(f"  [Search failed: {r['error']}]")
        elif not r["snippets"]:
            lines.append("  [No results]")
        else:
            for s in r["snippets"]:
                lines.append(f"  • {s['title']}: {s['description']}")
                lines.append(f"    {s['url']}")
        lines.append("")

    return {
        "research_data": "\n".join(lines),
        "queries_succeeded": queries_succeeded,
        "total_snippets": total_snippets,
        "passed_gate": passed_gate,
        "ingredient_source": ingredient_result["source"],
        "raw_results": brave_results,
    }
