# ============================================================
# AI Stock Market Forecasting System — Makefile
# ============================================================
# Usage:
#   make install       Install all dependencies
#   make api           Start FastAPI backend
#   make test          Run pytest suite
#   make train         Train models for NIFTY
#   make fetch-data    Download and cache OHLCV data
#   make alerts        Run signal watcher (console only)
#   make docker-up     Start full stack via Docker
#   make lint          Run flake8 linting
#   make clean         Remove cache files
# ============================================================

PYTHON     := python3
VENV       := venv
PIP        := $(VENV)/bin/pip
UVICORN    := $(VENV)/bin/uvicorn
PYTEST     := $(VENV)/bin/pytest
STREAMLIT  := $(VENV)/bin/streamlit

.PHONY: all install api test train fetch-data alerts streamlit \
        docker-up docker-down lint clean help

# ── Default ───────────────────────────────────────────────
all: help

# ── Setup ─────────────────────────────────────────────────
install:
	@echo "→ Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "→ Upgrading pip..."
	$(PIP) install --upgrade pip --quiet
	@echo "→ Installing requirements..."
	$(PIP) install -r requirements.txt
	@echo "✓ Installation complete"
	@echo ""
	@echo "  Next: make api"

# ── Backend API ───────────────────────────────────────────
api:
	@echo "→ Starting FastAPI backend on http://localhost:8000"
	@echo "  Docs: http://localhost:8000/api/docs"
	cd backend && $(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

api-prod:
	cd backend && $(UVICORN) main:app --host 0.0.0.0 --port 8000 --workers 2

# ── Tests ─────────────────────────────────────────────────
test:
	@echo "→ Running test suite..."
	$(PYTEST) backend/tests/ -v --tb=short

test-cov:
	$(PYTEST) backend/tests/ -v --tb=short --cov=backend --cov-report=html
	@echo "→ Coverage report: htmlcov/index.html"

# ── Data pipeline ─────────────────────────────────────────
fetch-data:
	@echo "→ Fetching stock data for default watchlist..."
	$(PYTHON) scripts/fetch_data.py

fetch-data-custom:
	@echo "→ Fetching data for custom symbols..."
	$(PYTHON) scripts/fetch_data.py --symbols NIFTY RELIANCE TCS AAPL MSFT --period 2y

# ── Model training ────────────────────────────────────────
train:
	@echo "→ Training all models for NIFTY..."
	$(PYTHON) scripts/train_models.py --symbol NIFTY --epochs 20

train-all:
	@echo "→ Training models for full watchlist..."
	$(PYTHON) scripts/train_models.py --symbols NIFTY RELIANCE TCS AAPL MSFT --epochs 15

# ── Signal alerts ─────────────────────────────────────────
alerts:
	@echo "→ Starting signal alert watcher (NIFTY, RELIANCE, TCS)..."
	$(PYTHON) scripts/alert_service.py --symbols NIFTY RELIANCE TCS --interval 3600

alerts-once:
	@echo "→ Single scan for signals..."
	$(PYTHON) scripts/alert_service.py --symbols NIFTY RELIANCE TCS AAPL MSFT --once

# ── Streamlit dashboard ───────────────────────────────────
streamlit:
	@echo "→ Starting Streamlit dashboard on http://localhost:8501"
	$(STREAMLIT) run dashboard/streamlit_app.py

# ── Docker ────────────────────────────────────────────────
docker-up:
	@echo "→ Starting full stack with Docker..."
	docker-compose up --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# ── Lint ──────────────────────────────────────────────────
lint:
	$(VENV)/bin/flake8 backend/ scripts/ --max-line-length=100 \
	  --exclude=__pycache__,.venv,venv \
	  --ignore=E501,W503

# ── Clean ─────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned cache files"

clean-models:
	rm -f backend/models/*.h5 models/*.h5
	@echo "✓ Cleared saved model weights"

clean-data:
	rm -f data/*.parquet data/*.csv data/summary.json
	@echo "✓ Cleared cached data files"

# ── Help ──────────────────────────────────────────────────
help:
	@echo ""
	@echo "  AI StockVision — Developer Commands"
	@echo "  ══════════════════════════════════════"
	@echo ""
	@echo "  Setup"
	@echo "    make install        Install all Python dependencies"
	@echo ""
	@echo "  Run"
	@echo "    make api            Start FastAPI backend (dev, auto-reload)"
	@echo "    make api-prod       Start FastAPI backend (production)"
	@echo "    make streamlit      Start Streamlit dashboard"
	@echo ""
	@echo "  Data & Models"
	@echo "    make fetch-data     Download OHLCV data for watchlist"
	@echo "    make train          Train all models for NIFTY"
	@echo "    make train-all      Train models for full watchlist"
	@echo ""
	@echo "  Alerts"
	@echo "    make alerts         Start real-time signal watcher (loop)"
	@echo "    make alerts-once    Run single scan and print results"
	@echo ""
	@echo "  Testing"
	@echo "    make test           Run pytest suite (65 tests)"
	@echo "    make test-cov       Run tests + HTML coverage report"
	@echo "    make lint           Run flake8 linting"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-up      docker-compose up --build"
	@echo "    make docker-down    docker-compose down"
	@echo ""
	@echo "  Cleanup"
	@echo "    make clean          Remove Python cache files"
	@echo "    make clean-models   Remove saved .h5 model weights"
	@echo "    make clean-data     Remove cached parquet files"
	@echo ""
