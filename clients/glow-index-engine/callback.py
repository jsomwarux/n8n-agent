"""POST result to Glow Index callbackUrl with 3x retry, 5s backoff.
Also handles post-analysis image fetching via Brave Image Search."""

import asyncio
import logging
import os
import re
import urllib.parse
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BRAVE_IMAGE_URL = "https://api.search.brave.com/res/v1/images/search"
_ENV_PATH = os.path.expanduser("~/.config/env/global.env")


def _load_brave_key() -> Optional[str]:
    try:
        with open(_ENV_PATH) as f:
            for line in f:
                m = re.match(r"^BRAVE_API_KEY=(.+)$", line.strip())
                if m:
                    return m.group(1)
    except FileNotFoundError:
        pass
    return os.environ.get("BRAVE_API_KEY")


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


async def fetch_and_set_product_image(
    product_name: str,
    brand: str,
    product_id: str,
    fetch_images_url: str,
    admin_secret: str,
) -> None:
    """After analysis, fetch a product image via Brave and POST to the app's fetch-images endpoint.
    Falls back to direct Brave search + DB update via the admin API.
    This is fire-and-forget — failures are logged but do not affect the analysis pipeline."""
    brave_key = _load_brave_key()
    if not brave_key:
        logger.warning(f"No BRAVE_API_KEY — skipping image fetch for {brand} {product_name}")
        return

    query = f"{product_name} {brand} skincare product"
    params = urllib.parse.urlencode({"q": query, "count": "1"})
    url = f"{_BRAVE_IMAGE_URL}?{params}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    "X-Subscription-Token": brave_key,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            logger.info(f"No image results for {brand} {product_name}")
            return

        image_url = results[0].get("thumbnail", {}).get("src") or results[0].get("properties", {}).get("url")
        if not image_url:
            logger.info(f"No usable image URL for {brand} {product_name}")
            return

        # POST to the app's fetch-images endpoint to update DB
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                fetch_images_url,
                json={"productId": product_id, "imageUrl": image_url},
                headers={
                    "Content-Type": "application/json",
                    "x-admin-key": admin_secret,
                },
                timeout=10.0,
            )
        logger.info(f"Image set for {brand} {product_name}: {image_url[:80]}")
    except Exception as e:
        logger.warning(f"Image fetch failed for {brand} {product_name}: {e}")
