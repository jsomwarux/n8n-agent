"""Validators for LLM responses and pipeline gates."""

import json
import logging
import re

logger = logging.getLogger(__name__)


def parse_llm_json(raw_text: str, model_key: str) -> dict:
    """Parse JSON from LLM response text. Handles markdown fences and extra content."""
    if not raw_text:
        return None
    text = raw_text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object from surrounding text
        try:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    logger.error(f"Failed to parse JSON from {model_key}: {text[:200]}")
    return None


def validate_score(parsed: dict, model_key: str) -> bool:
    """Validate that total score is a float in 0-100 range."""
    if not parsed:
        return False
    total = parsed.get("total")
    if total is None:
        logger.warning(f"{model_key}: missing 'total' field")
        return False
    try:
        val = float(total)
    except (TypeError, ValueError):
        logger.warning(f"{model_key}: 'total' is not numeric: {total}")
        return False
    if not (0.0 <= val <= 100.0):
        logger.warning(f"{model_key}: score {val} out of range 0-100")
        return False
    return True


def validate_stage2_minimum(results: dict) -> bool:
    """Check that at least 3 models produced valid Stage 2 results."""
    valid_count = sum(1 for v in results.values() if v is not None and validate_score(v, "s2"))
    return valid_count >= 3


def extract_openrouter_content(response_json: dict) -> str:
    """Extract content from OpenRouter response. ALL models use choices[0].message.content."""
    try:
        return response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        logger.warning(f"Unexpected OpenRouter response structure: {str(response_json)[:200]}")
        return None
