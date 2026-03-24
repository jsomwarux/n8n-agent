"""Stage 1: Data collection via Brave Search + Firecrawl ingredient scrape."""

import logging
from typing import Optional
from collectors.skincare_collector import collect_research

logger = logging.getLogger(__name__)


async def run(product_name: str, brand: str, price_usd: Optional[float] = None) -> dict:
    """Collect research data and validate the gate.

    Returns:
        {research_data, passed_gate, queries_succeeded, total_snippets, ingredient_source}

    Raises:
        ValueError if validation gate fails (< 3 queries or < 5 snippets).
    """
    result = await collect_research(product_name, brand, price_usd=price_usd)

    logger.info(
        f"Stage 1 collection: {result['queries_succeeded']}/6 queries succeeded, "
        f"{result['total_snippets']} total snippets, "
        f"ingredient_source={result['ingredient_source'] or 'none'}, "
        f"brand_match={result.get('brand_match_confidence', 'unknown')}, "
        f"gate={'PASS' if result['passed_gate'] else 'FAIL'}"
    )

    if not result["passed_gate"]:
        reason = result.get("gate_fail_reason", "unknown")
        raise ValueError(f"Data collection gate failed: {reason}")

    return result
