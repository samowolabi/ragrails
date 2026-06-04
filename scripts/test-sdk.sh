#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UV="${UV:-uv}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"

"$UV" run python -m unittest discover ragrails/interfaces/sdk "$@"
