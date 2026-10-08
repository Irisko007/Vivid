#!/usr/bin/env bash
# Download the latest versioned GitHub release and verify it before installing.
set -euo pipefail
VIVID_DEFAULT=0
VIVID_INSTALL_DEPS=0
for arg in "$@"; do
    case "$arg" in
        --default) VIVID_DEFAULT=1 ;;
        --install-deps) VIVID_INSTALL_DEPS=1 ;;
        --help|-h)
            printf '%s\n' 'Usage: download-install.sh [--default] [--install-deps]' 'Destination: $VIVID_INSTALL_DIR or $XDG_DATA_HOME/vivid/app (~/.local/share/vivid/app).'
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
done
for VIVID_TOOL in curl python3 tar sha256sum; do
    command -v "$VIVID_TOOL" >/dev/null || { printf 'Required command: %s\n' "$VIVID_TOOL" >&2; exit 1; }
done
VIVID_TMP="$(mktemp -d)"
VIVID_TARGET="${VIVID_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/vivid/app}"
VIVID_BACKUP=""
VIVID_REPLACED=0
VIVID_SUCCESS=0
vivid_cleanup() {
    if [[ "$VIVID_REPLACED" == 1 && "$VIVID_SUCCESS" == 0 ]]; then
        rm -rf -- "$VIVID_TARGET"
        if [[ -n "$VIVID_BACKUP" ]]; then
            mv -- "$VIVID_BACKUP" "$VIVID_TARGET"
        fi
    fi
    rm -rf -- "$VIVID_TMP"
}
trap vivid_cleanup EXIT
curl --fail --location --silent --show-error --retry 2 --connect-timeout 15 --max-time 60 \
    https://api.github.com/repos/Irisko007/Vivid/releases/latest -o "$VIVID_TMP/release.json"
VIVID_TAG="$(python3 - "$VIVID_TMP/release.json" <<'PY'
import json, re, sys
with open(sys.argv[1]) as stream:
    tag = json.load(stream)['tag_name']
if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag):
    raise SystemExit('Unexpected release tag.')
print(tag)
PY
)"
VIVID_BASE="https://github.com/Irisko007/Vivid/releases/download/$VIVID_TAG"
for VIVID_ASSET in vivid-linux.tar.gz SHA256SUMS; do
    curl --fail --location --silent --show-error --retry 2 --connect-timeout 15 --max-time 300 \
        "$VIVID_BASE/$VIVID_ASSET" -o "$VIVID_TMP/$VIVID_ASSET"
done
(cd -- "$VIVID_TMP" && sha256sum --check --strict SHA256SUMS)
mkdir -- "$VIVID_TMP/unpacked"
tar -xzf "$VIVID_TMP/vivid-linux.tar.gz" -C "$VIVID_TMP/unpacked"
[[ -f "$VIVID_TMP/unpacked/vivid/install.sh" && -f "$VIVID_TMP/unpacked/vivid/pyproject.toml" ]] || { printf '%s\n' 'Incomplete release archive.' >&2; exit 1; }
if [[ -L "$VIVID_TARGET" || ( -e "$VIVID_TARGET" && ! -f "$VIVID_TARGET/vivid/__init__.py" ) ]]; then
    printf 'Refusing to replace a directory that is not a Vivid installation: %s\n' "$VIVID_TARGET" >&2
    exit 1
fi
mkdir -p -- "$(dirname -- "$VIVID_TARGET")"
if [[ -d "$VIVID_TARGET" ]]; then
    VIVID_BACKUP="$(mktemp -d "${VIVID_TARGET}.previous.XXXXXX")"
    rmdir -- "$VIVID_BACKUP"
    mv -- "$VIVID_TARGET" "$VIVID_BACKUP"
fi
VIVID_REPLACED=1
mv -- "$VIVID_TMP/unpacked/vivid" "$VIVID_TARGET"
VIVID_OPTIONS=()
[[ "$VIVID_DEFAULT" == 0 ]] || VIVID_OPTIONS+=(--default)
[[ "$VIVID_INSTALL_DEPS" == 0 ]] || VIVID_OPTIONS+=(--install-deps)
"$VIVID_TARGET/install.sh" "${VIVID_OPTIONS[@]}"
VIVID_SUCCESS=1
if [[ -n "$VIVID_BACKUP" ]]; then
    rm -rf -- "$VIVID_BACKUP"
fi
printf 'Installed Vivid %s in %s\n' "$VIVID_TAG" "$VIVID_TARGET"
