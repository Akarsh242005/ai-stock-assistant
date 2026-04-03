import json
import math

def replace_nans(obj):
    import numpy as np
    import pandas as pd
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if hasattr(np, "floating") and isinstance(obj, np.floating):
        return None if np.isnan(obj) or np.isinf(obj) else float(obj)
    if isinstance(obj, dict):
        return {k: replace_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_nans(i) for i in obj]
    if hasattr(np, "ndarray") and isinstance(obj, np.ndarray):
        return [replace_nans(i) for i in obj.tolist()]
    if hasattr(pd, "Series") and isinstance(obj, pd.Series):
        return [replace_nans(i) for i in obj.tolist()]
    return obj

def sanitize_for_json(obj):
    def fallback(o):
        import numpy as np
        import pandas as pd
        if isinstance(o, np.integer): return int(o)
        if hasattr(np, "floating") and isinstance(o, np.floating): return float(o)
        if hasattr(np, "bool_") and isinstance(o, np.bool_): return bool(o)
        if hasattr(pd, "Timestamp") and isinstance(o, pd.Timestamp): return o.isoformat()
        return str(o)
    
    clean_obj = replace_nans(obj)
    return json.loads(json.dumps(clean_obj, default=fallback, ensure_ascii=False))
