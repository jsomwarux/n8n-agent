"""Stage 1: Data collection via Brave Search + validation gate."""

import logging
from collectors.skincare_collector import collect_research

logger = logging.getLogger(__name__)


async def run(product_name: str, brand: str) -> dict:
    """Collect research data and validate the gate.

    Returns:
        {research_data: str, passed_gate: bool, queries_succeeded: int, total_snippets: int}

    Raises:
        ValueError if validation gate fails (< 3 queries or < 5 snippets).
    """
    result = await collect_research(product_name, brand)

    logger.info(
        f"Stage 1 collection: {result['queries_succeeded']}/5 queries succeeded, "
        f"{result['total_snippets']} total snippets, gate={'PASS' if result['passed_gate'] else 'FAIL'}"
    )

    if not result["passed_gate"]:
        raise ValueError(
            f"Data collection gate failed: {result['queries_succeeded']}/5 queries, "
            f"{result['total_snippets']} snippets (need >=3 queries and >=5 snippets)"
        )

    return result
