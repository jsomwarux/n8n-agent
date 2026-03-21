"""Stage 4: Weighted consensus aggregation."""

import logging
import math
from typing import Optional

from config import MODEL_DISPLAY_NAMES

logger = logging.getLogger(__name__)


def _anti_00(score: float) -> float:
    """If score ends in .00, adjust by a small amount to avoid false precision."""
    rounded = round(score, 2)
    if rounded == math.floor(rounded):
        # Ends in .00 — adjust by +0.13 (arbitrary small nudge)
        rounded += 0.13
    return round(rounded, 2)


def run(
    stage2_results: dict[str, dict],
    stage3_results: dict[str, dict],
    product: dict,
) -> dict:
    """Compute weighted consensus from Stage 3 (deliberation) results.

    Falls back to Stage 2 scores for models that failed Stage 3.

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
        parsed = s3.get("parsed") if (s3.get("parsed") and not s3.get("error")) else s2.get("parsed")
        score = _get_score(parsed)
        model_scores[model_key] = score  # None if failed

    valid_scores = {k: v for k, v in model_scores.items() if v is not None}

    if len(valid_scores) < 3:
        raise ValueError(f"Only {len(valid_scores)} valid scores for consensus (need 3)")

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
    # Valid values: BUY_IT, WORTH_IT_WITH_CAVEATS, SKIP_IT
    VALID_VERDICTS = {"BUY_IT", "WORTH_IT_WITH_CAVEATS", "SKIP_IT"}
    verdicts = []
    for model_key in stage2_results:
        s3 = stage3_results.get(model_key, {})
        s2 = stage2_results.get(model_key, {})
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

    logger.info(f"Stage 4 consensus: score={consensus_score}, tier={tier}, verdict={consumer_verdict}")

    return {
        "analyses": analyses,
        "consensusScore": consensus_score,
        "tier": tier,
        "consumerVerdict": consumer_verdict,
        "modelScores": {k: v for k, v in model_scores.items()},
    }
