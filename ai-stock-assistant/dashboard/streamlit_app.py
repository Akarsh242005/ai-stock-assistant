"""
============================================================
AI Stock Market Forecasting — Streamlit Dashboard
============================================================
Alternative lightweight deployment using Streamlit.
Run: streamlit run dashboard/streamlit_app.py
Deploy free: streamlit.io/cloud
============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Allow importing backend services
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

# ── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title="AI StockVision",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #080c10; color: #e6edf3; }
    .metric-card {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 16px; text-align: center;
    }
    .signal-buy  { color: #00e5a0; font-size: 2rem; font-weight: bold; }
    .signal-sell { color: #ff3860; font-size: 2rem; font-weight: bold; }
    .signal-hold { color: #ffb300; font-size: 2rem; font-weight: bold; }
    .stSelectbox label, .stSlider label { color: #8b949e !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⬡ AI StockVision")
    st.markdown("*Forecasting & Trading Assistant*")
    st.divider()

    symbol = st.selectbox("Select Symbol", [
        "^NSEI (NIFTY)",
        "RELIANCE.NS",
        "TCS.NS",
        "INFOSYS.NS (INFY)",
        "AAPL",
        "MSFT",
        "TSLA",
        "Custom...",
    ])

    if symbol == "Custom...":
        symbol = st.text_input("Enter ticker:", "^NSEI")
    else:
        symbol = symbol.split()[0]

    period = st.selectbox("Data Period", ["6mo", "1y", "2y", "5y"], index=2)

    analyze = st.button("▶ ANALYZE", use_container_width=True, type="primary")

    st.divider()
    st.markdown("#### Models")
    use_lstm    = st.checkbox("LSTM", value=True)
    use_prophet = st.checkbox("Prophet", value=True)
    use_arima   = st.checkbox("ARIMA", value=True)

    st.divider()
    st.caption("Data: Yahoo Finance | For educational use only")


# ── Main Area ─────────────────────────────────────────────
st.title("AI Stock Market Forecasting System")
st.caption("LSTM · Prophet · ARIMA · Technical Analysis · Chart Vision")

if not analyze:
    # Welcome state
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info("🧠 LSTM Deep Learning")
        st.caption("2-layer LSTM with 60-day lookback window")
    with col2:
        st.info("📊 Prophet Forecasting")
        st.caption("Trend + seasonality decomposition")
    with col3:
        st.info("📉 ARIMA Model")
        st.caption("Auto-selected p,d,q via ADF test")
    with col4:
        st.info("👁️ Chart Vision AI")
        st.caption("OpenCV candlestick analysis")
    st.stop()


# ── Load data ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data(sym, per):
    try:
        from services.data_service import fetch_stock_data, fetch_stock_info
        df   = fetch_stock_data(sym, period=per)
        info = fetch_stock_info(sym)
        return df, info
    except Exception as e:
        st.error(f"Data fetch error: {e}")
        return None, {}

@st.cache_data(ttl=300)
def run_analysis(sym, per):
    try:
        from services.data_service       import fetch_stock_data
        from services.technical_analysis import generate_signal
        df = fetch_stock_data(sym, period=per)
        return generate_signal(df), df
    except Exception as e:
        return None, None

@st.cache_data(ttl=600)
def run_forecast(sym, per):
    try:
        from services.data_service    import fetch_stock_data
        from services.lstm_service    import train_and_predict
        from services.prophet_service import forecast_with_prophet
        from services.arima_service   import forecast_with_arima
        df = fetch_stock_data(sym, period=per)
        return {
            'lstm':    train_and_predict(df, sym, epochs=15),
            'prophet': forecast_with_prophet(df, sym),
            'arima':   forecast_with_arima(df, sym),
        }
    except Exception as e:
        st.error(f"Forecast error: {e}")
        return None


# ── Run Analysis ──────────────────────────────────────────
with st.spinner(f"Fetching data for {symbol}..."):
    df, info = load_data(symbol, period)

if df is None:
    st.error("Could not fetch data. Check symbol or API connection.")
    st.stop()

with st.spinner("Running analysis..."):
    analysis, _ = run_analysis(symbol, period)

# ── Metrics Row ───────────────────────────────────────────
st.subheader(f"📊 {info.get('name', symbol)}")

col1, col2, col3, col4, col5 = st.columns(5)
close = float(df['Close'].iloc[-1])

with col1:
    st.metric("Current Price", f"₹{close:,.2f}")
with col2:
    signal = analysis['signal'] if analysis else 'N/A'
    color  = "🟢" if signal=="BUY" else "🔴" if signal=="SELL" else "🟡"
    st.metric("Signal", f"{color} {signal}")
with col3:
    st.metric("52W High", f"₹{info.get('52w_high', 0):,.2f}" if info.get('52w_high') else "N/A")
with col4:
    st.metric("52W Low", f"₹{info.get('52w_low', 0):,.2f}" if info.get('52w_low') else "N/A")
with col5:
    st.metric("P/E Ratio", f"{info.get('pe_ratio', 0):.1f}" if info.get('pe_ratio') else "N/A")

st.divider()

# ── Tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 Technical Analysis", "🔮 Forecasting", "⚖️ Model Comparison", "👁️ Chart Vision"])

# ── Tab 1: Technical Analysis ─────────────────────────────
with tab1:
    if analysis:
        cd = analysis['chart_data']

        # Indicator chips
        cols = st.columns(7)
        inds = [
            ("RSI (14)", analysis['indicators']['rsi']),
            ("MACD", analysis['indicators']['macd']),
            ("Signal", analysis['indicators']['macd_signal']),
            ("SMA 50", analysis['indicators']['sma_50']),
            ("SMA 200", analysis['indicators']['sma_200']),
            ("BB Upper", analysis['indicators']['bb_upper']),
            ("BB Lower", analysis['indicators']['bb_lower']),
        ]
        for col, (label, val) in zip(cols, inds):
            col.metric(label, f"{val:.2f}")

        st.divider()

        # Price + BB chart
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.22, 0.23],
            subplot_titles=['Price + Bollinger Bands + SMAs', 'RSI (14)', 'MACD'])

        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['close'], name='Close',
            line=dict(color='#00b8ff', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['sma_50'], name='SMA50',
            line=dict(color='#ffb300', dash='dot', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['sma_200'], name='SMA200',
            line=dict(color='#a78bfa', dash='dash', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['bb_upper'], name='BB Upper',
            line=dict(color='rgba(0,229,160,0.4)', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['bb_lower'], name='BB Lower',
            line=dict(color='rgba(0,229,160,0.4)', width=1),
            fill='tonexty', fillcolor='rgba(0,229,160,0.05)'), row=1, col=1)

        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['rsi'], name='RSI',
            line=dict(color='#a78bfa', width=2)), row=2, col=1)
        fig.add_hline(y=70, line_dash='dot', line_color='rgba(255,56,96,0.5)', row=2, col=1)
        fig.add_hline(y=30, line_dash='dot', line_color='rgba(0,229,160,0.5)', row=2, col=1)

        colors_hist = ['rgba(0,229,160,0.7)' if (v or 0) >= 0 else 'rgba(255,56,96,0.7)'
                       for v in (cd['histogram'] or [])]
        fig.add_trace(go.Bar(x=cd['dates'], y=cd['histogram'], name='Histogram',
            marker_color=colors_hist), row=3, col=1)
        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['macd_line'], name='MACD',
            line=dict(color='#00b8ff', width=2)), row=3, col=1)
        fig.add_trace(go.Scatter(x=cd['dates'], y=cd['macd_signal'], name='Signal',
            line=dict(color='#ff6b6b', dash='dot', width=1.5)), row=3, col=1)

        fig.update_layout(
            template='plotly_dark', paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
            height=620, showlegend=True, margin=dict(t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Signal reasoning
        col_a, col_b = st.columns(2)
        with col_a:
            sig_color = "#00e5a0" if signal=="BUY" else "#ff3860" if signal=="SELL" else "#ffb300"
            arrow = "▲" if signal=="BUY" else "▼" if signal=="SELL" else "⬡"
            st.markdown(f"""
            <div style='text-align:center;padding:24px;background:#0d1117;border:1px solid #21262d;border-radius:12px'>
              <div style='font-size:3rem;color:{sig_color};font-weight:bold'>{arrow} {signal}</div>
              <div style='color:#8b949e;margin-top:8px'>Confidence: {analysis['confidence']}%</div>
              <div style='height:6px;background:#1c2332;border-radius:3px;margin-top:12px'>
                <div style='height:100%;width:{analysis["confidence"]}%;background:{sig_color};border-radius:3px'></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown("**Signal Reasoning:**")
            for reason in analysis.get('reasons', []):
                st.markdown(f"› {reason}")


# ── Tab 2: Forecasting ────────────────────────────────────
with tab2:
    if st.button("🔮 Run All Forecasts", type="primary"):
        with st.spinner("Training models... (this may take 1-2 minutes)"):
            forecasts = run_forecast(symbol, period)

        if forecasts:
            for model_key, label, color in [
                ('lstm', 'LSTM Deep Learning', '#00e5a0'),
                ('prophet', 'Facebook Prophet', '#00b8ff'),
                ('arima', 'ARIMA', '#a78bfa'),
            ]:
                fc = forecasts[model_key]
                st.subheader(f"📊 {label}")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("RMSE", f"{fc['metrics']['rmse']:.4f}")
                col2.metric("MAE", f"{fc['metrics']['mae']:.4f}")
                col3.metric("MAPE", f"{fc['metrics']['mape']:.2f}%")
                dir_icon = "▲" if fc['direction']=="UP" else "▼"
                dir_color = "normal" if fc['direction']=="UP" else "inverse"
                col4.metric("7-day Direction", f"{dir_icon} {fc['direction']}",
                            f"{fc['pct_change']:+.2f}%", delta_color=dir_color)

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=fc['test_dates'], y=fc['actuals'],
                    name='Actual', line=dict(color='#8b949e', width=1.5)))
                fig.add_trace(go.Scatter(x=fc['test_dates'], y=fc['predictions'],
                    name='Predicted', line=dict(color=color, width=2)))
                fig.add_trace(go.Scatter(x=fc['forecast_dates'], y=fc['forecast'],
                    name='Forecast', line=dict(color=color, width=2.5, dash='dot'),
                    mode='lines+markers'))
                if fc.get('forecast_upper'):
                    fig.add_trace(go.Scatter(x=fc['forecast_dates'], y=fc['forecast_upper'],
                        name='Upper CI', line=dict(color=f'rgba(255,255,255,0.2)', width=1),
                        fill=None))
                    fig.add_trace(go.Scatter(x=fc['forecast_dates'], y=fc['forecast_lower'],
                        name='Lower CI', line=dict(color=f'rgba(255,255,255,0.2)', width=1),
                        fill='tonexty', fillcolor='rgba(255,255,255,0.03)'))

                fig.update_layout(template='plotly_dark', paper_bgcolor='#0d1117',
                    plot_bgcolor='#0d1117', height=320, margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

                if model_key == 'arima' and fc.get('adf_test'):
                    adf = fc['adf_test']
                    st.info(f"**ADF Test:** Stat={adf.get('test_stat','N/A')} | "
                            f"p-value={adf.get('p_value','N/A')} | "
                            f"{'✅ Stationary' if adf.get('stationary') else '❌ Non-stationary'}")

                st.divider()
    else:
        st.info("Click **Run All Forecasts** to train LSTM, Prophet, and ARIMA models.")


# ── Tab 3: Model Comparison ───────────────────────────────
with tab3:
    if st.button("⚖️ Compare Models", type="primary", key="compare_btn"):
        with st.spinner("Training all models for comparison..."):
            forecasts = run_forecast(symbol, period)
        if forecasts:
            rows = []
            for key, label in [('lstm','LSTM'), ('prophet','Prophet'), ('arima','ARIMA')]:
                fc = forecasts[key]
                rows.append({
                    'Model': label, 'RMSE': fc['metrics']['rmse'],
                    'MAE': fc['metrics']['mae'], 'MAPE (%)': fc['metrics']['mape'],
                    'Direction': fc['direction'], '7d Change (%)': fc['pct_change'],
                })
            df_comp = pd.DataFrame(rows).set_index('Model')
            best = df_comp['RMSE'].idxmin()
            st.success(f"🏆 Best Model by RMSE: **{best}**")
            st.dataframe(df_comp.style.highlight_min(subset=['RMSE','MAE','MAPE (%)'],
                color='#0d2b1a'), use_container_width=True)

            # Consensus
            ups = sum(1 for r in rows if r['Direction']=='UP')
            consensus = "BULLISH 🟢" if ups >= 2 else "BEARISH 🔴"
            st.metric("Model Consensus", consensus, f"{ups}/3 models predict UP")
    else:
        st.info("Click **Compare Models** to see side-by-side performance.")


# ── Tab 4: Chart Vision ───────────────────────────────────
with tab4:
    st.subheader("👁️ Upload Chart Screenshot")
    st.caption("Upload any NIFTY / stock chart image for AI analysis")

    uploaded = st.file_uploader("Choose a chart image", type=["png", "jpg", "jpeg", "webp"])

    if uploaded:
        from PIL import Image
        import io

        col_img, col_res = st.columns([1, 1])
        with col_img:
            img = Image.open(uploaded)
            st.image(img, caption="Uploaded Chart", use_column_width=True)

        with col_res:
            with st.spinner("Analyzing chart..."):
                try:
                    from services.chart_vision_service import analyze_chart_image
                    result = analyze_chart_image(uploaded.read())
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    result = None

            if result:
                sig_c = result['color']
                st.markdown(f"""
                <div style='text-align:center;padding:20px;background:#0d1117;border:1px solid #21262d;border-radius:12px;margin-bottom:16px'>
                  <div style='font-size:3rem;color:{sig_c};font-weight:bold'>{result['signal']}</div>
                  <div style='color:#8b949e;margin-top:8px;font-size:14px'>
                    Trend: {result['trend']}<br>
                    Confidence: {result['confidence']}%
                  </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**Detected Patterns:**")
                for p in result.get('patterns', []):
                    st.markdown(f"- {p}")

                st.markdown("**Analysis Reasoning:**")
                for r in result.get('reasons', []):
                    st.markdown(f"› {r}")

                if result.get('support_resistance'):
                    st.markdown(f"**S/R Levels:** {result['support_resistance']}")
    else:
        st.info("Upload a NIFTY 5-min, 15-min, or daily chart screenshot to get AI analysis.")
