import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
WEB_DIR = ROOT / "web"

for p in (ROOT, SRC_DIR, WEB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.app import app
