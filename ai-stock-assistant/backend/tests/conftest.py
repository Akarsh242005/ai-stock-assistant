"""
conftest.py — pytest configuration for the backend test suite.

Adds the backend directory to sys.path so all imports resolve
correctly regardless of where pytest is invoked from.
"""

import sys
import os

# Ensure backend/ is on the import path
backend_dir = os.path.dirname(__file__)
root_dir    = os.path.dirname(backend_dir)

for path in (backend_dir, root_dir):
    if path not in sys.path:
        sys.path.insert(0, path)
