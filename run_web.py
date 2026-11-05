#!/usr/bin/env python3
"""SAHRA AEGIS - Web Operations Dashboard Launcher

Rules-based multi-agent heat-stress decision engine for Dubai.
Built for the Create AI Agents Championship (Dubai Chamber of Digital Economy).
"""

import argparse
import sys
import webbrowser
from pathlib import Path

# Add project root, src, and web directories to sys.path
ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
WEB_DIR = ROOT / "web"

for p in (ROOT, SRC_DIR, WEB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import uvicorn


def print_banner(host: str, port: int) -> None:
    banner = f"""
======================================================================
  ____    _    _   _ ____      _       _     _____ ____ ___ ____  
 / ___|  / \\  | | | |  _ \\    / \\     / \\   | ____/ ___|_ _/ ___| 
 \\___ \\ / _ \\ | |_| | |_) |  / _ \\   / _ \\  |  _|| |  _ | |\\___ \\ 
  ___) / ___ \\|  _  |  _ <  / ___ \\ / ___ \\ | |__| |_| || | ___) |
 |____/_/   \\_\\_| |_|_| \\_\\/_/   \\_\\/_/   \\_\\_____\\____|___|____/ 

  DUBAI HEAT-STRESS MULTI-AGENT DECISION ENGINE (100% DETERMINISTIC)
======================================================================
  * Operations Dashboard : http://{host}:{port}
  * Interactive API Docs : http://{host}:{port}/docs
  * Active Agents        : Monitor, Predict, Arbiter, Plan, Act, Verify
  * Regulatory Compliance: ISO 7243 / UAE MOHRE Heat Safety Regulations
======================================================================
"""
    print(banner)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SAHRA AEGIS Web Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    parser.add_argument("--open", action="store_true", help="Automatically open browser on launch")
    args = parser.parse_args()

    print_banner(args.host, args.port)

    if args.open:
        try:
            webbrowser.open(f"http://{args.host}:{args.port}")
        except Exception:
            pass

    # Run Uvicorn server
    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(WEB_DIR),
        log_level="info",
    )


if __name__ == "__main__":
    main()
