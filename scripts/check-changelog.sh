#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UV="${UV:-uv}"

VERSION="$(
  "$UV" run --locked python - <<'PY'
from pathlib import Path

for line in Path("pyproject.toml").read_text().splitlines():
    if line.startswith("version = "):
        print(line.split('"', 2)[1])
        break
else:
    raise SystemExit("Could not find project version in pyproject.toml")
PY
)"

if [[ ! -f CHANGELOG.md ]]; then
  printf "CHANGELOG.md is missing\n" >&2
  exit 1
fi

if ! grep -q "^## \\[$VERSION\\]" CHANGELOG.md; then
  printf "CHANGELOG.md does not contain a section for version %s\n" "$VERSION" >&2
  printf "Add a section like: ## [%s] - YYYY-MM-DD\n" "$VERSION" >&2
  exit 1
fi

if ! grep -q "^## \\[Unreleased\\]" CHANGELOG.md; then
  printf "CHANGELOG.md does not contain an [Unreleased] section\n" >&2
  exit 1
fi

printf "Changelog OK for version %s\n" "$VERSION"
