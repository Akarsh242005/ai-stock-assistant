import re
import sys

html_file = r"c:\Users\Akarsh Sharma\OneDrive\Desktop\ai stock analysis\stockvision-dashboard.html"

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove from "LIVE DATA FETCH" to "MAIN SEARCH FLOW"
new_content = re.sub(
    r"// ════════════════════════════════════════════════\r?\n// LIVE DATA FETCH — Yahoo Finance via CORS proxy\r?\n// ════════════════════════════════════════════════.*?// ════════════════════════════════════════════════\r?\n// MAIN SEARCH FLOW\r?\n// ════════════════════════════════════════════════",
    "// ════════════════════════════════════════════════\n// MAIN SEARCH FLOW\n// ════════════════════════════════════════════════",
    content,
    flags=re.DOTALL
)

print("Replacement 1 success:", new_content != content)
content = new_content

# 2. Replace MAIN SEARCH FLOW
main_search_replacement = """var currentSymbol = null;
var appData = {};
var charts = {};
const BACKEND_URL = 'http://localhost:8000';

function qs(sym) { document.getElementById('ti').value = sym; doSearch(); }

function doSearch() {
  var raw = document.getElementById('ti').value.trim();
  if (!raw) { showToast('Enter a stock symbol', 'err'); return; }
  currentSymbol = raw.toUpperCase();
  var ticker = resolveTicker(currentSymbol);

  showLoader('FETCHING AI ANALYSIS FROM BACKEND...');
  setBtnDisabled(true);

  Promise.all([
    fetch(BACKEND_URL + '/api/analysis/' + ticker).then(r => r.json()),
    fetch(BACKEND_URL + '/api/forecast/' + ticker).then(r => r.json())
  ])
  .then(function(results) {
    var analysis = results[0];
    var forecast = results[1];
    if (analysis.detail) throw new Error(analysis.detail);
    if (forecast.detail) throw new Error(forecast.detail);
    
    processBackendData(analysis, forecast, currentSymbol);
    hideLoader();
    setBtnDisabled(false);
    document.getElementById('live-error').style.display = 'none';
    showToast('✓ Real-time AI analysis loaded', 'ok');
  })
  .catch(function(err) {
    hideLoader();
    setBtnDisabled(false);
    showToast('Error: ' + err.message, 'err');
    document.getElementById('dash-empty').style.display = 'none';
    document.getElementById('dash-results').style.display = 'block';
    var errEl = document.getElementById('live-error');
    errEl.style.display = 'block';
    errEl.innerHTML = '<strong>⚠ Backend Error</strong><br>' + err.message +
      '<br><br>Ensure your AI assistant FastAPI backend is running on http://localhost:8000';
    document.getElementById('stats-grid').innerHTML = '';
    document.getElementById('sig-panel').innerHTML = '';
  });
}

function processBackendData(analysis, forecastData, displaySym) {
  var info = analysis.info || {};
  var cData = analysis.chart_data;
  
  var latestPrice = info.regularMarketPrice || cData.close[cData.close.length-1];
  var prevClose = info.previousClose || info.chartPreviousClose || cData.close[cData.close.length-2] || latestPrice;
  var change = latestPrice - prevClose;
  var changePct = (prevClose ? (change / prevClose) * 100 : 0);

  var sigObj = {
    signal: analysis.signal,
    confidence: analysis.confidence,
    score: analysis.score,
    color: analysis.color,
    reasons: analysis.reasons
  };

  appData = {
    ohlcv: { symbol: analysis.symbol },
    closes: cData.close,
    dates: cData.dates,
    latestPrice: latestPrice,
    prevClose: prevClose,
    change: change,
    changePct: changePct,
    rsi: cData.rsi,
    macd: { macd: cData.macd_line, signal: cData.macd_signal, histogram: cData.histogram },
    bb: { upper: cData.bb_upper, lower: cData.bb_lower },
    sma50: cData.sma_50,
    sma200: cData.sma_200,
    signal: sigObj,
    forecast: {
      lstm: forecastData.lstm,
      prophet: forecastData.prophet,
      arima: forecastData.arima
    },
    meta: {
      name: info.longName || info.shortName || displaySym,
      currency: info.currency || 'INR',
      exchange: info.exchangeName || 'NSE',
      high52: info.fiftyTwoWeekHigh,
      low52: info.fiftyTwoWeekLow
    }
  };

  renderDashboard();
  renderTA();
  renderForecast();
  renderComparison();

  document.getElementById('dash-sub').textContent =
    'Live ML Data for ' + displaySym + (appData.meta.name ? ' · ' + appData.meta.name : '') +
    ' · ' + appData.meta.exchange + ' · ' + appData.meta.currency;
}
"""

new_content = re.sub(
    r"var currentSymbol = null;.*?// ════════════════════════════════════════════════\r?\n// RENDER DASHBOARD\r?\n// ════════════════════════════════════════════════",
    main_search_replacement + "\n// ════════════════════════════════════════════════\n// RENDER DASHBOARD\n// ════════════════════════════════════════════════",
    content,
    flags=re.DOTALL
)
print("Replacement 2 success:", new_content != content)
content = new_content

# 3. Replace CHART VISION AI
chart_vision_replacement = """function cvDrop(e) {
  e.preventDefault(); e.stopPropagation();
  document.getElementById('cv-drop').classList.remove('drag');
  var f = e.dataTransfer.files[0];
  if (f) cvProcess(f);
}
function cvFile(e) {
  var f = e.target.files[0];
  if (f) cvProcess(f);
  e.target.value = '';
}
function cvProcess(file) {
  if (!file.type.startsWith('image/')) { showToast('Upload an image file', 'err'); return; }
  if (file.size > 10*1024*1024) { showToast('File too large (max 10MB)', 'err'); return; }
  showLoader('AI ANALYZING CHART...');
  
  var formData = new FormData();
  formData.append('file', file);

  fetch(BACKEND_URL + '/api/chart/analyze', {
    method: 'POST',
    body: formData
  })
  .then(r => r.json())
  .then(function(result) {
    if (result.detail) throw new Error(result.detail);
    hideLoader();

    var color = result.color || (result.signal === 'BUY' ? '#00e5a0' : result.signal === 'SELL' ? '#ff3860' : '#ffb300');
    var arrow = result.signal === 'BUY' ? '▲' : result.signal === 'SELL' ? '▼' : '⏸';
    var cpCls = result.signal === 'BUY' ? 'cp-call' : result.signal === 'SELL' ? 'cp-put' : 'cp-wait';
    var cpIcon = result.signal === 'BUY' ? '📈' : result.signal === 'SELL' ? '📉' : '⏳';
    var cpTitle = result.signal === 'BUY' ? 'BUY CALL Option Recommended' : result.signal === 'SELL' ? 'BUY PUT Option Recommended' : 'WAIT — No Clear Signal';
    
    var thumb = URL.createObjectURL(file);
    
    var patternsHtml = (result.patterns || []).map(function(p){return '<span class="ptag">'+p+'</span>';}).join('');
    var reasonsHtml = (result.reasons || []).map(function(r){return '<li>› '+r+'</li>';}).join('');
    var srHtml = result.support_resistance ? '<li style="color:var(--txt)"><strong>S/R Levels:</strong> '+result.support_resistance+'</li>' : '';

    document.getElementById('cv-panel').innerHTML =
      '<div class="card mb"><div class="ch"><span class="ct">AI Analysis — '+file.name+'</span></div>' +
      '<div class="vis-wrap">' +
      '<img src="'+thumb+'" class="vis-thumb" alt="chart">' +
      '<div>' +
      '<div class="vis-sig" style="color:'+color+'">'+arrow+' '+result.signal+'</div>' +
      '<div style="font-size:12px;color:var(--mute);margin-bottom:10px">Trend: '+result.trend+' · Confidence: '+Math.round(result.confidence)+'%</div>' +
      '<div class="cbar"><div class="cbar-fill" style="width:'+Math.round(result.confidence)+'%;background:'+color+'"></div></div>' +
      '<div style="margin-top:12px"><div style="font-size:9px;color:var(--mute);letter-spacing:1px;margin-bottom:5px">DETECTED</div>'+
      patternsHtml+'</div>' +
      '</div></div>' +
      '<div class="cp-box '+cpCls+'" style="margin-top:14px"><div class="cp-title">'+cpIcon+' '+cpTitle+'</div><div class="cp-sub">Based on computer vision analysis, the AI detected a <strong>'+result.trend+'</strong> trend. Confidence score is '+Math.round(result.confidence)+'%.</div></div>' +
      '</div>' +
      '<div class="card"><div class="ch"><span class="ct">Analysis Breakdown</span></div>' +
      '<ul class="reasons">' + reasonsHtml + srHtml + '</ul></div>';
      
    showToast('✓ Chart analyzed — '+result.signal, 'ok');
  })
  .catch(function(err) {
    hideLoader();
    showToast('Error: ' + err.message, 'err');
    document.getElementById('cv-panel').innerHTML = '<div class="err-box"><strong>⚠ AI Analysis Failed</strong><br>' + err.message + '<br><br>Ensure the backend is running at ' + BACKEND_URL + '</div>';
  });
}
"""

new_content = re.sub(
    r"function cvDrop\(e\).*?// ════════════════════════════════════════════════\r?\n// CHART / UI HELPERS\r?\n// ════════════════════════════════════════════════",
    chart_vision_replacement + "\n// ════════════════════════════════════════════════\n// CHART / UI HELPERS\n// ════════════════════════════════════════════════",
    content,
    flags=re.DOTALL
)
print("Replacement 3 success:", new_content != content)
content = new_content

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patching complete!")
