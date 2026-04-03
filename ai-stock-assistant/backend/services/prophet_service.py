"""
============================================================
Facebook Prophet Forecasting Service
============================================================
Uses Meta's Prophet model to forecast stock prices with:
  - Yearly seasonality
  - Weekly seasonality
  - Holiday effects (Indian holidays)
  - Trend changepoints

Prophet excels at:
  - Handling missing data
  - Accounting for holidays
  - Providing uncertainty intervals
============================================================
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


FORECAST_DAYS = 7


def forecast_with_prophet(df: pd.DataFrame, symbol: str) -> dict:
    """
    Train Prophet model on stock data and generate forecast.
    """
    try:
        from prophet import Prophet
    except ImportError:
        return _fallback_forecast(df, symbol)

    # ── Prepare Prophet format: ds, y ─────────────────────
    prophet_df = df[["Close"]].copy()
    prophet_df = prophet_df.reset_index()
    prophet_df.columns = ["ds", "y"]
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"]).dt.tz_localize(None)

    # ── Train/test split (80/20) ──────────────────────────
    split     = int(len(prophet_df) * 0.8)
    train_df  = prophet_df.iloc[:split]
    test_df   = prophet_df.iloc[split:]

    # ── Build model ───────────────────────────────────────
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_mode="multiplicative",
    )

    # Add Indian market holidays
    indian_holidays = _get_indian_market_holidays()
    for name, dates in indian_holidays.items():
        model.add_country_holidays(country_name="IN")
        break  # Prophet handles this natively

    model.fit(train_df)

    # ── Predict on test period ────────────────────────────
    future_test = model.make_future_dataframe(periods=len(test_df), freq="B")
    forecast_all = model.predict(future_test)

    test_forecast = forecast_all.iloc[split:].reset_index(drop=True)
    predictions   = test_forecast["yhat"].values
    actuals       = test_df["y"].values[:len(predictions)]

    # ── Metrics ───────────────────────────────────────────
    rmse = math.sqrt(mean_squared_error(actuals, predictions))
    mae  = mean_absolute_error(actuals, predictions)
    mape = np.mean(np.abs((actuals - predictions) / (actuals + 1e-8))) * 100

    # ── Future Forecast ───────────────────────────────────
    future_df    = model.make_future_dataframe(periods=len(test_df) + FORECAST_DAYS, freq="B")
    forecast_out = model.predict(future_df)
    future_rows  = forecast_out.tail(FORECAST_DAYS)

    future_dates  = future_rows["ds"].dt.strftime("%Y-%m-%d").tolist()
    future_values = future_rows["yhat"].tolist()
    future_upper  = future_rows["yhat_upper"].tolist()
    future_lower  = future_rows["yhat_lower"].tolist()

    current_price = float(df["Close"].iloc[-1])
    direction     = "UP" if future_values[-1] > current_price else "DOWN"
    pct_change    = ((future_values[-1] - current_price) / current_price) * 100

    test_dates_list = test_df["ds"].dt.strftime("%Y-%m-%d").tolist()[:len(predictions)]

    return {
        "model":         "Prophet",
        "test_dates":    test_dates_list,
        "actuals":       [round(float(v), 2) for v in actuals],
        "predictions":   [round(float(v), 2) for v in predictions],
        "forecast_dates": future_dates,
        "forecast":      [round(float(v), 2) for v in future_values],
        "forecast_upper": [round(float(v), 2) for v in future_upper],
        "forecast_lower": [round(float(v), 2) for v in future_lower],
        "metrics": {
            "rmse": round(rmse, 4),
            "mae":  round(mae, 4),
            "mape": round(mape, 2),
        },
        "direction":     direction,
        "pct_change":    round(pct_change, 2),
        "current_price": round(current_price, 2),
        "components":    {
            "trend":      [round(v, 2) for v in forecast_all["trend"].tail(100).tolist()],
            "weekly":     [round(v, 4) for v in forecast_all.get("weekly", pd.Series([0]*len(forecast_all))).tail(100).tolist()],
        }
    }


def _fallback_forecast(df: pd.DataFrame, symbol: str) -> dict:
    """Exponential smoothing fallback if Prophet not installed."""
    close  = df["Close"].values
    alpha  = 0.3
    smooth = [close[0]]
    for v in close[1:]:
        smooth.append(alpha * v + (1 - alpha) * smooth[-1])

    last        = smooth[-1]
    trend       = (smooth[-1] - smooth[-10]) / 10
    forecast    = [last + trend * (i + 1) for i in range(FORECAST_DAYS)]
    actuals     = close[-30:].tolist()
    preds       = smooth[-30:]
    test_dates  = df.index[-30:].strftime("%Y-%m-%d").tolist()

    rmse = math.sqrt(mean_squared_error(actuals, preds))
    mae  = mean_absolute_error(actuals, preds)

    last_date    = pd.to_datetime(df.index[-1])
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                  periods=FORECAST_DAYS).strftime("%Y-%m-%d").tolist()

    direction  = "UP" if forecast[-1] > close[-1] else "DOWN"
    pct_change = ((forecast[-1] - close[-1]) / close[-1]) * 100

    return {
        "model":          "EMA Smoothing (Prophet fallback)",
        "test_dates":     test_dates,
        "actuals":        [round(float(v), 2) for v in actuals],
        "predictions":    [round(float(v), 2) for v in preds],
        "forecast_dates": future_dates,
        "forecast":       [round(float(v), 2) for v in forecast],
        "forecast_upper": [round(float(v) * 1.02, 2) for v in forecast],
        "forecast_lower": [round(float(v) * 0.98, 2) for v in forecast],
        "metrics": {
            "rmse": round(rmse, 4),
            "mae":  round(mae, 4),
            "mape": 0.0,
        },
        "direction":     direction,
        "pct_change":    round(pct_change, 2),
        "current_price": round(float(close[-1]), 2),
    }


def _get_indian_market_holidays() -> dict:
    """Returns major NSE market holidays (indicative)."""
    return {
        "Republic Day": ["2024-01-26"],
        "Holi": ["2024-03-25"],
        "Good Friday": ["2024-03-29"],
        "Ambedkar Jayanti": ["2024-04-14"],
        "Maharashtra Day": ["2024-05-01"],
        "Independence Day": ["2024-08-15"],
        "Ganesh Chaturthi": ["2024-09-07"],
        "Dussehra": ["2024-10-12"],
        "Diwali": ["2024-11-01"],
        "Christmas": ["2024-12-25"],
    }
