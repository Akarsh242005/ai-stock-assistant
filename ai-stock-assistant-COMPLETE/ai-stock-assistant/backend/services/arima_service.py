"""
============================================================
ARIMA Forecasting Service
============================================================
Auto-selects optimal (p, d, q) using ADF test + pmdarima.
Forecasts next N days of stock prices.

Pipeline:
  1. ADF Test for stationarity
  2. Auto-ARIMA for parameter selection
  3. Fit ARIMA(p, d, q)
  4. Generate forecast with confidence intervals
============================================================
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math

try:
    from statsmodels.tsa.stattools import adfuller
    from statsmodels.tsa.arima.model import ARIMA
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

try:
    import pmdarima as pm
    PMDARIMA_AVAILABLE = True
except ImportError:
    PMDARIMA_AVAILABLE = False


FORECAST_DAYS = 7


def run_adf_test(series: pd.Series) -> dict:
    """
    Augmented Dickey-Fuller test for stationarity.

    Returns:
        dict with test statistics and interpretation
    """
    if not STATSMODELS_AVAILABLE:
        return {"stationary": False, "reason": "statsmodels not installed"}

    result = adfuller(series.dropna(), autolag="AIC")
    is_stationary = result[1] < 0.05

    return {
        "test_stat":   round(result[0], 4),
        "p_value":     round(result[1], 4),
        "critical_1":  round(result[4]["1%"], 4),
        "critical_5":  round(result[4]["5%"], 4),
        "critical_10": round(result[4]["10%"], 4),
        "stationary":  is_stationary,
        "interpretation": (
            "Series is STATIONARY — no differencing needed (d=0)."
            if is_stationary else
            "Series is NON-STATIONARY — differencing required (d≥1)."
        )
    }


def forecast_with_arima(df: pd.DataFrame, symbol: str) -> dict:
    """
    Fit ARIMA model and generate price forecast.

    Strategy:
      - If pmdarima available: auto_arima for best (p,d,q)
      - Else: default ARIMA(1,1,1)
    """
    if not STATSMODELS_AVAILABLE:
        return _fallback_arima(df, symbol)

    close = df["Close"].dropna()
    log_close = np.log(close)   # Log-transform for variance stabilization

    # ── ADF test ──────────────────────────────────────────
    adf_result = run_adf_test(log_close)

    # ── Auto ARIMA ────────────────────────────────────────
    split = int(len(log_close) * 0.8)
    train = log_close.iloc[:split]
    test  = log_close.iloc[split:]

    if PMDARIMA_AVAILABLE:
        try:
            auto_model = pm.auto_arima(
                train,
                start_p=1, start_q=1,
                max_p=5,   max_q=5,
                d=None,                 # auto-detect differencing
                seasonal=False,
                information_criterion="aic",
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                max_order=None,
                n_jobs=-1,
            )
            order = auto_model.order
        except Exception:
            order = (1, 1, 1)
    else:
        order = (1, 1, 1)

    # ── Fit on train + predict test ───────────────────────
    try:
        model_fit = ARIMA(train, order=order).fit()

        # Rolling one-step-ahead forecast on test
        history = list(train)
        predictions_log = []

        for t in range(len(test)):
            temp_model = ARIMA(history, order=order)
            temp_fit   = temp_model.fit()
            yhat       = temp_fit.forecast(steps=1)[0]
            predictions_log.append(yhat)
            history.append(test.iloc[t])

        predictions = np.exp(predictions_log)
        actuals     = np.exp(test.values[:len(predictions)])

        # ── Metrics ───────────────────────────────────────
        rmse = math.sqrt(mean_squared_error(actuals, predictions))
        mae  = mean_absolute_error(actuals, predictions)
        mape = np.mean(np.abs((actuals - predictions) / (actuals + 1e-8))) * 100

        # ── Future forecast ───────────────────────────────
        final_model   = ARIMA(log_close, order=order).fit()
        fc_result     = final_model.get_forecast(steps=FORECAST_DAYS)
        fc_log        = fc_result.predicted_mean.values
        fc_ci_log     = fc_result.conf_int(alpha=0.05).values

        forecast       = np.exp(fc_log)
        forecast_upper = np.exp(fc_ci_log[:, 1])
        forecast_lower = np.exp(fc_ci_log[:, 0])

    except Exception as e:
        return _fallback_arima(df, symbol)

    test_dates   = close.index[split:split + len(predictions)].strftime("%Y-%m-%d").tolist()
    last_date    = pd.to_datetime(df.index[-1])
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                  periods=FORECAST_DAYS).strftime("%Y-%m-%d").tolist()

    current_price = float(close.iloc[-1])
    direction     = "UP" if forecast[-1] > current_price else "DOWN"
    pct_change    = ((forecast[-1] - current_price) / current_price) * 100

    return {
        "model":          f"ARIMA{order}",
        "order":          list(order),
        "test_dates":     test_dates,
        "actuals":        [round(float(v), 2) for v in actuals],
        "predictions":    [round(float(v), 2) for v in predictions],
        "forecast_dates": future_dates,
        "forecast":       [round(float(v), 2) for v in forecast],
        "forecast_upper": [round(float(v), 2) for v in forecast_upper],
        "forecast_lower": [round(float(v), 2) for v in forecast_lower],
        "metrics": {
            "rmse": round(rmse, 4),
            "mae":  round(mae, 4),
            "mape": round(mape, 2),
        },
        "adf_test":      adf_result,
        "direction":     direction,
        "pct_change":    round(pct_change, 2),
        "current_price": round(current_price, 2),
    }


def _fallback_arima(df: pd.DataFrame, symbol: str) -> dict:
    """Moving average fallback."""
    close      = df["Close"].values
    window     = 5
    ma         = pd.Series(close).rolling(window).mean().fillna(method="bfill").values
    actuals    = close[-30:].tolist()
    preds      = ma[-30:].tolist()
    test_dates = df.index[-30:].strftime("%Y-%m-%d").tolist()

    trend      = (ma[-1] - ma[-10]) / 10
    forecast   = [ma[-1] + trend * (i + 1) for i in range(FORECAST_DAYS)]
    last_date  = pd.to_datetime(df.index[-1])
    fut_dates  = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                periods=FORECAST_DAYS).strftime("%Y-%m-%d").tolist()
    rmse       = math.sqrt(mean_squared_error(actuals, preds))
    mae        = mean_absolute_error(actuals, preds)
    direction  = "UP" if forecast[-1] > close[-1] else "DOWN"
    pct_change = ((forecast[-1] - close[-1]) / close[-1]) * 100

    return {
        "model":          "Moving Average (ARIMA fallback)",
        "order":          [1, 1, 1],
        "test_dates":     test_dates,
        "actuals":        [round(float(v), 2) for v in actuals],
        "predictions":    [round(float(v), 2) for v in preds],
        "forecast_dates": fut_dates,
        "forecast":       [round(float(v), 2) for v in forecast],
        "forecast_upper": [round(float(v) * 1.02, 2) for v in forecast],
        "forecast_lower": [round(float(v) * 0.98, 2) for v in forecast],
        "metrics":        {"rmse": round(rmse, 4), "mae": round(mae, 4), "mape": 0.0},
        "adf_test":       {"stationary": False, "reason": "fallback mode"},
        "direction":      direction,
        "pct_change":     round(pct_change, 2),
        "current_price":  round(float(close[-1]), 2),
    }
