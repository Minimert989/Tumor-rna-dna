#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e .
cancer-atlas init
cancer-atlas full
