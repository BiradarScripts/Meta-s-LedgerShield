#!/usr/bin/env bash
#
# validate-submission.sh — LedgerShield Submission Validator
#
# Checks that your HF Space is live, Docker image builds, and openenv validate passes.
#
# Prerequisites:
#   - Docker:       https://docs.docker.com/get-docker/
#   - openenv-core: pip install openenv-core
#   - curl (usually pre-installed)
#
# Run:
#   ./validate-submission.sh <ping_url> [repo_dir]
#
# Arguments:
#   ping_url   Your HuggingFace Space URL (e.g. https://your-space.hf.space)
#   repo_dir   Path to your repo (default: current directory)
#

set -uo pipefail

DOCKER_BUILD_TIMEOUT=600
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
  if command -v timeout &>/dev/null; then
    timeout "$secs" "$@"
  elif command -v gtimeout &>/dev/null; then
    gtimeout "$secs" "$@"
  else
    "$@" &
    local pid=$!
    ( sleep "$secs" && kill "$pid" 2>/dev/null ) &
    local watcher=$!
    wait "$pid" 2>/dev/null
    local rc=$?
    kill "$watcher" 2>/dev/null
    wait "$watcher" 2>/dev/null
    return $rc
  fi
}

portable_mktemp() {
  local prefix="${1:-validate}"
  mktemp "${TMPDIR:-/tmp}/${prefix}-XXXXXX" 2>/dev/null || mktemp
}

CLEANUP_FILES=()
cleanup() { rm -f "${CLEANUP_FILES[@]+"${CLEANUP_FILES[@]}"}"; }
trap cleanup EXIT

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  printf "Usage: %s <ping_url> [repo_dir]\n" "$0"
  printf "\n"
  printf "  ping_url   Your HuggingFace Space URL (e.g. https://your-space.hf.space)\n"
  printf "  repo_dir   Path to your repo (default: current directory)\n"
  exit 1
fi

if ! REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd)"; then
  printf "Error: directory '%s' not found\n" "${2:-.}"
  exit 1
fi
PING_URL="${PING_URL%/}"
export PING_URL
PASS=0

log() { printf "  %s\n" "$*"; }
pass() { printf "${GREEN}✓${NC} %s\n" "$*"; ((PASS++)); }
fail() { printf "${RED}✗${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}!${NC} %s\n" "$*"; }
stop_at() {
  printf "\n${RED}========================================${NC}\n"
  printf "${RED}  Stopped at: %s${NC}\n" "$1"
  printf "${RED}========================================${NC}\n\n"
  exit 1
}

printf "${BOLD}========================================${NC}\n"
printf "${BOLD}  LedgerShield Submission Validator${NC}\n"
printf "${BOLD}========================================${NC}\n\n"

printf "${BOLD}Step 1/3: Checking HF Space (${PING_URL})${NC}\n"
log "Pinging ${PING_URL}..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "${PING_URL}" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
  pass "HF Space is live (HTTP 200)"
  
  log "Checking /reset endpoint..."
  RESET_RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 -X POST "${PING_URL}/reset" -H "Content-Type: application/json" -d '{"seed":42}' 2>/dev/null || echo "000")
  
  if [ "$RESET_RESP" = "200" ]; then
    pass "reset() endpoint responds correctly"
  else
    warn "reset() endpoint returned ${RESET_RESP} (may still be OK if space is stateless)"
  fi
else
  fail "HF Space returned HTTP ${HTTP_CODE}"
  if [ "$HTTP_CODE" = "000" ]; then
    warn "Could not connect - is the space URL correct?"
  fi
  stop_at "Step 1"
fi

printf "\n${BOLD}Step 2/3: Running docker build${NC}\n"

if ! command -v docker &>/dev/null; then
  warn "docker command not found"
  warn "Install Docker: https://docs.docker.com/get-docker/"
  stop_at "Step 2"
fi

if [ -f "$REPO_DIR/envs/ledgershield_env/server/Dockerfile" ]; then
  DOCKERFILE="$REPO_DIR/envs/ledgershield_env/server/Dockerfile"
  DOCKER_CONTEXT="$REPO_DIR/envs/ledgershield_env/server"
elif [ -f "$REPO_DIR/Dockerfile" ]; then
  DOCKERFILE="$REPO_DIR/Dockerfile"
  DOCKER_CONTEXT="$REPO_DIR"
else
  fail "No Dockerfile found"
  stop_at "Step 2"
fi

log "Found Dockerfile at $DOCKERFILE"
log "Building Docker image (timeout: ${DOCKER_BUILD_TIMEOUT}s)..."

BUILD_OK=false
BUILD_OUTPUT=$(run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build "$DOCKER_CONTEXT" -f "$DOCKERFILE" 2>&1) && BUILD_OK=true

if [ "$BUILD_OK" = true ]; then
  pass "Docker build succeeded"
else
  fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"
  printf "%s\n" "$BUILD_OUTPUT" | tail -20
  stop_at "Step 2"
fi

printf "\n${BOLD}Step 3/3: Running openenv validate${NC}\n"

if ! command -v openenv &>/dev/null; then
  warn "openenv command not found"
  warn "Install it: pip install openenv-core"
  log "Skipping openenv validation (can run manually with: pip install openenv-core && openenv validate)"
else
  VALIDATE_OK=false
  VALIDATE_OUTPUT=$(cd "$REPO_DIR/envs/ledgershield_env" && openenv validate 2>&1) && VALIDATE_OK=true

  if [ "$VALIDATE_OK" = true ]; then
    pass "openenv validate passed"
    [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"
  else
    fail "openenv validate failed"
    printf "%s\n" "$VALIDATE_OUTPUT"
    stop_at "Step 3"
  fi
fi

printf "\n"
printf "${BOLD}========================================${NC}\n"
printf "${GREEN}${BOLD}  All 3/3 checks passed!${NC}\n"
printf "${GREEN}${BOLD}  Your submission is ready to submit.${NC}\n"
printf "${BOLD}========================================${NC}\n"
printf "\n"

exit 0
