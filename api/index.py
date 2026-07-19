"""
api/index.py
------------
Vercel's Python runtime looks for a WSGI-compatible `app` object in this
file. It imports the real Flask app from the project root so the actual
application code lives in one place (app.py) instead of being duplicated
or restructured for the platform.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app  # noqa: E402  (import after sys.path fix, required)

# Vercel's @vercel/python builder detects this module-level `app` and
# serves it as the WSGI entrypoint for every route matched in vercel.json.
