"""Puts the project root on the path, so a check can import `algorithms` from here.

The checks are scripts rather than a test package, so the directory Python puts on the
path is `tests`, not the project root. Importing this module first fixes that, which is
the shim the Hitchhiker's Guide to Python suggests for a test suite in its own folder.

Run a check from the project root: uv run tests/test_token_bucket.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
