"""Configure pytest to import from src/ correctly.

The src/models/__init__.py uses 'from models.acer_graph import ...' (package-relative
imports) which only resolves when the working directory is src/. This conftest
adds src/ to sys.path so the imports resolve regardless of where pytest is invoked.
"""
import sys
import os

# Add src/ to sys.path so 'from models.acer_graph import ...' resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
