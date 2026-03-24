"""Configuration — loads all keys from ~/.config/env/global.env via python-dotenv."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load global env file
_env_path = Path.home() / ".config" / "env" / "global.env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    raise RuntimeError(f"Missing env file: {_env_path}")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in global.env")
if not BRAVE_API_KEY:
    raise RuntimeError("BRAVE_API_KEY not set in global.env — add it to ~/.config/env/global.env")
if not FIRECRAWL_API_KEY:
    raise RuntimeError("FIRECRAWL_API_KEY not set in global.env — add it to ~/.config/env/global.env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Models via OpenRouter
MODELS = {
    "claude": "anthropic/claude-sonnet-4.6",
    "gpt": "openai/o3",
    "gemini": "google/gemini-3.1-pro-preview",
    "grok": "x-ai/grok-4.20-beta",
}

# Synthesis model: one call per analysis (not 4 parallel) — worth Opus for better cross-model reasoning
SYNTHESIS_MODEL = "anthropic/claude-opus-4-5"
SYNTHESIS_MODEL_DISPLAY = "Claude Opus 4.5"

MODEL_DISPLAY_NAMES = {
    "claude": "Claude Sonnet 4.6",
    "gpt": "o3",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4.20",
}

LLM_TIMEOUT = 120  # seconds per model call
LLM_MAX_TOKENS = 4096

# Gemini thinking mode consumes max_tokens for its reasoning chain BEFORE output.
# At 4096, reasoning burns ~2k-3k tokens → JSON gets truncated → parse fails → no Gemini chip.
# Fix: give Gemini 8192 to ensure reasoning + full JSON output both fit.
MODEL_MAX_TOKENS = {
    "claude": 4096,
    "gpt": 4096,
    "gemini": 8192,  # thinking mode needs headroom
    "grok": 4096,
}
ANALYSIS_TIMEOUT_MINUTES = 10

# Concurrency: max parallel pipelines before queuing
MAX_CONCURRENT_ANALYSES = 2
