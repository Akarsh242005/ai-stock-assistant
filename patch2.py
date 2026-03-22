import sys

html_file = r"c:\Users\Akarsh Sharma\Downloads\files\stockvision-dashboard.html"
with open(html_file, "r", encoding="utf-8") as f:
    text = f.read()

sections = text.split("// ════════════════════════════════════════════════")

# Find the CHART VISION AI section dynamically
cv_index = -1
for idx, s in enumerate(sections):
    if "CHART VISION AI" in s:
        cv_index = idx
        break

if cv_index == -1:
    print("Error: Could not find CHART VISION AI section.")
    sys.exit(1)

# Replacement for CHART VISION AI
chart_vision_replacement = """\n// CHART VISION AI — image analysis
// ════════════════════════════════════════════════
function cvDrop(e) {
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
}\n"""

sections[cv_index] = chart_vision_replacement

with open(html_file, "w", encoding="utf-8") as f:
    f.write("// ════════════════════════════════════════════════".join(sections))

print("Chart vision patch applied.")
