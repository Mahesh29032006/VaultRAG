#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "🚀 Starting SovereignRAG Backend on http://127.0.0.1:8093..."
arch -arm64 ./venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8093
