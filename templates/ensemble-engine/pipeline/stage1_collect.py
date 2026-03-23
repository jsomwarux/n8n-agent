"""Stage 1: Data collection via Brave Search + Firecrawl.

No niche-specific changes needed — delegates to the collector module.
CUSTOMIZE: collectors/niche_collector.py (the Brave queries and scrape targets).
"""

import logging
from typing import Optional
from collectors.niche_collector import collect_research

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
        f"ingredient_source={result.get('ingredient_source') or 'none'}, "
        f"gate={'PASS' if result['passed_gate'] else 'FAIL'}"
    )

    if not result["passed_gate"]:
        raise ValueError(
            f"Data collection gate failed: {result['queries_succeeded']}/6 queries, "
            f"{result['total_snippets']} snippets (need >=3 queries and >=5 snippets)"
        )

    return result
