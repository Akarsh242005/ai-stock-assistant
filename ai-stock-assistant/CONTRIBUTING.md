# Contributing to AI StockVision

Thank you for considering a contribution! This guide explains how to set up your environment, run tests, and submit pull requests.

---

## Development Setup

```bash
git clone https://github.com/yourusername/ai-stock-assistant.git
cd ai-stock-assistant

# Create virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install deps + dev tools
pip install -r requirements.txt
pip install httpx pytest pytest-cov flake8 black pillow

# Verify setup
make test
```

---

## Project Layout

```
backend/
  services/     — Core ML/analysis logic (pure functions, no HTTP)
  routers/      — FastAPI route handlers (thin — delegate to services)
  tests/        — pytest suite (mirrors services/ structure)
  config.py     — Environment variable configuration
  main.py       — FastAPI app factory

scripts/        — CLI utilities (data pipeline, model training, alerts)
dashboard/      — Streamlit alternative UI
notebooks/      — Jupyter EDA and analysis
frontend/       — HTML/JS dashboard (standalone)
```

### Key design principle

Services are **pure Python functions** with no FastAPI imports. Routers are thin wrappers that call service functions. This keeps business logic testable without spinning up a server.

---

## Running Tests

```bash
# Full suite (65 tests)
pytest backend/tests/ -v

# Single test class
pytest backend/tests/test_backend.py::TestTechnicalAnalysisService -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

All tests use mocked data — no internet connection required.

---

## Adding a New Feature

### New forecasting model

1. Create `backend/services/mymodel_service.py`
2. Implement `forecast_with_mymodel(df, symbol) -> dict` returning the standard shape:
   ```python
   {
     "model": "MyModel",
     "test_dates": [...], "actuals": [...], "predictions": [...],
     "forecast_dates": [...], "forecast": [...],
     "metrics": {"rmse": float, "mae": float, "mape": float},
     "direction": "UP" | "DOWN",
     "pct_change": float,
     "current_price": float,
   }
   ```
3. Add a route in `backend/routers/forecast.py`
4. Write tests in `backend/tests/test_backend.py` (add a `TestMyModelService` class)
5. Update `frontend/index.html` to display the new model

### New technical indicator

1. Add a `compute_myindicator(close, **params) -> pd.Series` function in `technical_analysis.py`
2. Incorporate it into `generate_signal()` with a score contribution
3. Add it to the `indicators` dict in the return value
4. Write unit tests checking output range/shape

---

## Code Style

- **Python**: PEP 8, max line length 100
- **Docstrings**: triple-quoted, first line = one-sentence summary
- **Type hints**: use them for all public function signatures
- **Comments**: explain *why*, not *what*

Run linting before submitting:
```bash
flake8 backend/ scripts/ --max-line-length=100 --ignore=E501,W503,E402
```

---

## Pull Request Checklist

Before opening a PR, confirm:

- [ ] `make test` passes locally (all 65+ tests green)
- [ ] `make lint` produces no errors
- [ ] New code has corresponding tests
- [ ] Docstrings added to new public functions
- [ ] `requirements.txt` updated if new packages added
- [ ] PR description explains *what* changed and *why*

---

## Reporting Issues

Open a GitHub Issue with:
- Python version (`python --version`)
- Operating system
- Full error traceback
- Minimal reproduction steps

---

## Roadmap / Good First Issues

Looking for a place to start? These are open areas:

| Area | Description | Difficulty |
|------|-------------|------------|
| Tests | Add integration tests that call the real yfinance API | Easy |
| Indicators | Add Volume Profile, ATR, Stochastic RSI | Medium |
| Models | Add XGBoost directional classifier | Medium |
| Vision | Fine-tune EfficientNet on labeled chart images | Hard |
| Frontend | Add candlestick chart (OHLC) view | Medium |
| Alerts | Add Telegram bot integration | Easy |
| Docs | Add API usage examples to README | Easy |
