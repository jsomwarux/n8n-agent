"""Skincare data collector — Brave Search + Firecrawl ingredient scrape."""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

import httpx

from config import BRAVE_API_KEY, BRAVE_SEARCH_URL, FIRECRAWL_API_KEY

logger = logging.getLogger(__name__)

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"

# Retry config for Brave 429 rate limits
BRAVE_429_MAX_RETRIES = 2
BRAVE_429_BACKOFF_SECS = 2.0

# Priority ingredient databases — tried in order, first success wins
INGREDIENT_SOURCES = [
    ("INCIDecoder",   lambda n, b: f"https://incidecoder.com/search?query={quote_plus(b + ' ' + n)}"),
    ("COSDNA",        lambda n, b: f"https://cosdna.com/eng/cosmetic.php?q={quote_plus(n + ' ' + b)}"),
    ("EWG Skin Deep", lambda n, b: f"https://www.ewg.org/skindeep/search/?search={quote_plus(n)}"),
]


def _slugify(text: str) -> str:
    """Convert text to URL slug: lowercase, spaces→hyphens, strip special chars."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)  # remove special chars except hyphens
    slug = re.sub(r"[\s_]+", "-", slug)   # spaces/underscores → hyphens
    slug = re.sub(r"-+", "-", slug)       # collapse multiple hyphens
    return slug.strip("-")


def _validate_brand_match(content: str, brand: str) -> str:
    """Check if scraped content belongs to the correct brand.

    Returns brand_match_confidence: high / medium / low / none.
    """
    if not content or not brand:
        return "none"

    brand_lower = brand.lower().strip()
    content_lower = content[:1500].lower()  # check first 1500 chars (title/heading area)

    # Check for exact brand name
    if brand_lower in content_lower:
        return "high"

    # Check for brand words (e.g. "La Roche-Posay" → check "roche" and "posay")
    brand_words = [w for w in re.split(r"[\s\-]+", brand_lower) if len(w) > 2]
    matches = sum(1 for w in brand_words if w in content_lower)
    if brand_words and matches >= len(brand_words) * 0.6:
        return "medium"

    # Single-word brand partial match (e.g. "CeraVe" in content)
    if len(brand_words) == 1 and brand_words[0] in content_lower:
        return "high"

    return "none"


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
    """Execute a single Brave search with retry on 429 rate limits."""
    last_error = None
    for attempt in range(1 + BRAVE_429_MAX_RETRIES):
        try:
            resp = await client.get(
                BRAVE_SEARCH_URL,
                params={"q": query_obj["query"], "count": count},
                headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"},
                timeout=15.0,
            )
            if resp.status_code == 429 and attempt < BRAVE_429_MAX_RETRIES:
                wait = BRAVE_429_BACKOFF_SECS * (attempt + 1)
                logger.warning(f"Brave 429 rate limit for '{query_obj['key']}', retry {attempt + 1} in {wait}s")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            results = data.get("web", {}).get("results", [])
            snippets = [
                {"title": r.get("title", ""), "description": r.get("description", ""), "url": r.get("url", "")}
                for r in results
            ]
            return {"key": query_obj["key"], "purpose": query_obj["purpose"], "query": query_obj["query"], "snippets": snippets, "error": None}
        except Exception as e:
            last_error = e
            if attempt < BRAVE_429_MAX_RETRIES:
                # Only retry on 429, not other errors
                if "429" not in str(e):
                    break
                wait = BRAVE_429_BACKOFF_SECS * (attempt + 1)
                logger.warning(f"Brave error for '{query_obj['key']}': {e}, retry {attempt + 1} in {wait}s")
                await asyncio.sleep(wait)
            else:
                break

    logger.warning(f"Brave search failed for '{query_obj['key']}': {last_error}")
    return {"key": query_obj["key"], "purpose": query_obj["purpose"], "query": query_obj["query"], "snippets": [], "error": str(last_error)}


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


async def _try_incidecoder_slug_fallback(product_name: str, brand: str) -> dict:
    """Fallback: try direct INCIDecoder URL pattern when search/Brave fails.

    Pattern: https://incidecoder.com/products/{brand-slug}-{product-slug}
    """
    slug = _slugify(f"{brand} {product_name}")
    url = f"https://incidecoder.com/products/{slug}"
    logger.info(f"Trying INCIDecoder slug fallback: {url}")
    result = await _firecrawl_scrape(url, "incidecoder")
    if result["content"]:
        confidence = _validate_brand_match(result["content"], brand)
        if confidence in ("high", "medium"):
            logger.info(f"INCIDecoder slug fallback succeeded (brand_match={confidence})")
            return result
        else:
            logger.warning(f"INCIDecoder slug fallback scraped wrong product (brand_match={confidence}), discarding")
            return {"source": None, "url": url, "content": None, "error": f"Brand mismatch on slug fallback (confidence={confidence})"}
    return result


async def _scrape_ingredients_from_brave(brave_results: list, brand: str) -> tuple[dict, str]:
    """Use Brave inci_formula results to find a direct product URL, then Firecrawl it.

    Returns (ingredient_result, brand_match_confidence).
    Brand validation: after scraping, verify the content belongs to the correct brand.
    If brand doesn't match → discard and continue searching.
    """
    inci_result = next((r for r in brave_results if r["key"] == "inci_formula"), None)
    if not inci_result or not inci_result["snippets"]:
        return {"source": None, "url": None, "content": None, "error": "No inci_formula Brave results"}, "none"

    # Priority: incidecoder product page > cosdna > ewg
    priority_domains = ["incidecoder.com/products/", "cosdna.com/cosmetic/", "ewg.org/skindeep/products/"]
    for domain in priority_domains:
        for snippet in inci_result["snippets"]:
            url = snippet.get("url", "")
            if domain in url:
                source_name = domain.split(".")[0].replace("www.", "")
                result = await _firecrawl_scrape(url, source_name)
                if result["content"]:
                    confidence = _validate_brand_match(result["content"], brand)
                    if confidence in ("high", "medium"):
                        logger.info(f"Ingredient data found via direct scrape: {url} (brand_match={confidence})")
                        return result, confidence
                    else:
                        logger.warning(
                            f"Scraped {url} but brand '{brand}' not found in content "
                            f"(brand_match={confidence}) — discarding wrong product"
                        )
                        # Don't return — keep searching other results

    # Fallback: try other ingredient DB results
    for snippet in inci_result["snippets"]:
        url = snippet.get("url", "")
        if url and any(d in url for d in ["incidecoder", "cosdna", "ewg.org", "paulaschoice", "skincarisma"]):
            result = await _firecrawl_scrape(url, "ingredient-db")
            if result["content"]:
                confidence = _validate_brand_match(result["content"], brand)
                if confidence in ("high", "medium"):
                    logger.info(f"Ingredient data found via fallback scrape: {url} (brand_match={confidence})")
                    return result, confidence
                else:
                    logger.warning(f"Fallback scrape {url} brand mismatch (brand_match={confidence}), skipping")

    return {"source": None, "url": None, "content": None, "error": "No scrapeable ingredient page found in Brave results"}, "none"


async def collect_research(product_name: str, brand: str, price_usd: Optional[float] = None) -> dict:
    """Run Brave searches + Firecrawl ingredient scrape concurrently.

    Returns {research_data, queries_succeeded, total_snippets, passed_gate,
             ingredient_source, brand_match_confidence, gate_fail_reason, raw_results}
    """
    queries = _build_brave_queries(product_name, brand)

    # Step 1: Run all Brave searches in parallel
    async with httpx.AsyncClient() as client:
        brave_results = await asyncio.gather(*[_search_brave(client, q) for q in queries])

    # Step 2: Use inci_formula Brave results to find direct product URL, then Firecrawl it
    # Now passes brand for validation
    ingredient_result, brand_confidence = await _scrape_ingredients_from_brave(list(brave_results), brand)

    # Step 3: If Brave-based scrape failed, try INCIDecoder slug fallback
    if not ingredient_result["content"]:
        logger.info(f"Brave-based ingredient scrape failed, trying INCIDecoder slug fallback for '{brand} {product_name}'")
        slug_result = await _try_incidecoder_slug_fallback(product_name, brand)
        if slug_result["content"]:
            ingredient_result = slug_result
            brand_confidence = _validate_brand_match(slug_result["content"], brand)

    queries_succeeded = sum(1 for r in brave_results if r["snippets"])
    total_snippets = sum(len(r["snippets"]) for r in brave_results)

    # Gate logic: loosened thresholds, but ingredients required
    gate_fail_reason = None
    if queries_succeeded < 2:
        gate_fail_reason = f"Only {queries_succeeded}/6 queries succeeded (need >=2)"
    elif total_snippets < 3:
        gate_fail_reason = f"Only {total_snippets} total snippets (need >=3)"
    elif not ingredient_result["content"]:
        gate_fail_reason = "No valid ingredient data found — ingredients are required for meaningful analysis"

    passed_gate = gate_fail_reason is None

    if gate_fail_reason:
        logger.warning(f"Stage 1 gate FAIL for '{brand} {product_name}': {gate_fail_reason}")

    # Determine final ingredient_source
    ingredient_source = ingredient_result["source"] if ingredient_result["content"] else "not_found"

    # Format research data for prompt injection
    lines = ["=== RESEARCH DATA (verified from web) ===\n"]

    # Ingredient confidence notice — so LLMs know how reliable ingredient data is
    lines.append(f"--- INGREDIENT DATA CONFIDENCE: {brand_confidence.upper()} ---")
    if brand_confidence in ("low", "none"):
        lines.append("[WARNING: Ingredient data could not be verified as belonging to this brand. Caveat all ingredient-based scores.]")
    lines.append("")

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
        "gate_fail_reason": gate_fail_reason,
        "ingredient_source": ingredient_source,
        "brand_match_confidence": brand_confidence,
        "raw_results": brave_results,
    }
