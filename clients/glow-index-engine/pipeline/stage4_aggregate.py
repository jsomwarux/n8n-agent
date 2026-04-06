"""Stage 4: Weighted consensus aggregation + Claude synthesis."""

import json
import logging
import math
from pathlib import Path
from typing import Optional

import httpx

from config import (
    MODEL_DISPLAY_NAMES,
    MODELS,
    OPENROUTER_API_KEY,
    OPENROUTER_URL,
    LLM_TIMEOUT,
    SYNTHESIS_MODEL,
)
from pipeline.validators import extract_openrouter_content, parse_llm_json

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage4_synthesis.txt"


def _anti_00(score: float) -> float:
    """If score ends in .00, adjust by a small amount to avoid false precision."""
    rounded = round(score, 2)
    if rounded == math.floor(rounded):
        rounded += 0.13
    return round(rounded, 2)


def _load_synthesis_prompt() -> str:
    text = SYNTHESIS_PROMPT_PATH.read_text()
    assert len(text) > 500, f"Stage 4 synthesis prompt too short ({len(text)} chars)"
    return text


def _format_stage3_outputs(stage3_results: dict[str, dict]) -> str:
    """Format all Stage 3 outputs as labeled JSON blocks for the synthesis prompt."""
    sections = []
    for model_key in MODELS:
        display_name = MODEL_DISPLAY_NAMES.get(model_key, model_key)
        result = stage3_results.get(model_key, {})
        parsed = result.get("parsed")
        if parsed and not result.get("error"):
            sections.append(f"### {display_name}\n```json\n{json.dumps(parsed, indent=2)}\n```")
        else:
            error = result.get("error", "No output")
            sections.append(f"### {display_name}\n[FAILED: {error}]")
    return "\n\n".join(sections)


async def _claude_synthesis(
    stage3_results: dict[str, dict],
    consensus_score: float,
    tier: str,
    product: dict,
) -> Optional[dict]:
    """Call Claude via OpenRouter to synthesize all 4 Stage 3 outputs into a consumer-facing summary."""
    try:
        template = _load_synthesis_prompt()
    except Exception as e:
        logger.warning(f"Stage 4 synthesis: failed to load prompt: {e}")
        return None

    stage3_text = _format_stage3_outputs(stage3_results)
    prompt = template.format(
        consensus_score=consensus_score,
        tier=tier,
        stage3_outputs=stage3_text,
        display_name=product.get("displayName", "Ranking"),
        entity_name=product.get("entityName", "product"),
    )

    model_id = SYNTHESIS_MODEL  # Claude Opus — one call per analysis, worth the upgrade
    body = {
        "model": model_id,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        async with httpx.AsyncClient() as client:
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
            logger.warning(f"Stage 4 synthesis: no content in response")
            return None

        parsed = parse_llm_json(raw_text, "claude")
        if not parsed:
            logger.warning(f"Stage 4 synthesis: JSON parse failed. Preview: {(raw_text or '')[:300]}")
            return None

        # Validate required fields
        required = ("final_reasoning", "key_findings", "verdict", "consensus_notes")
        missing = [f for f in required if f not in parsed]
        if missing:
            logger.warning(f"Stage 4 synthesis: missing fields {missing}")
            return None

        logger.info(f"Stage 4 synthesis: Claude produced {len(parsed.get('key_findings', []))} findings, verdict='{parsed.get('verdict', '')[:60]}'")
        return parsed

    except Exception as e:
        logger.warning(f"Stage 4 synthesis: Claude call failed: {e}")
        return None


async def run(
    stage2_results: dict[str, dict],
    stage3_results: dict[str, dict],
    product: dict,
) -> dict:
    """Compute weighted consensus from Stage 3 (deliberation) results,
    then call Claude for final synthesis.

    Falls back to Stage 2 scores for models that failed Stage 3.
    Falls back to stitched output if Claude synthesis fails.

    Returns full callback-ready payload.
    """
    def _get_score(parsed: dict) -> Optional[float]:
        """Extract score from parsed response — base_score preferred, total as fallback."""
        if not parsed:
            return None
        for field in ("base_score", "total"):
            val = parsed.get(field)
            if val is not None:
                try:
                    f = float(val)
                    if 0.0 <= f <= 100.0:
                        return f
                except (TypeError, ValueError):
                    pass
        return None

    # Collect final scores: prefer Stage 3, fall back to Stage 2
    model_scores = {}
    for model_key in stage2_results:
        s3 = stage3_results.get(model_key, {})
        s2 = stage2_results.get(model_key, {})
        # Defensive: s3/s2 could be non-dict if asyncio.gather returned an exception string
        if not isinstance(s3, dict): s3 = {}
        if not isinstance(s2, dict): s2 = {}
        parsed = s3.get("parsed") if (s3.get("parsed") and not s3.get("error")) else s2.get("parsed")
        score = _get_score(parsed)
        model_scores[model_key] = score  # None if failed

    valid_scores = {k: v for k, v in model_scores.items() if v is not None}

    if len(valid_scores) < 2:
        raise ValueError(f"Only {len(valid_scores)} valid scores for consensus (need at least 2)")
    if len(valid_scores) < 3:
        import logging; logging.getLogger(__name__).warning(f"Only {len(valid_scores)}/4 models scored — computing consensus from available models")

    # Weighted average: abs(score - median) > 15 → weight 0.5, else 1.0
    sorted_vals = sorted(valid_scores.values())
    n = len(sorted_vals)
    median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2 if n % 2 == 0 else sorted_vals[n // 2]

    weighted_sum = 0.0
    weight_total = 0.0
    for score in valid_scores.values():
        weight = 0.5 if abs(score - median) > 15 else 1.0
        weighted_sum += score * weight
        weight_total += weight

    consensus_score = _anti_00(weighted_sum / weight_total) if weight_total > 0 else 0.0

    # Tier
    if consensus_score >= 85:
        tier = "S+"
    elif consensus_score >= 75:
        tier = "S"
    elif consensus_score >= 65:
        tier = "A"
    elif consensus_score >= 50:
        tier = "B"
    else:
        tier = "C"

    # Consumer verdict: majority vote from Stage 3 (or Stage 2 fallback)
    VALID_VERDICTS = {"BUY_IT", "WORTH_IT_WITH_CAVEATS", "SKIP_IT"}
    verdicts = []
    for model_key in stage2_results:
        s3 = stage3_results.get(model_key, {})
        s2 = stage2_results.get(model_key, {})
        if not isinstance(s3, dict): s3 = {}
        if not isinstance(s2, dict): s2 = {}
        parsed = s3.get("parsed") if (s3.get("parsed") and not s3.get("error")) else s2.get("parsed")
        if parsed:
            v = parsed.get("consumer_verdict", "")
            if v in VALID_VERDICTS:
                verdicts.append(v)

    verdict_counts: dict[str, int] = {}
    for v in verdicts:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    consumer_verdict = max(verdict_counts, key=verdict_counts.get) if verdict_counts else "WORTH_IT_WITH_CAVEATS"

    # Build analyses array for callback
    analyses = []
    for model_key in stage2_results:
        display_name = MODEL_DISPLAY_NAMES.get(model_key, model_key)

        # Stage 1 (from stage2_results — the "parsed" contains the S1 analysis)
        s2 = stage2_results.get(model_key, {})
        s2_parsed = s2.get("parsed")
        if s2_parsed and not s2.get("error"):
            analyses.append({
                "llm": display_name,
                "stage": 1,
                "scores": s2_parsed.get("scores", {}),
                "total": _get_score(s2_parsed) or 0.0,
                "reasoning": s2_parsed.get("reasoning", ""),
                "key_findings": s2_parsed.get("key_findings", []),
                "red_flags": s2_parsed.get("red_flags", []),
                "best_dupe": s2_parsed.get("best_dupe"),
                "consumer_verdict": s2_parsed.get("consumer_verdict", ""),
                "best_for": s2_parsed.get("best_for", []),
                "skip_if": s2_parsed.get("skip_if", []),
                "how_to_use": s2_parsed.get("how_to_use", ""),
                "verdict": s2_parsed.get("verdict", ""),
            })

        # Stage 2 (from stage3_results — deliberation)
        s3 = stage3_results.get(model_key, {})
        s3_parsed = s3.get("parsed")
        if s3_parsed and not s3.get("error"):
            analyses.append({
                "llm": display_name,
                "stage": 2,
                "scores": s3_parsed.get("scores", {}),
                "total": _get_score(s3_parsed) or 0.0,
                "reasoning": s3_parsed.get("reasoning", ""),
                "key_findings": s3_parsed.get("key_findings", []),
                "red_flags": s3_parsed.get("red_flags", []),
                "best_dupe": s3_parsed.get("best_dupe"),
                "consumer_verdict": s3_parsed.get("consumer_verdict", ""),
                "confidence": s3_parsed.get("confidence", ""),
            })
        elif model_scores.get(model_key) is None:
            analyses.append({
                "llm": f"failed_{model_key}",
                "stage": 2,
                "scores": {},
                "total": 0,
                "reasoning": s3.get("error") or s2.get("error") or "Model failed",
            })

    # Claude synthesis call
    synthesis = await _claude_synthesis(stage3_results, consensus_score, tier, product)

    result = {
        "analyses": analyses,
        "consensusScore": consensus_score,
        "tier": tier,
        "consumerVerdict": consumer_verdict,
        "modelScores": {k: v for k, v in model_scores.items()},
    }

    if synthesis:
        result["final_reasoning"] = synthesis["final_reasoning"]
        result["key_findings"] = synthesis["key_findings"]
        result["red_flags"] = synthesis.get("red_flags", [])
        result["best_dupe"] = synthesis.get("best_dupe")
        result["verdict"] = synthesis["verdict"]
        result["consensus_notes"] = synthesis["consensus_notes"]
        result["synthesis_by"] = "claude"
        logger.info(f"Stage 4 consensus: score={consensus_score}, tier={tier}, verdict={consumer_verdict}, synthesis=claude")
    else:
        # Fallback: stitch from individual model outputs
        all_findings = []
        all_flags = []
        all_dupes = []
        for model_key in stage2_results:
            s3 = stage3_results.get(model_key, {})
            parsed = s3.get("parsed") if (s3.get("parsed") and not s3.get("error")) else stage2_results.get(model_key, {}).get("parsed")
            if parsed:
                all_findings.extend(parsed.get("key_findings", []))
                all_flags.extend(parsed.get("red_flags", []))
                dupe = parsed.get("best_dupe")
                if dupe:
                    all_dupes.append(dupe)

        # Dedupe by taking unique findings (simple dedup)
        seen = set()
        deduped_findings = []
        for f in all_findings:
            normalized = f.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                deduped_findings.append(f)

        seen_flags = set()
        deduped_flags = []
        for f in all_flags:
            normalized = f.strip().lower()
            if normalized not in seen_flags:
                seen_flags.add(normalized)
                deduped_flags.append(f)

        result["final_reasoning"] = ""
        result["key_findings"] = deduped_findings[:5]
        result["red_flags"] = deduped_flags[:5]
        result["best_dupe"] = all_dupes[0] if all_dupes else None
        result["verdict"] = ""
        result["consensus_notes"] = ""
        result["synthesis_by"] = "fallback"
        logger.info(f"Stage 4 consensus: score={consensus_score}, tier={tier}, verdict={consumer_verdict}, synthesis=fallback")

    return result
