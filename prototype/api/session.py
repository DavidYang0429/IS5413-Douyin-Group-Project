"""Vercel HTTP adapter; authentication and SQL remain in app.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Handler as handler
