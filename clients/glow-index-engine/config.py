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

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in global.env")
if not BRAVE_API_KEY:
    raise RuntimeError("BRAVE_API_KEY not set in global.env — add it to ~/.config/env/global.env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Models via OpenRouter
MODELS = {
    "claude": "anthropic/claude-sonnet-4.6",
    "gpt": "openai/o3",
    "gemini": "google/gemini-2.5-pro",
    "grok": "x-ai/grok-4",
}

MODEL_DISPLAY_NAMES = {
    "claude": "Claude Sonnet 4.6",
    "gpt": "GPT-5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
}

LLM_TIMEOUT = 120  # seconds per model call
LLM_MAX_TOKENS = 4096
ANALYSIS_TIMEOUT_MINUTES = 10
