#!/usr/bin/env bash

set -euo pipefail

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

has_pytest_cov() {
  python - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("pytest_cov") else 1)
PY
}

run_pytest() {
  local cov_target="$1"
  shift 1
  if has_pytest_cov; then
    pytest "$@" --cov="$cov_target" --cov-report=term-missing
  else
    pytest "$@"
  fi
}

run_pytest_in_dir() {
  local dir="$1"
  local cov_target="$2"
  shift 2
  pushd "$dir" >/dev/null
  run_pytest "$cov_target" "$@"
  popd >/dev/null
}

run_group "Gateway Unit Tests" run_pytest_in_dir gateway janus_gateway tests/unit -v --tb=short
run_group "Baseline CLI Unit Tests" run_pytest_in_dir baseline-agent-cli janus_baseline_agent_cli tests/unit -v --tb=short
run_group "Baseline LangChain Unit Tests" run_pytest_in_dir baseline-langchain janus_baseline_langchain tests/unit -v --tb=short
run_group "UI Unit Tests" bash -c "cd ui && npm run test:unit"

if [ "${failed}" -ne 0 ]; then
  echo "One or more unit test groups failed."
  exit 1
fi

echo "SUCCESS: All unit tests passed."
