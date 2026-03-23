"""Configuration template — copy to config.py and customize for your niche.

REQUIRED CHANGES:
1. Set NICHE_NAME to your niche slug (e.g. "crypto-ratings", "restaurant-reviews")
2. Set PORT to a unique port (8001=glow-index, use 8002+ for new niches)
3. Optionally adjust MODELS if you want different model selection
4. Optionally adjust LLM_TIMEOUT, LLM_MAX_TOKENS, MAX_CONCURRENT_ANALYSES
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load global env file
_env_path = Path.home() / ".config" / "env" / "global.env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    raise RuntimeError(f"Missing env file: {_env_path}")

# ============================================================
# NICHE-SPECIFIC CONFIG — REPLACE THESE
# ============================================================

# Your niche slug — used in logging and LaunchAgent label
NICHE_NAME = "your-niche-slug"  # REPLACE (e.g. "crypto-ratings", "restaurant-reviews")

# Port — each niche needs a unique port
PORT = 8002  # REPLACE — 8001=glow-index, 8002=next, 8003=next...

# ============================================================
# API KEYS — loaded from global.env, no changes needed
# ============================================================

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in global.env")
if not BRAVE_API_KEY:
    raise RuntimeError("BRAVE_API_KEY not set in global.env — add it to ~/.config/env/global.env")
if not FIRECRAWL_API_KEY:
    raise RuntimeError("FIRECRAWL_API_KEY not set in global.env — add it to ~/.config/env/global.env")

# ============================================================
# API ENDPOINTS — no changes needed
# ============================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# ============================================================
# MODELS — adjust if you want different models
# ============================================================

# All models via OpenRouter. Verified available as of March 2026.
# Cost per ensemble analysis: ~$0.75-0.80 (13 LLM calls, ~31k max output tokens)
MODELS = {
    "claude": "anthropic/claude-sonnet-4.6",
    "gpt": "openai/o3",
    "gemini": "google/gemini-3.1-pro-preview",
    "grok": "x-ai/grok-4.20-beta",
}

MODEL_DISPLAY_NAMES = {
    "claude": "Claude Sonnet 4.6",
    "gpt": "o3",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4.20",
}

# ============================================================
# TUNING — adjust per niche needs
# ============================================================

LLM_TIMEOUT = 120  # seconds per model call
LLM_MAX_TOKENS = 4096  # max tokens per LLM response
ANALYSIS_TIMEOUT_MINUTES = 10  # auto-kill pipelines older than this
MAX_CONCURRENT_ANALYSES = 2  # max parallel pipelines before queuing
