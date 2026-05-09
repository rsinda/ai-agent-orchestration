#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to run this app."
  exit 1
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Add GOOGLE_API_KEY, OPENAI_API_KEY, or TELEGRAM_BOT_TOKEN if needed."
fi

echo "Starting AI Agent Orchestration Platform..."
docker compose up --build

