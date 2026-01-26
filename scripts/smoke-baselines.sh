#!/bin/bash

set -euo pipefail

python tests/smoke_baselines.py "$@"
