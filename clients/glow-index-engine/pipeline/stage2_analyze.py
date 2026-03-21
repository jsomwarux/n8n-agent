"""Stage 2: 4 parallel LLM calls for independent analysis."""

import asyncio
import logging
from datetime import date
from pathlib import Path

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_URL, MODELS, MODEL_DISPLAY_NAMES, LLM_TIMEOUT, LLM_MAX_TOKENS
from pipeline.validators import extract_openrouter_content, parse_llm_json, validate_score

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage1_analysis.txt"


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


async def _call_model(client: httpx.AsyncClient, model_key: str, prompt: str, attempt: int = 1) -> dict:
    """Call a single model via OpenRouter. Returns {model_key, raw_text, parsed, error}."""
    model_id = MODELS[model_key]
    display_name = MODEL_DISPLAY_NAMES[model_key]

    messages = []
    # Grok MUST have a system message or it refuses
    if model_key == "grok":
        messages.append({"role": "system", "content": "You are a senior skincare analyst and cosmetic chemist. Return ONLY valid JSON, no markdown fences."})
    elif model_key in ("gpt", "gemini"):
        messages.append({"role": "system", "content": "You are a senior skincare analyst and cosmetic chemist. Return ONLY valid JSON, no markdown fences."})
    messages.append({"role": "user", "content": prompt})

    body = {"model": model_id, "max_tokens": LLM_MAX_TOKENS, "messages": messages}
    # response_format json_object: only supported by OpenAI/Grok — NOT Gemini or Claude
    if model_key in ("gpt", "grok"):
        body["response_format"] = {"type": "json_object"}

    try:
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
            logger.warning(f"Stage 2 {display_name}: parse/validate failed. raw preview: {(raw_text or '')[:300]}")
            return {"model_key": model_key, "raw_text": raw_text, "parsed": parsed, "error": "Invalid score or parse failure"}

    except httpx.TimeoutException:
        if attempt < 2:
            logger.warning(f"Stage 2 {display_name}: timeout, retrying...")
            return await _call_model(client, model_key, prompt, attempt + 1)
        return {"model_key": model_key, "raw_text": None, "parsed": None, "error": "Timeout after retry"}
    except Exception as e:
        if attempt < 2:
            logger.warning(f"Stage 2 {display_name}: error {e}, retrying...")
            await asyncio.sleep(2)
            return await _call_model(client, model_key, prompt, attempt + 1)
        return {"model_key": model_key, "raw_text": None, "parsed": None, "error": str(e)}


async def run(product: dict, research_data: str) -> dict[str, dict]:
    """Run 4 LLM calls in parallel with the Stage 1 analysis prompt.

    Returns: {claude: {model_key, raw_text, parsed, error}, gpt: ..., gemini: ..., grok: ...}
    """
    template = _load_prompt()
    results = {}
    async with httpx.AsyncClient() as client:
        tasks = {}
        for model_key in MODELS:
            prompt = _build_prompt(template, product, research_data, MODEL_DISPLAY_NAMES[model_key])
            tasks[model_key] = _call_model(client, model_key, prompt)

        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for model_key, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            results[model_key] = {"model_key": model_key, "raw_text": None, "parsed": None, "error": str(result)}
        else:
            results[model_key] = result

    # Check minimum 3 valid models
    valid_count = sum(1 for r in results.values() if r.get("parsed") and not r.get("error"))
    if valid_count < 3:
        failed = [f"{k}: {r.get('error', 'unknown')}" for k, r in results.items() if r.get("error")]
        raise ValueError(f"Only {valid_count}/4 models succeeded (need 3). Failures: {'; '.join(failed)}")

    return results
