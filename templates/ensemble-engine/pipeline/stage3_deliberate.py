"""Stage 3: Cross-review deliberation. No niche-specific changes needed."""

import asyncio
import json
import logging
from pathlib import Path

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_URL, MODELS, MODEL_DISPLAY_NAMES, LLM_TIMEOUT, LLM_MAX_TOKENS
from pipeline.validators import extract_openrouter_content, parse_llm_json, validate_score

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage2_deliberation.txt"


def _load_prompt() -> str:
    text = PROMPT_PATH.read_text()
    assert len(text) > 500, f"Stage 2 deliberation prompt too short ({len(text)} chars)"
    return text


def _build_deliberation_prompt(
    template: str, model_key: str, product: dict, stage2_results: dict[str, dict]
) -> str:
    display_name = MODEL_DISPLAY_NAMES[model_key]
    own_result = stage2_results.get(model_key, {})
    own_text = json.dumps(own_result.get("parsed") or {"error": "No Stage 2 output"}, indent=2)

    other_lines = []
    for k in MODELS:
        if k != model_key:
            other = stage2_results.get(k, {})
            other_parsed = other.get("parsed") or {"error": "No Stage 2 output"}
            other_lines.append(f"{MODEL_DISPLAY_NAMES[k]}: {json.dumps(other_parsed, indent=2)}")
            other_lines.append("")

    return template.format(
        own_analysis=own_text,
        other_analyses="\n".join(other_lines),
        llmName=display_name,
        productName=product["productName"],
        brand=product["brand"],
    )


async def _call_model(client: httpx.AsyncClient, model_key: str, prompt: str, attempt: int = 1) -> dict:
    """Call a single model for deliberation."""
    model_id = MODELS[model_key]
    display_name = MODEL_DISPLAY_NAMES[model_key]

    messages = []
    if model_key in ("grok", "gpt", "gemini"):
        messages.append({"role": "system", "content": "You are a senior analyst doing cross-model deliberation. Return ONLY valid JSON, no markdown fences."})
    messages.append({"role": "user", "content": prompt})

    body = {"model": model_id, "max_tokens": LLM_MAX_TOKENS, "messages": messages}
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
            return {"model_key": model_key, "raw_text": None, "parsed": None, "error": f"No content: {str(data)[:200]}"}

        parsed = parse_llm_json(raw_text, model_key)
        if parsed and validate_score(parsed, model_key):
            score = parsed.get("base_score") or parsed.get("total")
            logger.info(f"Stage 3 {display_name}: score={score}, tier={parsed.get('tier')}, verdict={parsed.get('consumer_verdict')}")
            return {"model_key": model_key, "raw_text": raw_text, "parsed": parsed, "error": None}
        else:
            return {"model_key": model_key, "raw_text": raw_text, "parsed": parsed, "error": "Invalid score or parse failure"}

    except httpx.TimeoutException:
        if attempt < 2:
            logger.warning(f"Stage 3 {display_name}: timeout, retrying...")
            return await _call_model(client, model_key, prompt, attempt + 1)
        return {"model_key": model_key, "raw_text": None, "parsed": None, "error": "Timeout after retry"}
    except Exception as e:
        if attempt < 2:
            logger.warning(f"Stage 3 {display_name}: error {e}, retrying...")
            await asyncio.sleep(2)
            return await _call_model(client, model_key, prompt, attempt + 1)
        return {"model_key": model_key, "raw_text": None, "parsed": None, "error": str(e)}


async def run(product: dict, stage2_results: dict[str, dict]) -> dict[str, dict]:
    """Run deliberation for all models that succeeded in Stage 2."""
    template = _load_prompt()
    eligible = {k: v for k, v in stage2_results.items() if v.get("parsed") and not v.get("error")}

    if len(eligible) < 3:
        raise ValueError(f"Only {len(eligible)} eligible models for deliberation (need 3)")

    results = {}
    async with httpx.AsyncClient() as client:
        tasks = {}
        for model_key in eligible:
            prompt = _build_deliberation_prompt(template, model_key, product, stage2_results)
            tasks[model_key] = _call_model(client, model_key, prompt)
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for model_key, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            results[model_key] = {"model_key": model_key, "raw_text": None, "parsed": None, "error": str(result)}
        else:
            results[model_key] = result

    for model_key in MODELS:
        if model_key not in eligible:
            results[model_key] = {"model_key": model_key, "raw_text": None, "parsed": None, "error": "Skipped — failed Stage 2"}

    return results
