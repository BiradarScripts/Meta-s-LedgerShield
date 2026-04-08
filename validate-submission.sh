#!/usr/bin/env bash
#
# validate-submission.sh — LedgerShield pre-submission validator
#
# Validates the local repo and a deployed HF Space against the Meta OpenEnv
# hackathon's most important hard gates:
#   1. Space health + reset
#   2. Docker build + local container run
#   3. openenv validate
#   4. inference.py completes and emits strict [START]/[STEP]/[END] logs

set -euo pipefail

DOCKER_BUILD_TIMEOUT=900
LOCAL_PORT="${LOCAL_PORT:-18080}"

if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BOLD='' NC=''
fi

run_with_timeout() {
  local secs="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$secs" "$@"
  else
    "$@" &
    local pid=$!
    ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
    local watcher=$!
    wait "$pid" 2>/dev/null
    local rc=$?
    kill "$watcher" 2>/dev/null || true
    wait "$watcher" 2>/dev/null || true
    return $rc
  fi
}

portable_mktemp() {
  local prefix="${1:-validate}"
  mktemp "${TMPDIR:-/tmp}/${prefix}-XXXXXX" 2>/dev/null || mktemp
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  else
    echo "python/python3 not found"
    exit 1
  fi
fi

CLEANUP_FILES=()
IMAGE_TAG=""
CONTAINER_NAME=""

cleanup() {
  if [ -n "${CONTAINER_NAME}" ]; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi
  rm -f "${CLEANUP_FILES[@]+"${CLEANUP_FILES[@]}"}" 2>/dev/null || true
}
trap cleanup EXIT

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  printf "Usage: %s <space_url> [repo_dir]\n" "$0"
  printf "\n"
  printf "  space_url  Your Hugging Face Space URL (e.g. https://team-name.hf.space)\n"
  printf "  repo_dir   Path to repo root (default: current directory)\n"
  exit 1
fi

if ! REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd)"; then
  printf "Error: directory '%s' not found\n" "${2:-.}"
  exit 1
fi

PING_URL="${PING_URL%/}"
PASS=0

log()  { printf "[%s] %b\n" "$(date -u +%H:%M:%S)" "$*"; }
pass() { log "${GREEN}PASSED${NC} -- $1"; PASS=$((PASS + 1)); }
fail() { log "${RED}FAILED${NC} -- $1"; }
hint() { printf "  ${YELLOW}Hint:${NC} %b\n" "$1"; }
stop_at() {
  printf "\n"
  printf "${RED}${BOLD}Validation stopped at %s.${NC} Fix the above before continuing.\n" "$1"
  exit 1
}

print_header() {
  printf "\n"
  printf "${BOLD}========================================${NC}\n"
  printf "${BOLD}  LedgerShield Submission Validator${NC}\n"
  printf "${BOLD}========================================${NC}\n"
  log "Repo:     $REPO_DIR"
  log "Space:    $PING_URL"
  log "Python:   $PYTHON_BIN"
  printf "\n"
}

http_code() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  if [ -n "$body" ]; then
    curl -s -o /dev/null -w "%{http_code}" -X "$method" \
      -H "Content-Type: application/json" \
      -d "$body" \
      "$url" \
      --max-time 30 || printf "000"
  else
    curl -s -o /dev/null -w "%{http_code}" -X "$method" \
      "$url" \
      --max-time 30 || printf "000"
  fi
}

wait_for_http_200() {
  local url="$1"
  local method="${2:-GET}"
  local body="${3:-}"
  local tries="${4:-40}"
  local pause="${5:-1}"

  for _ in $(seq 1 "$tries"); do
    local code
    code="$(http_code "$method" "$url" "$body")"
    if [ "$code" = "200" ]; then
      return 0
    fi
    sleep "$pause"
  done
  return 1
}

print_header

log "${BOLD}Step 1/4: Checking deployed HF Space${NC}"

SPACE_HEALTH_CODE="$(http_code GET "$PING_URL/health")"
if [ "$SPACE_HEALTH_CODE" = "200" ]; then
  pass "HF Space responds to /health"
else
  fail "HF Space /health returned HTTP $SPACE_HEALTH_CODE"
  hint "Make sure the Space is running and exposes the FastAPI app."
  stop_at "Step 1"
fi

SPACE_RESET_CODE="$(http_code POST "$PING_URL/reset" '{}')"
if [ "$SPACE_RESET_CODE" = "200" ]; then
  pass "HF Space responds to /reset"
else
  fail "HF Space /reset returned HTTP $SPACE_RESET_CODE"
  hint "The validator expects POST /reset to succeed with an empty JSON body."
  stop_at "Step 1"
fi

log "${BOLD}Step 2/4: Building and running Docker image${NC}"

if ! command -v docker >/dev/null 2>&1; then
  fail "docker command not found"
  hint "Install Docker Desktop or Docker Engine before running this validator."
  stop_at "Step 2"
fi

if [ ! -f "$REPO_DIR/Dockerfile" ]; then
  fail "No Dockerfile found in repo root"
  stop_at "Step 2"
fi

IMAGE_TAG="ledgershield-validate:$(date +%s)"
BUILD_OK=false
BUILD_LOG="$(portable_mktemp "docker-build")"
CLEANUP_FILES+=("$BUILD_LOG")
run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build -t "$IMAGE_TAG" "$REPO_DIR" >"$BUILD_LOG" 2>&1 && BUILD_OK=true

if [ "$BUILD_OK" = true ]; then
  pass "Docker build succeeded"
else
  fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"
  tail -20 "$BUILD_LOG"
  stop_at "Step 2"
fi

CONTAINER_NAME="ledgershield-validate-$RANDOM"
docker run -d --rm \
  --name "$CONTAINER_NAME" \
  -p "127.0.0.1:${LOCAL_PORT}:8000" \
  "$IMAGE_TAG" >/dev/null

if wait_for_http_200 "http://127.0.0.1:${LOCAL_PORT}/health" GET "" 40 1; then
  pass "Local Docker container responds to /health"
else
  fail "Local Docker container did not become healthy"
  hint "Check the image entrypoint and ensure uvicorn starts on port 8000."
  docker logs "$CONTAINER_NAME" | tail -50
  stop_at "Step 2"
fi

LOCAL_RESET_CODE="$(http_code POST "http://127.0.0.1:${LOCAL_PORT}/reset" '{}')"
if [ "$LOCAL_RESET_CODE" = "200" ]; then
  pass "Local Docker container responds to /reset"
else
  fail "Local Docker container /reset returned HTTP $LOCAL_RESET_CODE"
  docker logs "$CONTAINER_NAME" | tail -50
  stop_at "Step 2"
fi

log "${BOLD}Step 3/4: Running openenv validate${NC}"

if ! command -v openenv >/dev/null 2>&1; then
  fail "openenv command not found"
  hint "Install with: pip install openenv-core"
  stop_at "Step 3"
fi

VALIDATE_OK=false
VALIDATE_OUTPUT="$(cd "$REPO_DIR" && openenv validate 2>&1)" && VALIDATE_OK=true

if [ "$VALIDATE_OK" = true ]; then
  pass "openenv validate passed"
  [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"
else
  fail "openenv validate failed"
  printf "%s\n" "$VALIDATE_OUTPUT"
  stop_at "Step 3"
fi

log "${BOLD}Step 4/4: Running inference.py and validating stdout contract${NC}"

if [ ! -f "$REPO_DIR/inference.py" ]; then
  fail "inference.py not found in repo root"
  stop_at "Step 4"
fi

INFERENCE_OUT="$(portable_mktemp "inference-out")"
CLEANUP_FILES+=("$INFERENCE_OUT")

(
  cd "$REPO_DIR"
  API_BASE_URL="${API_BASE_URL:-https://api.openai.com/v1}" \
  MODEL_NAME="${MODEL_NAME:-gpt-5.4}" \
  HF_TOKEN="${HF_TOKEN:-}" \
  LEDGERSHIELD_DEBUG=0 \
  "$PYTHON_BIN" inference.py --env-url "http://127.0.0.1:${LOCAL_PORT}"
) >"$INFERENCE_OUT"

if "$PYTHON_BIN" - "$INFERENCE_OUT" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

start_re = re.compile(r"^\[START\] task=\S+ env=\S+ model=\S+$")
step_re = re.compile(r"^\[STEP\] step=\d+ action=.+ reward=-?\d+\.\d{2} done=(true|false) error=.+$")
end_re = re.compile(r"^\[END\] success=(true|false) steps=\d+ score=\d+\.\d{2} rewards=.*$")

if not lines:
    raise SystemExit("inference.py produced no stdout")

episode_count = 0
step_count = 0
end_count = 0
current_started = False

for line in lines:
    if line.startswith("[START]"):
        if not start_re.match(line):
            raise SystemExit(f"invalid [START] line: {line}")
        if current_started:
            raise SystemExit("encountered [START] before previous [END]")
        current_started = True
        episode_count += 1
        continue

    if line.startswith("[STEP]"):
        if not current_started:
            raise SystemExit("encountered [STEP] before [START]")
        if not step_re.match(line):
            raise SystemExit(f"invalid [STEP] line: {line}")
        step_count += 1
        continue

    if line.startswith("[END]"):
        if not current_started:
            raise SystemExit("encountered [END] before [START]")
        if not end_re.match(line):
            raise SystemExit(f"invalid [END] line: {line}")
        score_match = re.search(r"score=(\d+\.\d{2})", line)
        if not score_match:
            raise SystemExit(f"missing score in [END] line: {line}")
        score_value = float(score_match.group(1))
        if not (0.0 < score_value < 1.0):
            raise SystemExit(f"score out of range in [END] line: {line}")
        rewards_match = re.search(r"rewards=(.*)$", line)
        if not rewards_match:
            raise SystemExit(f"missing rewards in [END] line: {line}")
        reward_tokens = [token for token in rewards_match.group(1).split(",") if token]
        if not reward_tokens:
            raise SystemExit(f"expected at least one reward in [END] line: {line}")
        for token in reward_tokens:
            if not re.fullmatch(r"-?\d+\.\d{2}", token):
                raise SystemExit(f"invalid reward token in [END] line: {token}")
        current_started = False
        end_count += 1
        continue

    raise SystemExit(f"unexpected stdout line: {line}")

if current_started:
    raise SystemExit("missing final [END] line")
if episode_count == 0:
    raise SystemExit("no episodes were executed")
if episode_count != end_count:
    raise SystemExit("mismatched [START]/[END] counts")
if step_count < episode_count:
    raise SystemExit("expected at least one [STEP] per episode")
PY
then
  pass "inference.py completed and stdout matches the required contract"
else
  fail "inference.py output did not match the required [START]/[STEP]/[END] format"
  printf "%s\n" "Captured stdout:"
  sed -n '1,120p' "$INFERENCE_OUT"
  stop_at "Step 4"
fi

printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${GREEN}${BOLD}  All 4/4 checks passed!${NC}\n"
printf "${GREEN}${BOLD}  LedgerShield is submission-ready.${NC}\n"
printf "${BOLD}========================================${NC}\n"
printf "\n"

exit 0
