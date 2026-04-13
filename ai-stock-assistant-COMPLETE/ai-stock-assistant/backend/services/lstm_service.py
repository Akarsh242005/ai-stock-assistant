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

# TF is loaded dynamically to prevent boot timeout


WINDOW_SIZE   = 60    # Look-back days
FORECAST_DAYS = 7     # Days to predict ahead
MODEL_DIR     = os.path.join(os.path.dirname(__file__), "../models")
os.makedirs(MODEL_DIR, exist_ok=True)


def prepare_sequences(data: np.ndarray, window: int):
    """
    Create sliding-window sequences for Multi-Variate LSTM training.
    
    Args:
        data: shape (n_samples, n_features)
    Returns:
        X: shape (n_samples, window, n_features)
        y: Close price target (1st column)
    """
    X, y = [], []
    for i in range(window, len(data)):
        X.append(data[i - window:i, :])
        y.append(data[i, 0]) # Target is always Close
    return np.array(X), np.array(y)


def build_lstm_model(window: int, n_features: int = 3) -> "Sequential":
    """Build and compile a robust Multi-Variate LSTM model."""
    from tensorflow.keras.layers import BatchNormalization
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=(window, n_features)),
        BatchNormalization(),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        BatchNormalization(),
        Dropout(0.2),
        Dense(64, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="huber_loss") # Huber is robust to stock price spikes
    return model


def train_and_predict(
    df: pd.DataFrame,
    symbol: str,
    epochs: int = 20,
    use_cache: bool = True,
) -> dict:
    """
    Train Multi-Variate LSTM on Close + Volume + RSI.
    """
    if not TF_AVAILABLE:
        return _fallback_prediction(df, symbol)

    # --- Feature Engineering ---
    df_feat = df.copy()
    
    # Calculate RSI (14 period)
    import pandas_ta as ta
    df_feat['RSI'] = ta.rsi(df_feat['Close'], length=14)
    df_feat['RSI'].fillna(50, inplace=True) # Neutral fill
    
    # Select features: Close (Target), Volume, RSI
    features = ['Close', 'Volume', 'RSI']
    data = df_feat[features].values

    # --- Scale ---
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(data)

    # --- Train / Test split ---
    split = int(len(scaled) * 0.8)
    train = scaled[:split]
    test  = scaled[split:]

    X_train, y_train = prepare_sequences(train, WINDOW_SIZE)
    # For test we need window rows from training tail
    test_input = scaled[split - WINDOW_SIZE:]
    X_test, y_test = prepare_sequences(test_input, WINDOW_SIZE)

    # --- Model ---
    model_path = os.path.join(MODEL_DIR, f"lstm_mv_{symbol.replace('.', '_')}.h5")
    _should_train = False

    # Short-circuit if not enough data to train effectively
    if len(X_train) < WINDOW_SIZE:
        print(f"Data too sparse for {symbol} ({len(X_train)} samples). Using fallback.")
        return _fallback_prediction(df, symbol)

    if use_cache and os.path.exists(model_path):
        try:
            model = load_model(model_path)
        except Exception as e:
            print(f"Error loading LSTM model for {symbol}: {e}. Re-training...")
            model = build_lstm_model(WINDOW_SIZE, n_features=len(features))
            _should_train = True
    else:
        model = build_lstm_model(WINDOW_SIZE, n_features=len(features))
        _should_train = True

    if _should_train:
        # Reduced epochs for faster live analysis
        train_epochs = min(epochs, 5) 
        early_stop = EarlyStopping(monitor="val_loss", patience=2, restore_best_weights=True)
        model.fit(
            X_train, y_train,
            epochs=train_epochs,
            batch_size=32,
            validation_split=0.1,
            callbacks=[early_stop],
            verbose=0,
        )
        model.save(model_path)

    # --- Test predictions ---
    pred_scaled = model.predict(X_test, verbose=0)
    
    # Inverse Scale - only the Close price (column 0)
    # Create dummy array to inverse scale correctly
    dummy_pred = np.zeros((len(pred_scaled), len(features)))
    dummy_pred[:, 0] = pred_scaled.flatten()
    predictions = scaler.inverse_transform(dummy_pred)[:, 0]

    dummy_actual = np.zeros((len(y_test), len(features)))
    dummy_actual[:, 0] = y_test.flatten()
    actuals = scaler.inverse_transform(dummy_actual)[:, 0]

    # --- Metrics ---
    rmse = math.sqrt(mean_squared_error(actuals, predictions))
    mae = mean_absolute_error(actuals, predictions)
    mape = np.mean(np.abs((actuals - predictions) / (actuals + 1e-9))) * 100

    # --- Future Forecast ---
    last_window = scaled[-WINDOW_SIZE:]
    forecast = []
    current = last_window.copy()

    for _ in range(FORECAST_DAYS):
        x_pred = current.reshape(1, WINDOW_SIZE, len(features))
        next_s_scaled = model.predict(x_pred, verbose=0)[0, 0]
        
        # We only predict Close, so we hold other features constant for simplifaction in live forecast
        # or we could use the last known Volume/RSI. Here we take the last row and update Close.
        new_row = current[-1].copy()
        new_row[0] = next_s_scaled
        forecast.append(next_s_scaled)
        current = np.append(current[1:], [new_row], axis=0)

    # Inverse scale forecast
    dummy_f = np.zeros((len(forecast), len(features)))
    dummy_f[:, 0] = forecast
    forecast_prices = scaler.inverse_transform(dummy_f)[:, 0]

    # --- Date indices for frontend ---
    test_dates = df.index[split:].strftime("%Y-%m-%d").tolist()
    if len(test_dates) > len(predictions):
        test_dates = test_dates[:len(predictions)]

    last_date = pd.to_datetime(df.index[-1])
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1),
                                  periods=FORECAST_DAYS).strftime("%Y-%m-%d").tolist()

    current_price = float(df["Close"].iloc[-1])
    direction = "UP" if forecast_prices[-1] > current_price else "DOWN"
    pct_change = ((forecast_prices[-1] - current_price) / current_price) * 100

    return {
        "model": "Multi-Variate LSTM (P+V+RSI)",
        "test_dates": test_dates,
        "actuals": [round(float(v), 2) for v in actuals[:len(test_dates)]],
        "predictions": [round(float(v), 2) for v in predictions[:len(test_dates)]],
        "forecast_dates": future_dates,
        "forecast": [round(float(v), 2) for v in forecast_prices],
        "metrics": {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "mape": round(mape, 2),
        },
        "direction": direction,
        "pct_change": round(pct_change, 2),
        "current_price": round(current_price, 2),
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
