import json

def sanitize_for_json(obj):
    def fallback(o):
        import numpy as np
        import pandas as pd
        if isinstance(o, np.integer): return int(o)
        if hasattr(np, "floating") and isinstance(o, np.floating): return float(o)
        if hasattr(np, "bool_") and isinstance(o, np.bool_): return bool(o)
        if hasattr(np, "ndarray") and isinstance(o, np.ndarray): return o.tolist()
        if hasattr(pd, "Timestamp") and isinstance(o, pd.Timestamp): return o.isoformat()
        if hasattr(pd, "Series") and isinstance(o, pd.Series): return o.tolist()
        return str(o)
    return json.loads(json.dumps(obj, default=fallback, ensure_ascii=False, allow_nan=False))
