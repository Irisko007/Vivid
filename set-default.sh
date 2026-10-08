#!/usr/bin/env bash
set -euo pipefail
VIVID_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$VIVID_ROOT"
exec python3 -m vivid.desktop --default
