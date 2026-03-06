#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

export REFLEX_USE_NPM=true
export NPM_CONFIG_CACHE="$PWD/.npm-cache"
mkdir -p "$NPM_CONFIG_CACHE"

FRONTEND_PORT="${FRONTEND_PORT:-3010}"
BACKEND_PORT="${BACKEND_PORT:-8010}"

pick_free_port() {
  local preferred="$1"
  python3 - "$preferred" <<'PY'
import socket
import sys

start = int(sys.argv[1])
for port in range(start, start + 200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)

print(start)
PY
}

FREE_FRONTEND_PORT="$(pick_free_port "$FRONTEND_PORT")"
FREE_BACKEND_PORT="$(pick_free_port "$BACKEND_PORT")"

if [[ "$FREE_FRONTEND_PORT" != "$FRONTEND_PORT" ]]; then
  echo "Frontend port $FRONTEND_PORT ocupado. Usando $FREE_FRONTEND_PORT."
fi

if [[ "$FREE_BACKEND_PORT" != "$BACKEND_PORT" ]]; then
  echo "Backend port $BACKEND_PORT ocupado. Usando $FREE_BACKEND_PORT."
fi

python -m reflex run --frontend-port "$FREE_FRONTEND_PORT" --backend-port "$FREE_BACKEND_PORT"
