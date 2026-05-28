#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UV="${UV:-uv}"

"$UV" run --locked python -m unittest discover \
  -s tests/cli \
  -p "test_*.py" \
  -v
