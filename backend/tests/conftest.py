"""
Pytest configuration and shared fixtures.
"""
import pytest
import sys
from pathlib import Path

# Add the backend app to the path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
