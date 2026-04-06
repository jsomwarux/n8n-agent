"""Stage 2: 4 parallel LLM calls for independent analysis.

Resilience contract: ALL 4 models must produce a valid score.
Each model gets 3 attempts with exponential backoff.
Parse/validate failures are retried just like network errors.
If any model fails after 3 attempts, the entire stage retries once (60s wait).
If still failing after stage retry, the product analysis fails cleanly.
"""

import asyncio
import logging
from datetime import date
from pathlib import Path

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_URL, MODELS, MODEL_DISPLAY_NAMES, LLM_TIMEOUT, LLM_MAX_TOKENS, MODEL_MAX_TOKENS
from pipeline.validators import extract_openrouter_content, parse_llm_json, validate_score

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage1_analysis.txt"
MAX_MODEL_ATTEMPTS = 3
RETRY_BACKOFF = [2, 5, 10]  # seconds between attempts 1→2, 2→3


def _load_prompt() -> str:
    text = PROMPT_PATH.read_text()
    assert len(text) > 500, f"Stage 1 prompt too short ({len(text)} chars) — check prompts/stage1_analysis.txt"
    return text


def _build_prompt(template: str, product: dict, research_data: str, llm_name: str) -> str:
    research_section = research_data if research_data else ""
    return template.format(
        productName=product["productName"],
        brand=product["brand"],
        category=product.get("category", "skincare"),
        priceUsd=product["priceUsd"],
        date=date.today().isoformat(),
        research_section=research_section,
        llmName=llm_name,
    )


async def _call_model_once(client: httpx.AsyncClient, model_key: str, prompt: str) -> dict:
    """Single attempt to call a model. Returns {model_key, raw_text, parsed, error}."""
    model_id = MODELS[model_key]
    display_name = MODEL_DISPLAY_NAMES[model_key]

    messages = []
    if model_key in ("grok", "gpt", "gemini"):
        messages.append({"role": "system", "content": "You are a senior skincare analyst and cosmetic chemist. Return ONLY valid JSON, no markdown fences."})
    messages.append({"role": "user", "content": prompt})

    max_tokens = MODEL_MAX_TOKENS.get(model_key, LLM_MAX_TOKENS)
    body = {"model": model_id, "max_tokens": max_tokens, "messages": messages}
    if model_key in ("gpt", "grok"):
        body["response_format"] = {"type": "json_object"}

    resp = await client.post(
        OPENROUTER_URL,
        json=body,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=LLM_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    raw_text = extract_openrouter_content(data)
    if raw_text is None:
        return {"model_key": model_key, "raw_text": None, "parsed": None, "error": f"No content in response: {str(data)[:200]}"}

    parsed = parse_llm_json(raw_text, model_key)
    if parsed and validate_score(parsed, model_key):
        logger.info(f"Stage 2 {display_name}: score={parsed.get('base_score') or parsed.get('total')}, tier={parsed.get('tier')}")
        return {"model_key": model_key, "raw_text": raw_text, "parsed": parsed, "error": None}
    else:
        logger.warning(f"Stage 2 {display_name}: parse/validate failed. raw: {(raw_text or '')[:200]}")
        return {"model_key": model_key, "raw_text": raw_text, "parsed": None, "error": f"Parse/validate failure: {(raw_text or '')[:100]}"}


async def _call_model_with_retry(client: httpx.AsyncClient, model_key: str, prompt: str) -> dict:
    """Call model with up to MAX_MODEL_ATTEMPTS retries and exponential backoff.
    Retries on: network errors, timeouts, parse failures, validate failures.
    Returns the result dict — error field is set if all attempts failed.
    """
    display_name = MODEL_DISPLAY_NAMES[model_key]
    last_error = "unknown"

    for attempt in range(1, MAX_MODEL_ATTEMPTS + 1):
        try:
            result = await _call_model_once(client, model_key, prompt)
            if result.get("error") is None:
                return result  # Success
            # Parse/validate failure — treat as retryable
            last_error = result.get("error", "parse failure")
            logger.warning(f"Stage 2 {display_name} attempt {attempt}/{MAX_MODEL_ATTEMPTS}: {last_error[:80]}")
        except httpx.TimeoutException:
            last_error = f"timeout (attempt {attempt})"
            logger.warning(f"Stage 2 {display_name} attempt {attempt}/{MAX_MODEL_ATTEMPTS}: timeout")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Stage 2 {display_name} attempt {attempt}/{MAX_MODEL_ATTEMPTS}: {last_error[:80]}")

        if attempt < MAX_MODEL_ATTEMPTS:
            wait = RETRY_BACKOFF[attempt - 1]
            logger.info(f"Stage 2 {display_name}: waiting {wait}s before retry...")
            await asyncio.sleep(wait)

    return {"model_key": model_key, "raw_text": None, "parsed": None, "error": f"Failed after {MAX_MODEL_ATTEMPTS} attempts: {last_error}"}


async def _run_all_models(product: dict, research_data: str) -> dict[str, dict]:
    """Run all 4 models in parallel. Returns results dict."""
    template = _load_prompt()
    results = {}
    async with httpx.AsyncClient() as client:
        tasks = {
            model_key: _call_model_with_retry(
                client, model_key,
                _build_prompt(template, product, research_data, MODEL_DISPLAY_NAMES[model_key])
            )
            for model_key in MODELS
        }
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for model_key, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            results[model_key] = {"model_key": model_key, "raw_text": None, "parsed": None, "error": str(result)}
        else:
            results[model_key] = result

    return results


async def run(product: dict, research_data: str) -> dict[str, dict]:
    """Run 4 LLM calls. ALL 4 must produce valid scores.

    If any model fails after MAX_MODEL_ATTEMPTS, waits 60s and retries the entire stage once.
    Raises ValueError only if all stage attempts are exhausted.
    """
    for stage_attempt in range(1, 3):  # 2 stage-level attempts max
        results = await _run_all_models(product, research_data)

        failed = [k for k, r in results.items() if r.get("error") or not r.get("parsed")]
        if not failed:
            logger.info(f"Stage 2 complete — all 4 models scored successfully")
            return results

        failure_summary = "; ".join(f"{k}: {results[k].get('error','unknown')[:60]}" for k in failed)
        logger.warning(f"Stage 2 attempt {stage_attempt}: {len(failed)} model(s) failed — {failure_summary}")

        if stage_attempt < 2:
            logger.info(f"Stage 2: waiting 60s then retrying entire stage...")
            await asyncio.sleep(60)

    # Final failure — all retries exhausted
    failed_models = [k for k, r in results.items() if r.get("error") or not r.get("parsed")]
    failure_detail = "; ".join(f"{k}: {results[k].get('error','unknown')}" for k in failed_models)
    raise ValueError(f"Stage 2 failed: {len(failed_models)}/4 models could not produce valid scores after all retries. {failure_detail}")
