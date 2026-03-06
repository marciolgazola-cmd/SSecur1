#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source .venv/bin/activate

export REFLEX_USE_NPM=true
export NPM_CONFIG_CACHE="$PWD/.npm-cache"
mkdir -p "$NPM_CONFIG_CACHE"

python -m reflex export
