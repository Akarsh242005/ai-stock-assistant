"""
============================================================
LSTM Forecasting Service
============================================================
Trains an LSTM neural network on historical stock data
and predicts next N days of closing prices.

Architecture:
  Input → LSTM(128) → Dropout(0.2) → LSTM(64) → Dense(1)

Uses MinMaxScaler for normalization + sliding window approach.
============================================================
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math
import os
import joblib
import json

# ─── Try importing TensorFlow ─────────────────────────────
try:
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


WINDOW_SIZE   = 60    # Look-back days
FORECAST_DAYS = 7     # Days to predict ahead
MODEL_DIR     = os.path.join(os.path.dirname(__file__), "../models")
os.makedirs(MODEL_DIR, exist_ok=True)


def prepare_sequences(data: np.ndarray, window: int):
    """
    Create sliding-window sequences for LSTM training.

    Returns:
        X: shape (n_samples, window, 1)
        y: shape (n_samples,)
    """
    X, y = [], []
    for i in range(window, len(data)):
        X.append(data[i - window:i, 0])
        y.append(data[i, 0])
    return np.array(X).reshape(-1, window, 1), np.array(y)


def build_lstm_model(window: int) -> "Sequential":
    """Build and compile LSTM model."""
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=(window, 1)),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mean_squared_error")
    return model


def train_and_predict(
    df: pd.DataFrame,
    symbol: str,
    epochs: int = 20,
    use_cache: bool = True,
) -> dict:
    """
    Train LSTM on historical close prices and forecast next days.

    Args:
        df:        DataFrame with 'Close' column
        symbol:    Stock symbol (used for model caching)
        epochs:    Training epochs (lower = faster, less accurate)
        use_cache: Load saved model weights if available

    Returns:
        dict with predictions, actuals, metrics, and forecast
    """
    if not TF_AVAILABLE:
        return _fallback_prediction(df, symbol)

    close = df["Close"].values.reshape(-1, 1)

    # ── Scale ─────────────────────────────────────────────
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(close)

    # ── Train / Test split (80/20) ─────────────────────────
    split    = int(len(scaled) * 0.8)
    train    = scaled[:split]
    test     = scaled[split:]

    X_train, y_train = prepare_sequences(train, WINDOW_SIZE)
    # For test we need window rows from training tail
    test_input       = scaled[split - WINDOW_SIZE:]
    X_test,  y_test  = prepare_sequences(test_input, WINDOW_SIZE)

    # ── Model ─────────────────────────────────────────────
    model_path = os.path.join(MODEL_DIR, f"lstm_{symbol.replace('.', '_')}.h5")
    model = None

    if use_cache and os.path.exists(model_path):
        try:
            model = load_model(model_path)
        except Exception as e:
            print(f"Error loading model for {symbol}: {e}. Retraining...")
            model = None

    if model is None:
        model = build_lstm_model(WINDOW_SIZE)
        early_stop = EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)
        model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=32,
            validation_split=0.1,
            callbacks=[early_stop],
            verbose=0,
        )
        model.save(model_path)

    # ── Test predictions ──────────────────────────────────
    pred_scaled = model.predict(X_test, verbose=0)
    predictions = scaler.inverse_transform(pred_scaled).flatten()
    actuals     = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()

    # ── Metrics ───────────────────────────────────────────
    rmse = math.sqrt(mean_squared_error(actuals, predictions))
    mae  = mean_absolute_error(actuals, predictions)
    mape = np.mean(np.abs((actuals - predictions) / actuals)) * 100

    # ── Future Forecast ───────────────────────────────────
    last_window = scaled[-WINDOW_SIZE:]
    forecast = []
    current  = last_window.copy()

    for _ in range(FORECAST_DAYS):
        x_pred = current.reshape(1, WINDOW_SIZE, 1)
        next_s = model.predict(x_pred, verbose=0)[0, 0]
        forecast.append(next_s)
        current = np.append(current[1:], [[next_s]], axis=0)

    forecast_prices = scaler.inverse_transform(
        np.array(forecast).reshape(-1, 1)
    ).flatten()

    # ── Date indices for frontend ─────────────────────────
    test_dates  = df.index[split:].strftime("%Y-%m-%d").tolist()
    if len(test_dates) > len(predictions):
        test_dates = test_dates[:len(predictions)]

    last_date    = pd.to_datetime(df.index[-1])
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                  periods=FORECAST_DAYS).strftime("%Y-%m-%d").tolist()

    direction = "UP" if forecast_prices[-1] > close[-1][0] else "DOWN"
    pct_change = ((forecast_prices[-1] - close[-1][0]) / close[-1][0]) * 100

    return {
        "model":        "LSTM",
        "test_dates":   test_dates,
        "actuals":      [round(float(v), 2) for v in actuals[:len(test_dates)]],
        "predictions":  [round(float(v), 2) for v in predictions[:len(test_dates)]],
        "forecast_dates": future_dates,
        "forecast":     [round(float(v), 2) for v in forecast_prices],
        "metrics": {
            "rmse": round(rmse, 4),
            "mae":  round(mae, 4),
            "mape": round(mape, 2),
        },
        "direction":    direction,
        "pct_change":   round(pct_change, 2),
        "current_price": round(float(close[-1][0]), 2),
    }


def _fallback_prediction(df: pd.DataFrame, symbol: str) -> dict:
    """
    Simple linear trend fallback when TensorFlow is unavailable.
    Used in demo / lightweight deployments.
    """
    close   = df["Close"].values
    n       = len(close)
    x       = np.arange(n)
    coeffs  = np.polyfit(x[-60:], close[-60:], 1)
    slope, intercept = coeffs

    forecast = [intercept + slope * (n + i) for i in range(FORECAST_DAYS)]
    actuals  = close[-30:].tolist()
    preds    = [intercept + slope * (n - 30 + i) for i in range(30)]

    test_dates    = df.index[-30:].strftime("%Y-%m-%d").tolist()
    last_date     = pd.to_datetime(df.index[-1])
    future_dates  = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                   periods=FORECAST_DAYS).strftime("%Y-%m-%d").tolist()

    rmse = math.sqrt(mean_squared_error(actuals, preds))
    mae  = mean_absolute_error(actuals, preds)

    direction  = "UP" if forecast[-1] > close[-1] else "DOWN"
    pct_change = ((forecast[-1] - close[-1]) / close[-1]) * 100

    return {
        "model":          "Linear Trend (LSTM fallback)",
        "test_dates":     test_dates,
        "actuals":        [round(float(v), 2) for v in actuals],
        "predictions":    [round(float(v), 2) for v in preds],
        "forecast_dates": future_dates,
        "forecast":       [round(float(v), 2) for v in forecast],
        "metrics": {
            "rmse": round(rmse, 4),
            "mae":  round(mae, 4),
            "mape": 0.0,
        },
        "direction":     direction,
        "pct_change":    round(pct_change, 2),
        "current_price": round(float(close[-1]), 2),
    }
