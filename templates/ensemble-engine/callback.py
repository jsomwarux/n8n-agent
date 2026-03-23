"""POST result to callbackUrl with 3x retry, 5s backoff. No niche-specific changes needed."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


async def send_callback(callback_url: str, payload: dict, max_retries: int = 3, backoff: float = 5.0) -> bool:
    """Send callback with retry. Returns True if successful."""
    if not callback_url:
        logger.warning("No callbackUrl provided — skipping callback")
        return False

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    callback_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0,
                )
                resp.raise_for_status()
                logger.info(f"Callback sent successfully (attempt {attempt}): {resp.status_code}")
                return True
        except Exception as e:
            logger.warning(f"Callback attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(backoff * attempt)

    logger.error(f"Callback failed after {max_retries} attempts to {callback_url}")
    return False


async def send_failure_callback(callback_url: str, callback_secret: str, product_id: str, run_id: str, error: str) -> bool:
    """Send a failure callback."""
    payload = {
        "secret": callback_secret,
        "productId": product_id,
        "runId": run_id,
        "error": True,
        "message": error,
    }
    return await send_callback(callback_url, payload)
