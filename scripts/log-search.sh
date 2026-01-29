#!/usr/bin/env bash
set -euo pipefail

REQUEST_ID=${1:-}

if [[ -z "$REQUEST_ID" ]]; then
  echo "Usage: ./scripts/log-search.sh <request_id>"
  exit 1
fi

search_file() {
  local label=$1
  local path=$2

  echo "=== ${label} Logs ==="
  if [[ ! -f "$path" ]]; then
    echo "(missing) $path"
    return
  fi

  if command -v rg >/dev/null 2>&1; then
    rg --no-line-number --color never --fixed-strings "$REQUEST_ID" "$path" || true
  else
    grep -F "$REQUEST_ID" "$path" || true
  fi
}

search_file "Gateway" "/tmp/janus-gateway.log"
search_file "Baseline" "/tmp/janus-baseline.log"
search_file "Sandy" "/tmp/sandy.log"
