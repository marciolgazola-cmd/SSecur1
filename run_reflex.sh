#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

export REFLEX_USE_NPM=true
export NPM_CONFIG_CACHE="$PWD/.npm-cache"
mkdir -p "$NPM_CONFIG_CACHE"

FRONTEND_PORT="${FRONTEND_PORT:-3010}"
BACKEND_PORT="${BACKEND_PORT:-8010}"

kill_port_listeners() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN -Pn 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Encerrando processo(s) na porta $port: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN -Pn 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      echo "Forçando encerramento na porta $port: $pids"
      kill -9 $pids 2>/dev/null || true
      sleep 1
    fi
  fi
}

kill_port_listeners "$FRONTEND_PORT"
kill_port_listeners "$BACKEND_PORT"

python -m reflex run --frontend-port "$FRONTEND_PORT" --backend-port "$BACKEND_PORT"
