"""
============================================================
Backend Configuration
============================================================
Loads settings from environment variables / .env file.
Import this module in any service to access config.
============================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if it exists (dev convenience)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# ── API ───────────────────────────────────────────────────
API_HOST        = os.getenv("API_HOST", "0.0.0.0")
API_PORT        = int(os.getenv("API_PORT", 8000))
CORS_ORIGINS    = os.getenv("CORS_ORIGINS", "*").split(",")

# ── Model ─────────────────────────────────────────────────
LSTM_WINDOW_SIZE   = int(os.getenv("LSTM_WINDOW_SIZE", 60))
LSTM_FORECAST_DAYS = int(os.getenv("LSTM_FORECAST_DAYS", 7))
LSTM_EPOCHS        = int(os.getenv("LSTM_EPOCHS", 20))
LSTM_BATCH_SIZE    = int(os.getenv("LSTM_BATCH_SIZE", 32))
LSTM_USE_CACHE     = os.getenv("LSTM_USE_CACHE", "true").lower() == "true"

# ── Data ──────────────────────────────────────────────────
DEFAULT_PERIOD   = os.getenv("DEFAULT_PERIOD", "2y")
DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL", "1d")

# ── Chart Vision ──────────────────────────────────────────
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 10))

# ── Paths ─────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
MODEL_DIR  = BASE_DIR / "models"
DATA_DIR   = BASE_DIR / "data"
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── API Keys ──────────────────────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
