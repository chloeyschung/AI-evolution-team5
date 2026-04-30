#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${BRIEFLY_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SESSION_NAME="briefly-stack"
PID_FILE="$ROOT_DIR/.stack.pids"
LOG_DIR="$ROOT_DIR/logs"
ACTION="${1:-start}"
if [[ $# -gt 0 ]]; then
  shift
fi
SKIP_INSTALL="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install)
      SKIP_INSTALL="true"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

get_env_value() {
  local file="$1"
  local key="$2"
  if [[ -f "$file" ]]; then
    grep -E "^${key}=" "$file" | head -n 1 | cut -d'=' -f2- || true
  fi
}

upsert_env() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp

  mkdir -p "$(dirname "$file")"
  [[ -f "$file" ]] || touch "$file"

  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { replaced = 0 }
    $0 ~ "^" key "=" {
      if (!replaced) {
        print key "=" value
        replaced = 1
      }
      next
    }
    { print }
    END {
      if (!replaced) print key "=" value
    }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

ensure_env_default() {
  local file="$1"
  local key="$2"
  local value="$3"

  if [[ -z "$(get_env_value "$file" "$key")" ]]; then
    upsert_env "$file" "$key" "$value"
  fi
}

generate_jwt_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
  fi
}

generate_hex_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
  fi
}

generate_fernet_key() {
  if command -v python3 >/dev/null 2>&1 && python3 - <<'PY' >/dev/null 2>&1
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
  then
    python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
  else
    uv run python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
  fi
}

ensure_local_env() {
  local root_env="$ROOT_DIR/.env"
  local web_env="$ROOT_DIR/web-dashboard/.env"
  local ext_env="$ROOT_DIR/browser-extension/.env"
  local jwt_secret
  local enc_key
  local google_client_id
  local google_client_secret
  local google_redirect_uri
  local email_lookup_key

  jwt_secret="$(get_env_value "$root_env" "JWT_SECRET_KEY")"
  enc_key="$(get_env_value "$root_env" "ENCRYPTION_KEY")"
  google_client_id="$(get_env_value "$root_env" "GOOGLE_CLIENT_ID")"
  google_client_secret="$(get_env_value "$root_env" "GOOGLE_CLIENT_SECRET")"
  google_redirect_uri="$(get_env_value "$root_env" "GOOGLE_REDIRECT_URI")"
  email_lookup_key="$(get_env_value "$root_env" "EMAIL_LOOKUP_KEY")"

  if [[ -z "$jwt_secret" ]]; then
    jwt_secret="$(generate_jwt_secret)"
  fi
  if [[ -z "$enc_key" ]]; then
    enc_key="$(generate_fernet_key)"
  fi
  if [[ -z "$google_client_id" ]]; then
    google_client_id="replace-with-google-client-id.apps.googleusercontent.com"
  fi
  if [[ -z "$google_client_secret" ]]; then
    google_client_secret="replace-with-google-client-secret"
  fi
  if [[ -z "$google_redirect_uri" ]]; then
    google_redirect_uri="http://localhost:3001/oauth-callback"
  fi
  if [[ -z "$email_lookup_key" ]]; then
    email_lookup_key="$(generate_hex_secret)"
  fi

  upsert_env "$root_env" "JWT_SECRET_KEY" "$jwt_secret"
  upsert_env "$root_env" "ENCRYPTION_KEY" "$enc_key"
  upsert_env "$root_env" "GOOGLE_CLIENT_ID" "$google_client_id"
  upsert_env "$root_env" "GOOGLE_CLIENT_SECRET" "$google_client_secret"
  upsert_env "$root_env" "GOOGLE_REDIRECT_URI" "$google_redirect_uri"
  upsert_env "$root_env" "EMAIL_LOOKUP_KEY" "$email_lookup_key"
  ensure_env_default "$root_env" "SMTP_HOST" "localhost"
  ensure_env_default "$root_env" "SMTP_PORT" "1025"
  ensure_env_default "$root_env" "SMTP_USER" ""
  ensure_env_default "$root_env" "SMTP_PASSWORD" ""
  ensure_env_default "$root_env" "EMAIL_FROM" "noreply@briefly.local"
  ensure_env_default "$root_env" "APP_BASE_URL" "http://localhost:3001"
  ensure_env_default "$root_env" "ALLOWED_ORIGINS" "http://localhost:3001"
  ensure_env_default "$root_env" "ALLOWED_ORIGIN_REGEX" "chrome-extension://[a-z]{32}"
  ensure_env_default "$root_env" "DATABASE_URL" "sqlite+aiosqlite:///./briefly.db"

  ensure_env_default "$web_env" "VITE_API_BASE_URL" "/api"
  upsert_env "$web_env" "VITE_GOOGLE_CLIENT_ID" "$google_client_id"

  ensure_env_default "$ext_env" "VITE_API_BASE_URL" "http://localhost:8000"
  upsert_env "$ext_env" "VITE_GOOGLE_CLIENT_ID" "$google_client_id"
  ensure_env_default "$ext_env" "VITE_SHOW_API_URL_SETTING" "false"
}

install_dependencies() {
  if [[ "$SKIP_INSTALL" == "true" ]]; then
    echo "Skipping dependency install."
    return 0
  fi

  [[ -d "$ROOT_DIR/.venv" ]] || uv sync
  [[ -d "$ROOT_DIR/web-dashboard/node_modules" ]] || (cd "$ROOT_DIR/web-dashboard" && npm install)
  [[ -d "$ROOT_DIR/browser-extension/node_modules" ]] || (cd "$ROOT_DIR/browser-extension" && npm install)
}

prepare_local_dev() {
  ensure_local_env
  install_dependencies
}

seed_dev_user() {
  prepare_local_dev
  cd "$ROOT_DIR"
  set -a && source "$ROOT_DIR/.env" && set +a
  uv run python scripts/seed_dev_user.py
}

build_all() {
  prepare_local_dev
  (cd "$ROOT_DIR/web-dashboard" && npm run build)
  (cd "$ROOT_DIR/browser-extension" && npm run build)
}

stop_background_stack() {
  if [[ -f "$PID_FILE" ]]; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      if kill -0 "$pid" >/dev/null 2>&1; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "Stopped background stack processes."
  else
    echo "No background PID file found: $PID_FILE"
  fi
}

show_status() {
  local has_tmux="false"
  local has_bg="false"

  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    has_tmux="true"
  fi

  if [[ -f "$PID_FILE" ]]; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      if kill -0 "$pid" >/dev/null 2>&1; then
        has_bg="true"
        break
      fi
    done < "$PID_FILE"
  fi

  if [[ "$has_tmux" == "true" ]]; then
    echo "Stack status: running (tmux session: $SESSION_NAME)"
    return 0
  fi

  if [[ "$has_bg" == "true" ]]; then
    echo "Stack status: running (background pids in $PID_FILE)"
    return 0
  fi

  echo "Stack status: stopped"
  return 1
}

stop_stack() {
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo "Stopped tmux session: $SESSION_NAME"
  fi
  stop_background_stack
}

require_cmd uv
require_cmd npm

cd "$ROOT_DIR"

case "$ACTION" in
  setup)
    prepare_local_dev
    echo "Local developer setup complete."
    echo "Seed test user: scripts/run-stack.sh seed-user"
    exit 0
    ;;
  start)
    ;;
  stop)
    stop_stack
    exit 0
    ;;
  status)
    show_status
    exit $?
    ;;
  restart)
    stop_stack
    ACTION="start"
    ;;
  seed-user)
    seed_dev_user
    exit 0
    ;;
  build)
    build_all
    exit 0
    ;;
  *)
    cat <<USAGE
Usage: scripts/run-stack.sh [setup|start|stop|status|restart|seed-user|build] [--skip-install]
Default action: start
USAGE
    exit 1
    ;;
esac

prepare_local_dev

if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
  fi

  tmux new-session -d -s "$SESSION_NAME" -n backend "cd '$ROOT_DIR' && set -a && source '$ROOT_DIR/.env' && set +a && uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload"
  tmux new-window -t "$SESSION_NAME" -n web "cd '$ROOT_DIR/web-dashboard' && npm run dev"
  tmux new-window -t "$SESSION_NAME" -n extension "cd '$ROOT_DIR/browser-extension' && npm run dev"

  cat <<MSG
Stack started in tmux session: $SESSION_NAME
Attach with: tmux attach -t $SESSION_NAME
Stop with:   tmux kill-session -t $SESSION_NAME
Status:      scripts/run-stack.sh status
MSG
else
  mkdir -p "$LOG_DIR"
  : > "$PID_FILE"

  (
    cd "$ROOT_DIR"
    set -a && source "$ROOT_DIR/.env" && set +a
    uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
  ) > "$LOG_DIR/backend.log" 2>&1 &
  echo "$!" >> "$PID_FILE"

  (
    cd "$ROOT_DIR/web-dashboard"
    npm run dev
  ) > "$LOG_DIR/web-dashboard.log" 2>&1 &
  echo "$!" >> "$PID_FILE"

  (
    cd "$ROOT_DIR/browser-extension"
    npm run dev
  ) > "$LOG_DIR/browser-extension.log" 2>&1 &
  echo "$!" >> "$PID_FILE"

  cat <<MSG
Stack started in background (no tmux found).
PIDs file: $PID_FILE
Logs:      $LOG_DIR/backend.log, $LOG_DIR/web-dashboard.log, $LOG_DIR/browser-extension.log
Stop all:  scripts/run-stack.sh stop
Status:    scripts/run-stack.sh status
MSG
fi
