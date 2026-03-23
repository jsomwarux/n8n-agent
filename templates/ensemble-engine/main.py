"""FastAPI app — /analyze endpoint, background task runner, force-reset, auto-timeout.

Copy this file as-is. No niche-specific changes needed — reads PORT from config.py.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import config  # noqa: F401
from config import MAX_CONCURRENT_ANALYSES
from callback import send_callback, send_failure_callback
from pipeline import stage1_collect, stage2_analyze, stage3_deliberate, stage4_aggregate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

running_analyses: dict[str, dict] = {}
analysis_queue: list[tuple[str, object]] = []
_pipeline_semaphore: object = None

STAGE_NAMES = {
    1: "Collecting research data",
    2: "Running 4-model analysis",
    3: "Cross-model deliberation",
    4: "Computing consensus score",
}

def _set_stage(run_id: str, stage: int):
    if run_id in running_analyses:
        running_analyses[run_id]["stage"] = stage
        running_analyses[run_id]["stage_name"] = STAGE_NAMES.get(stage, "Processing")
        running_analyses[run_id]["stage_started_at"] = time.time()

_timeout_task: object = None


async def _timeout_poller():
    """Every 60s, check for analyses running > timeout and auto-reset them."""
    while True:
        await asyncio.sleep(60)
        now = time.time()
        timed_out = []
        for run_id, info in list(running_analyses.items()):
            elapsed_min = (now - info["started_at"]) / 60
            if elapsed_min > config.ANALYSIS_TIMEOUT_MINUTES:
                timed_out.append(run_id)
        for run_id in timed_out:
            info = running_analyses.pop(run_id, None)
            if info:
                logger.warning(f"Auto-timeout: {run_id} ran for >{config.ANALYSIS_TIMEOUT_MINUTES} min")
                asyncio.create_task(
                    send_failure_callback(
                        info.get("callback_url", ""),
                        info.get("callback_secret", ""),
                        info.get("product_id", ""),
                        run_id,
                        f"Analysis timed out after {config.ANALYSIS_TIMEOUT_MINUTES} minutes",
                    )
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _timeout_task, _pipeline_semaphore
    _pipeline_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)
    _timeout_task = asyncio.create_task(_timeout_poller())
    logger.info(f"{config.NICHE_NAME} engine started — max {MAX_CONCURRENT_ANALYSES} concurrent analyses")
    yield
    if _timeout_task:
        _timeout_task.cancel()


app = FastAPI(title=f"{config.NICHE_NAME} Ensemble Engine", version="2.0.0", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    productId: str
    productName: str
    brand: str
    category: str = ""
    priceUsd: float = 0.0
    callbackUrl: str = ""
    callbackSecret: str = ""
    runId: str = ""


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Accept analysis request, run pipeline in background, return immediately."""
    run_id = req.runId or str(uuid.uuid4())
    analysis_queue.append((run_id, req))
    asyncio.create_task(_queue_worker())

    queue_pos = len(analysis_queue)
    active = len(running_analyses)
    msg = "Analysis pipeline started" if active < MAX_CONCURRENT_ANALYSES else f"Queued (position {queue_pos}, {active} running)"
    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "runId": run_id, "message": msg, "queuePosition": queue_pos},
    )


async def _queue_worker():
    """Drain the queue one item at a time, respecting the semaphore."""
    if not analysis_queue:
        return
    async with _pipeline_semaphore:
        if not analysis_queue:
            return
        run_id, req = analysis_queue.pop(0)
        await _run_pipeline(run_id, req)


async def _run_pipeline(run_id: str, req: AnalyzeRequest):
    """Full pipeline: collect -> analyze -> deliberate -> aggregate -> callback."""
    running_analyses[run_id] = {
        "started_at": time.time(),
        "product_id": req.productId,
        "product_name": req.productName,
        "brand": req.brand,
        "callback_url": req.callbackUrl,
        "callback_secret": req.callbackSecret,
        "stage": 0,
        "stage_name": "Starting",
        "stage_started_at": time.time(),
    }

    product = {
        "productId": req.productId,
        "productName": req.productName,
        "brand": req.brand,
        "category": req.category,
        "priceUsd": req.priceUsd,
    }
    start_time = time.time()

    try:
        _set_stage(run_id, 1)
        logger.info(f"[{run_id}] Stage 1: Collecting research data for {req.productName} by {req.brand}")
        collection = await stage1_collect.run(req.productName, req.brand, price_usd=req.priceUsd)
        research_data = collection["research_data"]

        _set_stage(run_id, 2)
        logger.info(f"[{run_id}] Stage 2: Running 4 LLM analyses")
        s2_results = await stage2_analyze.run(product, research_data)

        _set_stage(run_id, 3)
        logger.info(f"[{run_id}] Stage 3: Running deliberation")
        s3_results = await stage3_deliberate.run(product, s2_results)

        _set_stage(run_id, 4)
        logger.info(f"[{run_id}] Stage 4: Computing consensus")
        aggregated = stage4_aggregate.run(s2_results, s3_results, product)

        elapsed = round(time.time() - start_time, 1)
        logger.info(f"[{run_id}] Pipeline complete in {elapsed}s — consensus={aggregated['consensusScore']}, tier={aggregated['tier']}")

        callback_payload = {
            "secret": req.callbackSecret,
            "productId": req.productId,
            "runId": run_id,
            "analyses": aggregated["analyses"],
            "consensusScore": aggregated["consensusScore"],
            "tier": aggregated["tier"],
        }

        if req.callbackUrl:
            await send_callback(req.callbackUrl, callback_payload)
        else:
            logger.info(f"[{run_id}] No callbackUrl — result available via /status/{run_id}")

    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        logger.error(f"[{run_id}] Pipeline failed after {elapsed}s: {e}")
        if req.callbackUrl:
            await send_failure_callback(
                req.callbackUrl, req.callbackSecret, req.productId, run_id, str(e)
            )
    finally:
        running_analyses.pop(run_id, None)


@app.post("/force-reset/{run_id}")
async def force_reset(run_id: str):
    """Force-reset a running analysis."""
    info = running_analyses.pop(run_id, None)
    if not info:
        raise HTTPException(status_code=404, detail=f"No running analysis with runId={run_id}")
    logger.warning(f"Force-reset: {run_id}")
    if info.get("callback_url"):
        asyncio.create_task(
            send_failure_callback(
                info["callback_url"], info.get("callback_secret", ""), info.get("product_id", ""), run_id, "Analysis force-reset by operator",
            )
        )
    return {"status": "reset", "runId": run_id}


@app.get("/status")
async def status():
    """List all running analyses with stage progress."""
    now = time.time()
    return {
        "running": {
            run_id: {
                "product_id": info["product_id"],
                "product_name": info.get("product_name", ""),
                "brand": info.get("brand", ""),
                "stage": info.get("stage", 0),
                "stage_name": info.get("stage_name", "Starting"),
                "total_stages": 4,
                "elapsed_seconds": round(now - info["started_at"], 1),
                "stage_elapsed_seconds": round(now - info.get("stage_started_at", info["started_at"]), 1),
            }
            for run_id, info in running_analyses.items()
        },
        "count": len(running_analyses),
        "queued": len(analysis_queue),
        "max_concurrent": MAX_CONCURRENT_ANALYSES,
        "queue": [
            {"runId": rid, "product_name": r.productName, "brand": r.brand}
            for rid, r in analysis_queue
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "niche": config.NICHE_NAME, "version": "2.0.0", "timestamp": datetime.utcnow().isoformat()}
