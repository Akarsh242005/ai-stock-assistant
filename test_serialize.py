import sys
import traceback
import json
sys.path.append(r"c:\Users\Akarsh Sharma\Downloads\files\ai-stock-assistant-COMPLETE\ai-stock-assistant\backend")

from routers.forecast import get_all_forecasts

def fallback_encoder(o):
    import numpy as np
    import pandas as pd
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, np.floating): return float(o)
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, pd.Timestamp): return o.isoformat()
    if isinstance(o, pd.Series): return o.tolist()
    return str(o)

try:
    print("Fetching forecasts...")
    result = get_all_forecasts("TATASTEEL.NS", period="2y")
    print("Forecasts retrieved. Attempting JSON serialization...")
    
    safe_result = json.loads(json.dumps(result, default=fallback_encoder))
    from fastapi.encoders import jsonable_encoder
    jsonable_encoder(safe_result)
    
    print("SUCCESS")
except Exception as e:
    traceback.print_exc()
