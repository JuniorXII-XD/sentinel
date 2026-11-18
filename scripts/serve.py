"""Serve the built frontend and FastAPI from one origin. Migrate/create users first."""

import argparse
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--host", default=os.getenv("BIND_HOST", "127.0.0.1"))
parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
parser.add_argument("--strictPort", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
os.chdir(root / "backend")
sys.path.insert(0, str(root / "backend"))
import uvicorn

uvicorn.run("app.main:app", host=args.host, port=args.port, proxy_headers=False)
