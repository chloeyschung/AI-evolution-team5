#!/usr/bin/env bash
set -euo pipefail

# vLLM standalone server controller (no tmux)
# Uses the same launch parameters as:
#   ~/Desktop/vllm-env/agent_launcher.py (vllm_args + env block)

ACTION="${1:-status}"

HOME_DIR="${HOME:-/home/younghwan}"
VENV_BIN_DIR="${VENV_BIN_DIR:-$HOME_DIR/Desktop/vllm-env/.venv/bin}"
VLLM_BIN="${VLLM_BIN:-$VENV_BIN_DIR/vllm}"

MODEL_PATH="${VLLM_MODEL_PATH:-$HOME_DIR/Desktop/Models/Qwen3.5-27B-AWQ-BF16-INT4}"
PORT="${VLLM_PORT:-8180}"
GPU_UTIL="${LOCAL_AGENT_GPU_MEMORY_UTILIZATION:-0.90}"

STATE_DIR="${VLLM_STATE_DIR:-$HOME_DIR/.local/state/vllm-local}"
PID_FILE="$STATE_DIR/vllm_${PORT}.pid"
LOG_FILE="${VLLM_LOG_FILE:-$STATE_DIR/vllm_${PORT}.log}"

HEALTH_TIMEOUT_SEC="${VLLM_HEALTH_TIMEOUT_SEC:-180}"

mkdir -p "$STATE_DIR"

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE"
  fi
}

is_port_open() {
  ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${PORT}\$"
}

health_ok() {
  curl -fsS -m 2 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1
}

print_status() {
  local pid
  pid="$(read_pid || true)"

  if [[ -n "$pid" ]] && is_pid_running "$pid"; then
    echo "vLLM status: running (pid=$pid, port=$PORT)"
  elif is_port_open; then
    echo "vLLM status: running on port $PORT (pid file stale or missing)"
  else
    echo "vLLM status: stopped"
  fi

  if health_ok; then
    echo "health: ok"
  else
    echo "health: down"
  fi
}

start_server() {
  if [[ ! -x "$VLLM_BIN" ]]; then
    echo "vLLM executable not found: $VLLM_BIN" >&2
    exit 1
  fi

  if [[ ! -d "$MODEL_PATH" ]]; then
    echo "Model path not found: $MODEL_PATH" >&2
    exit 1
  fi

  local pid
  pid="$(read_pid || true)"
  if [[ -n "$pid" ]] && is_pid_running "$pid"; then
    echo "vLLM already running (pid=$pid, port=$PORT)"
    print_status
    exit 0
  fi

  # Keep same env knobs as agent_launcher.py
  export PATH="/usr/local/cuda-12.4/bin:${PATH}"
  export LD_LIBRARY_PATH="/usr/local/cuda-12.4/lib64:${LD_LIBRARY_PATH:-}"
  export CUDACXX="/usr/local/cuda-12.4/bin/nvcc"
  export CUDA_VISIBLE_DEVICES="0,1"
  export RAY_memory_monitor_refresh_ms="0"
  export NCCL_CUMEM_ENABLE="0"
  export VLLM_ENABLE_CUDAGRAPH_GC="1"
  export VLLM_USE_FLASHINFER_SAMPLER="1"
  export NCCL_P2P_DISABLE="0"
  export NCCL_P2P_LEVEL="NVL"
  export NCCL_IB_DISABLE="1"

  # Keep long-context auto mode behavior (--max-model-len -1)
  export VLLM_ALLOW_LONG_MAX_MODEL_LEN="1"
  unset VLLM_HEALTH_TIMEOUT_SEC

  : >"$LOG_FILE"

  # Keep vLLM args from agent_launcher.py
  nohup "$VLLM_BIN" serve "$MODEL_PATH" \
    --port "$PORT" \
    --served-model-name "local-model" \
    --tensor-parallel-size "2" \
    --max-model-len "-1" \
    --max-num-seqs "8" \
    --block-size "32" \
    --max-num-batched-tokens "2048" \
    --enable-auto-tool-choice \
    --tool-call-parser "qwen3_coder" \
    --reasoning-parser "qwen3" \
    --enable-prefix-caching \
    --attention-backend "FLASHINFER" \
    --gpu-memory-utilization "$GPU_UTIL" \
    --speculative-config '{"method":"mtp","num_speculative_tokens":5}' \
    --no-use-tqdm-on-load \
    --quantization "compressed-tensors" \
    >"$LOG_FILE" 2>&1 &

  local new_pid=$!
  echo "$new_pid" >"$PID_FILE"
  echo "vLLM starting (pid=$new_pid, port=$PORT)"
  echo "log: $LOG_FILE"

  local waited=0
  while (( waited < HEALTH_TIMEOUT_SEC )); do
    if health_ok; then
      echo "vLLM is healthy: http://127.0.0.1:${PORT}/health"
      return 0
    fi
    if ! is_pid_running "$new_pid"; then
      echo "vLLM process exited early. Check log: $LOG_FILE" >&2
      tail -n 80 "$LOG_FILE" || true
      exit 1
    fi
    sleep 2
    waited=$(( waited + 2 ))
  done

  echo "Timed out waiting for health endpoint (${HEALTH_TIMEOUT_SEC}s)." >&2
  tail -n 80 "$LOG_FILE" || true
  exit 1
}

stop_server() {
  local pid
  pid="$(read_pid || true)"

  if [[ -n "$pid" ]] && is_pid_running "$pid"; then
    echo "Stopping vLLM pid=$pid"
    kill "$pid" || true
    for _ in $(seq 1 15); do
      if ! is_pid_running "$pid"; then
        break
      fi
      sleep 1
    done
    if is_pid_running "$pid"; then
      echo "Force killing vLLM pid=$pid"
      kill -9 "$pid" || true
    fi
  fi

  if is_port_open; then
    fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
  fi

  rm -f "$PID_FILE"
  echo "vLLM stopped"
}

show_logs() {
  if [[ -f "$LOG_FILE" ]]; then
    tail -n 120 "$LOG_FILE"
  else
    echo "No log file: $LOG_FILE"
  fi
}

show_health() {
  curl -fsS "http://127.0.0.1:${PORT}/health" && echo
}

case "$ACTION" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    start_server
    ;;
  status)
    print_status
    ;;
  health)
    show_health
    ;;
  logs)
    show_logs
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|health|logs}" >&2
    exit 1
    ;;
esac
