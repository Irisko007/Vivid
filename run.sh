#!/usr/bin/env bash
set -euo pipefail
VIVID_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$VIVID_ROOT"
if [[ -x "$VIVID_ROOT/result/bin/vivid" ]]; then
    exec "$VIVID_ROOT/result/bin/vivid" "$@"
fi
if [[ -x "$VIVID_ROOT/.venv/bin/python" ]]; then
    exec "$VIVID_ROOT/.venv/bin/python" -m vivid "$@"
fi
if [[ -e /etc/NIXOS ]] && command -v nix-shell >/dev/null && ! python3 -c 'import PySide6.QtWidgets' >/dev/null 2>&1; then
    VIVID_ARGS=(python3 -m vivid "$@")
    printf -v VIVID_COMMAND '%q ' "${VIVID_ARGS[@]}"
    exec nix-shell "$VIVID_ROOT/shell.nix" --run "$VIVID_COMMAND"
fi
exec python3 -m vivid "$@"
