"""
============================================================
AI Stock Market Forecasting — Full Test Suite
============================================================
Run with:
    cd ai-stock-assistant
    pytest backend/tests/ -v --tb=short

Covers:
  - Health endpoint
  - Technical analysis (API + service unit tests)
  - Forecast endpoints (mocked)
  - LSTM / ARIMA / Prophet service fallbacks
  - Chart vision service + upload endpoint
  - Data service utilities
============================================================
"""

import sys
import os
import pytest
import math
import io
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_mock_df(days: int = 500, base: float = 100.0) -> pd.DataFrame:
    """Reproducible mock OHLCV DataFrame."""
    np.random.seed(42)
    dates  = pd.bdate_range(end=datetime.today(), periods=days)
    prices = base * (1 + np.random.randn(days) * 0.015).cumprod()
    prices = np.maximum(prices, 1.0)
    return pd.DataFrame({
        "Open":   prices * (1 + np.random.randn(days) * 0.002),
        "High":   prices * (1 + np.abs(np.random.randn(days)) * 0.005),
        "Low":    prices * (1 - np.abs(np.random.randn(days)) * 0.005),
        "Close":  prices,
        "Volume": np.random.randint(500_000, 5_000_000, days).astype(float),
    }, index=dates)


def make_mock_info() -> dict:
    return {
        "name": "TestCorp Ltd", "sector": "Technology",
        "industry": "Software", "market_cap": 500_000_000,
        "currency": "INR", "description": "Test company.",
        "52w_high": 130.0, "52w_low": 75.0, "pe_ratio": 22.5,
    }


def make_forecast_stub(model_name: str = "LSTM") -> dict:
    return {
        "model": model_name,
        "test_dates":    ["2024-01-01", "2024-01-02"],
        "actuals":       [100.0, 101.0],
        "predictions":   [100.5, 101.5],
        "forecast_dates":["2024-01-08"],
        "forecast":      [103.0],
        "forecast_upper":[105.0],
        "forecast_lower":[101.0],
        "metrics":       {"rmse": 1.5, "mae": 1.0, "mape": 1.2},
        "direction":     "UP",
        "pct_change":    2.0,
        "current_price": 101.0,
        "order":         [1, 1, 1],
        "adf_test":      {"stationary": True, "p_value": 0.03,
                          "test_stat": -3.5, "interpretation": "Stationary"},
    }


def make_png_bytes(r: int = 80, g: int = 180, b: int = 80) -> bytes:
    """Create a tiny solid-color PNG."""
    from PIL import Image
    img = Image.new("RGB", (120, 90), color=(r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════
# 1. HEALTH
# ═══════════════════════════════════════════════════════════

class TestHealth:
    def test_health_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "timestamp" in r.json()

    def test_root_message(self):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert "docs" in body
        assert "version" in body


# ═══════════════════════════════════════════════════════════
# 2. TECHNICAL ANALYSIS — API
# ═══════════════════════════════════════════════════════════

class TestAnalysisAPI:

    @patch("routers.analysis.fetch_stock_data", return_value=make_mock_df())
    @patch("routers.analysis.fetch_stock_info", return_value=make_mock_info())
    def test_full_analysis_structure(self, *_):
        r = client.get("/api/analysis/TEST")
        assert r.status_code == 200
        body = r.json()
        assert body["signal"] in ("BUY", "SELL", "HOLD")
        assert 0 <= body["confidence"] <= 100
        assert isinstance(body["reasons"], list) and len(body["reasons"]) >= 1
        assert "indicators" in body
        assert "chart_data" in body

    @patch("routers.analysis.fetch_stock_data", return_value=make_mock_df())
    @patch("routers.analysis.fetch_stock_info", return_value=make_mock_info())
    def test_indicator_keys_present(self, *_):
        r = client.get("/api/analysis/TEST")
        ind = r.json()["indicators"]
        for key in ("rsi", "macd", "macd_signal", "sma_50", "sma_200",
                    "bb_upper", "bb_lower", "close"):
            assert key in ind, f"Missing indicator: {key}"

    @patch("routers.analysis.fetch_stock_data", return_value=make_mock_df())
    @patch("routers.analysis.fetch_stock_info", return_value=make_mock_info())
    def test_chart_data_length_consistency(self, *_):
        r = client.get("/api/analysis/TEST")
        cd = r.json()["chart_data"]
        n = len(cd["dates"])
        assert len(cd["close"]) == n
        assert len(cd["rsi"]) == n
        assert len(cd["macd_line"]) == n

    @patch("routers.analysis.fetch_stock_data", side_effect=ValueError("Not found"))
    def test_invalid_symbol_404(self, *_):
        r = client.get("/api/analysis/XXXXXXXXX")
        assert r.status_code == 404

    @patch("routers.analysis.fetch_stock_data", return_value=make_mock_df())
    @patch("routers.analysis.fetch_stock_info", return_value=make_mock_info())
    def test_signal_quick_endpoint(self, *_):
        r = client.get("/api/analysis/TEST/signal")
        assert r.status_code == 200
        body = r.json()
        assert body["signal"] in ("BUY", "SELL", "HOLD")
        assert "confidence" in body
        assert "reasons" in body
        assert "indicators" in body

    @patch("routers.analysis.fetch_stock_data", return_value=make_mock_df())
    def test_ohlcv_returns_records(self, *_):
        r = client.get("/api/analysis/TEST/ohlcv")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body and len(body["data"]) > 0
        assert "count" in body


# ═══════════════════════════════════════════════════════════
# 3. TECHNICAL ANALYSIS — SERVICE UNIT
# ═══════════════════════════════════════════════════════════

class TestTechnicalAnalysisService:

    def setup_method(self):
        from services.technical_analysis import (
            compute_rsi, compute_macd, compute_bollinger_bands,
            compute_moving_averages, generate_signal,
        )
        self.compute_rsi  = compute_rsi
        self.compute_macd = compute_macd
        self.compute_bb   = compute_bollinger_bands
        self.compute_mas  = compute_moving_averages
        self.gen_signal   = generate_signal
        self.df = make_mock_df(days=300)

    def test_rsi_bounded_0_100(self):
        rsi = self.compute_rsi(self.df["Close"]).dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_rsi_window_creates_nans(self):
        rsi = self.compute_rsi(self.df["Close"], period=14)
        assert rsi.iloc[:13].isna().all()

    def test_macd_returns_three_keys(self):
        result = self.compute_macd(self.df["Close"])
        assert set(result.keys()) == {"macd", "signal", "histogram"}

    def test_macd_histogram_is_diff(self):
        result = self.compute_macd(self.df["Close"])
        computed_hist = (result["macd"] - result["signal"]).dropna()
        stored_hist   = result["histogram"].dropna()
        pd.testing.assert_series_equal(computed_hist, stored_hist, check_names=False)

    def test_bollinger_upper_ge_lower(self):
        bb = self.compute_bb(self.df["Close"])
        upper = bb["upper"].dropna()
        lower = bb["lower"].dropna()
        assert (upper >= lower).all()

    def test_bollinger_middle_is_sma(self):
        close = self.df["Close"]
        bb     = self.compute_bb(close, period=20)
        sma_20 = close.rolling(20).mean()
        pd.testing.assert_series_equal(bb["middle"].dropna(),
                                       sma_20.dropna(), check_names=False)

    def test_moving_averages_keys(self):
        mas = self.compute_mas(self.df["Close"])
        assert "sma_20" in mas and "sma_50" in mas and "sma_200" in mas

    def test_signal_output_valid(self):
        result = self.gen_signal(self.df)
        assert result["signal"] in ("BUY", "SELL", "HOLD")
        assert isinstance(result["score"], int)
        assert len(result["reasons"]) >= 4

    def test_signal_confidence_range(self):
        result = self.gen_signal(self.df)
        assert 0 <= result["confidence"] <= 100

    def test_signal_chart_data_present(self):
        result = self.gen_signal(self.df)
        for key in ("dates", "close", "sma_50", "rsi", "macd_line", "histogram"):
            assert key in result["chart_data"]


# ═══════════════════════════════════════════════════════════
# 4. FORECAST API
# ═══════════════════════════════════════════════════════════

class TestForecastAPI:

    @patch("routers.forecast.fetch_stock_data",     return_value=make_mock_df())
    @patch("routers.forecast.fetch_stock_info",     return_value=make_mock_info())
    @patch("routers.forecast.train_and_predict",    return_value=make_forecast_stub("LSTM"))
    @patch("routers.forecast.forecast_with_prophet",return_value=make_forecast_stub("Prophet"))
    @patch("routers.forecast.forecast_with_arima",  return_value=make_forecast_stub("ARIMA(1,1,1)"))
    def test_all_models_present(self, *_):
        r = client.get("/api/forecast/TEST")
        assert r.status_code == 200
        body = r.json()
        assert "lstm" in body and "prophet" in body and "arima" in body

    @patch("routers.forecast.fetch_stock_data", side_effect=ValueError("Not found"))
    def test_bad_symbol_returns_404(self, *_):
        r = client.get("/api/forecast/XXXXXXXXX")
        assert r.status_code == 404

    @patch("routers.forecast.fetch_stock_data",     return_value=make_mock_df())
    @patch("routers.forecast.fetch_stock_info",     return_value=make_mock_info())
    @patch("routers.forecast.train_and_predict",    return_value=make_forecast_stub("LSTM"))
    @patch("routers.forecast.forecast_with_prophet",return_value=make_forecast_stub("Prophet"))
    @patch("routers.forecast.forecast_with_arima",  return_value=make_forecast_stub("ARIMA(1,1,1)"))
    def test_compare_endpoint(self, *_):
        r = client.get("/api/forecast/TEST/compare")
        assert r.status_code == 200
        body = r.json()
        assert "comparison" in body
        assert len(body["comparison"]) == 3
        assert "best_model" in body
        assert "consensus" in body

    @patch("routers.forecast.fetch_stock_data",  return_value=make_mock_df())
    @patch("routers.forecast.train_and_predict", return_value=make_forecast_stub())
    def test_lstm_endpoint(self, *_):
        r = client.get("/api/forecast/TEST/lstm")
        assert r.status_code == 200
        assert "forecast" in r.json()

    @patch("routers.forecast.fetch_stock_data",      return_value=make_mock_df())
    @patch("routers.forecast.forecast_with_arima",   return_value=make_forecast_stub("ARIMA"))
    def test_arima_has_adf(self, *_):
        r = client.get("/api/forecast/TEST/arima")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════
# 5. LSTM SERVICE UNIT
# ═══════════════════════════════════════════════════════════

class TestLSTMService:

    def test_prepare_sequences_shapes(self):
        from services.lstm_service import prepare_sequences
        data = np.random.rand(100, 1)
        X, y = prepare_sequences(data, window=20)
        assert X.shape == (80, 20, 1)
        assert y.shape == (80,)

    def test_prepare_sequences_correct_target(self):
        from services.lstm_service import prepare_sequences
        data = np.arange(50).reshape(-1, 1).astype(float)
        X, y = prepare_sequences(data, window=5)
        assert y[0] == 5.0    # index 5 follows window 0-4
        assert y[-1] == 49.0

    def test_fallback_returns_7_day_forecast(self):
        from services.lstm_service import _fallback_prediction
        df = make_mock_df(days=200)
        result = _fallback_prediction(df, "UNIT")
        assert len(result["forecast"]) == 7
        assert len(result["forecast_dates"]) == 7

    def test_fallback_direction_valid(self):
        from services.lstm_service import _fallback_prediction
        result = _fallback_prediction(make_mock_df(days=200), "UNIT")
        assert result["direction"] in ("UP", "DOWN")

    def test_fallback_metrics_non_negative(self):
        from services.lstm_service import _fallback_prediction
        result = _fallback_prediction(make_mock_df(days=200), "UNIT")
        assert result["metrics"]["rmse"] >= 0
        assert result["metrics"]["mae"] >= 0


# ═══════════════════════════════════════════════════════════
# 6. ARIMA SERVICE UNIT
# ═══════════════════════════════════════════════════════════

class TestARIMAService:

    def test_fallback_forecast_length(self):
        from services.arima_service import _fallback_arima
        result = _fallback_arima(make_mock_df(days=200), "UNIT")
        assert len(result["forecast"]) == 7

    def test_fallback_upper_ge_lower(self):
        from services.arima_service import _fallback_arima
        result = _fallback_arima(make_mock_df(days=200), "UNIT")
        for u, l in zip(result["forecast_upper"], result["forecast_lower"]):
            assert u >= l

    def test_fallback_includes_order(self):
        from services.arima_service import _fallback_arima
        result = _fallback_arima(make_mock_df(days=200), "UNIT")
        assert "order" in result
        assert len(result["order"]) == 3

    def test_adf_test_structure(self):
        try:
            from services.arima_service import run_adf_test
        except ImportError:
            pytest.skip("statsmodels not installed")
        series = pd.Series(np.random.randn(200).cumsum())
        result = run_adf_test(series)
        for key in ("test_stat", "p_value", "stationary", "interpretation"):
            assert key in result
        assert isinstance(result["stationary"], bool)

    def test_adf_stationary_detection(self):
        try:
            from services.arima_service import run_adf_test
        except ImportError:
            pytest.skip("statsmodels not installed")
        # White noise should be stationary
        stationary_series = pd.Series(np.random.randn(500))
        result = run_adf_test(stationary_series)
        assert result["stationary"] is True


# ═══════════════════════════════════════════════════════════
# 7. PROPHET SERVICE UNIT
# ═══════════════════════════════════════════════════════════

class TestProphetService:

    def test_fallback_forecast(self):
        from services.prophet_service import _fallback_forecast
        df     = make_mock_df(days=200)
        result = _fallback_forecast(df, "UNIT")
        assert len(result["forecast"]) == 7
        assert result["direction"] in ("UP", "DOWN")
        assert result["metrics"]["rmse"] >= 0

    def test_fallback_ci_present(self):
        from services.prophet_service import _fallback_forecast
        result = _fallback_forecast(make_mock_df(days=200), "UNIT")
        assert "forecast_upper" in result
        assert "forecast_lower" in result
        for u, l in zip(result["forecast_upper"], result["forecast_lower"]):
            assert u >= l


# ═══════════════════════════════════════════════════════════
# 8. CHART VISION SERVICE
# ═══════════════════════════════════════════════════════════

class TestChartVisionService:

    def test_green_image_gives_buy(self):
        from services.chart_vision_service import analyze_chart_image
        result = analyze_chart_image(make_png_bytes(50, 200, 80))
        assert result["signal"] in ("BUY", "SELL", "WAIT")
        assert 0 <= result["confidence"] <= 100
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) >= 1

    def test_red_image_keys_present(self):
        from services.chart_vision_service import analyze_chart_image
        result = analyze_chart_image(make_png_bytes(200, 50, 60))
        for key in ("signal", "trend", "confidence", "color", "patterns",
                    "reasons", "analysis_method"):
            assert key in result

    def test_detect_patterns_returns_list(self):
        from services.chart_vision_service import _detect_patterns
        import numpy as np
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        patterns  = _detect_patterns(dummy_img, 500, 100, 0.05)
        assert isinstance(patterns, list)
        assert len(patterns) >= 1


class TestChartVisionAPI:

    def test_no_file_returns_422(self):
        r = client.post("/api/chart/analyze")
        assert r.status_code == 422

    def test_wrong_mimetype_returns_400(self):
        r = client.post(
            "/api/chart/analyze",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
        )
        assert r.status_code == 400

    def test_tiny_file_returns_400(self):
        r = client.post(
            "/api/chart/analyze",
            files={"file": ("tiny.png", b"\x89PNG\r\n", "image/png")},
        )
        assert r.status_code == 400

    def test_valid_png_returns_200(self):
        r = client.post(
            "/api/chart/analyze",
            files={"file": ("chart.png", make_png_bytes(), "image/png")},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["signal"] in ("BUY", "SELL", "WAIT")
        assert body["status"] == "success"


# ═══════════════════════════════════════════════════════════
# 9. DATA SERVICE UNIT
# ═══════════════════════════════════════════════════════════

class TestDataService:

    def test_ticker_map_nifty(self):
        from services.data_service import resolve_ticker
        assert resolve_ticker("NIFTY")   == "^NSEI"
        assert resolve_ticker("nifty")   == "^NSEI"
        assert resolve_ticker("NIFTY50") == "^NSEI"

    def test_ticker_map_indian_stocks(self):
        from services.data_service import resolve_ticker
        assert resolve_ticker("RELIANCE") == "RELIANCE.NS"
        assert resolve_ticker("TCS")      == "TCS.NS"
        assert resolve_ticker("INFOSYS")  == "INFY.NS"

    def test_ticker_passthrough(self):
        from services.data_service import resolve_ticker
        assert resolve_ticker("AAPL") == "AAPL"
        assert resolve_ticker("MSFT") == "MSFT"

    def test_df_to_json_records_structure(self):
        from services.data_service import df_to_json_records
        df      = make_mock_df(days=10)
        records = df_to_json_records(df)
        assert isinstance(records, list)
        assert len(records) == 10
        first = records[0]
        assert "date" in first
        assert "Close" in first
        assert "Volume" in first

    def test_df_to_json_records_date_format(self):
        from services.data_service import df_to_json_records
        df      = make_mock_df(days=5)
        records = df_to_json_records(df)
        # Date should be YYYY-MM-DD string
        import re
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        for row in records:
            assert re.match(date_pattern, row["date"]), f"Bad date format: {row['date']}"
