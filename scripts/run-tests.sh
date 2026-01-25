#!/usr/bin/env bash

set -euo pipefail

TEST_MODE=${1:-local}
export TEST_MODE

echo "=== Janus Comprehensive Test Suite ==="
echo ""
echo "Test mode: ${TEST_MODE}"
echo ""

failed=0

run_group() {
  local title="$1"
  shift
  echo "=== ${title} ==="
  if ! "$@"; then
    failed=1
  fi
  echo ""
}

run_group "Gateway Unit Tests" bash -c "cd gateway && pytest -v --tb=short"
run_group "Baseline CLI Unit Tests" bash -c "cd baseline-agent-cli && pytest -v --tb=short"
if python - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("langchain_core") else 1)
PY
then
  run_group "Baseline LangChain Unit Tests" bash -c "cd baseline-langchain && pytest -v --tb=short"
else
  echo "=== Baseline LangChain Unit Tests ==="
  echo "Skipping: langchain_core not installed"
  echo ""
fi
run_group "UI Tests" bash -c "cd ui && npm test"

run_group "Integration Tests (${TEST_MODE})" pytest tests/integration -v --tb=short
run_group "Smoke Tests" pytest tests/smoke -v --tb=short
run_group "Visual Tests" bash -c "pytest tests/visual -v --tb=short; rc=\$?; if [ \$rc -ne 0 ] && [ \$rc -ne 5 ]; then exit \$rc; fi"

echo "=== Test Suite Complete ==="
echo "Screenshots saved to: ./test-screenshots/"

if [ "${failed}" -ne 0 ]; then
  echo "One or more test groups failed."
  exit 1
fi
