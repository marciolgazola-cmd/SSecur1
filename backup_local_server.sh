#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${SSECUR1_DATA_DIR:-$HOME/smartlab-ssecur1-data}"
APP_DIR="${SSECUR1_APP_DIR:-$(cd "$(dirname "$0")" && pwd)}"
BACKUP_DIR="${SSECUR1_BACKUP_DIR:-$HOME/smartlab-ssecur1-backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

DB_PATH="$DATA_DIR/ssecur1.db"
if [[ ! -f "$DB_PATH" ]]; then
  echo "Banco nao encontrado em: $DB_PATH"
  exit 1
fi

cp "$DB_PATH" "$BACKUP_DIR/ssecur1_${TIMESTAMP}.db"
echo "Backup do banco salvo em: $BACKUP_DIR/ssecur1_${TIMESTAMP}.db"

UPLOADS_DIR="$APP_DIR/uploaded_files"
if [[ -d "$UPLOADS_DIR" ]]; then
  tar -czf "$BACKUP_DIR/uploaded_files_${TIMESTAMP}.tar.gz" -C "$APP_DIR" uploaded_files
  echo "Backup de uploads salvo em: $BACKUP_DIR/uploaded_files_${TIMESTAMP}.tar.gz"
fi
