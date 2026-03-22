import os
import re

routers_dir = r"c:\Users\Akarsh Sharma\Downloads\files\ai-stock-assistant-COMPLETE\ai-stock-assistant\backend\routers"

utils_code = """import json

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
"""

with open(os.path.join(routers_dir, "..", "utils.py"), "w", encoding="utf-8") as f:
    f.write(utils_code)

for filename in ["forecast.py", "analysis.py", "chart_vision.py"]:
    filepath = os.path.join(routers_dir, filename)
    if not os.path.exists(filepath): continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    
    if "sanitize_for_json" not in text:
        text = "from utils import sanitize_for_json\n" + text
        
    # Replace single line `return {` followed by anything matching to `}`
    # Wait, some returns are multi-line dicts.
    # We can use regex to wrap the whole dict if it's the only thing returned.
    # A generic way is just to find all exported functions and wrap them but regex is easier.
    
    # Or actually, we can just replace 'return {' with 'return sanitize_for_json({'
    # and then add an extra closing parenthesis ')' at the end of the return statement?
    # No, matching the end of the dict is hard due to nested braces.
    
    # Let's match: return { ... }
    # Since it's Python, we can just wrap the variables in the routers.
    pass

# Actually, the safest way is ast parsing and unparsing!
import ast

for filename in ["forecast.py", "analysis.py", "chart_vision.py"]:
    filepath = os.path.join(routers_dir, filename)
    if not os.path.exists(filepath): continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()
        
    class ReturnWrapper(ast.NodeTransformer):
        def visit_Return(self, node):
            self.generic_visit(node)
            if node.value is not None:
                # return sanitize_for_json(...)
                new_node = ast.Return(
                    value=ast.Call(
                        func=ast.Name(id="sanitize_for_json", ctx=ast.Load()),
                        args=[node.value],
                        keywords=[]
                    )
                )
                ast.copy_location(new_node, node)
                return new_node
            return node
            
    tree = ast.parse(original)
    tree = ReturnWrapper().visit(tree)
    
    # inject import at the top
    import_stmt = ast.ImportFrom(module="utils", names=[ast.alias(name="sanitize_for_json", asname=None)], level=0)
    tree.body.insert(0, import_stmt)
    
    ast.fix_missing_locations(tree)
    new_code = ast.unparse(tree)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_code)
