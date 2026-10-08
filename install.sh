#!/usr/bin/env bash
# Install into the current user's home. System dependencies are opt-in.
set -euo pipefail
VIVID_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VIVID_DEFAULT=0
VIVID_INSTALL_DEPS=0
for arg in "$@"; do
    case "$arg" in
        --default) VIVID_DEFAULT=1 ;;
        --install-deps) VIVID_INSTALL_DEPS=1 ;;
        --help|-h)
            printf '%s\n' 'Usage: ./install.sh [--default] [--install-deps]' '  --default       Make Vivid the default video player.' '  --install-deps  Install system dependencies using sudo (except NixOS).'
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
done
if [[ "$VIVID_INSTALL_DEPS" == 1 && ! -e /etc/NIXOS ]]; then
    VIVID_PRIVILEGE=()
    if [[ "$EUID" != 0 ]]; then
        command -v sudo >/dev/null || { printf '%s\n' 'sudo is required for --install-deps.' >&2; exit 1; }
        VIVID_PRIVILEGE=(sudo)
    fi
    if command -v apt-get >/dev/null; then
        "${VIVID_PRIVILEGE[@]}" apt-get update
        "${VIVID_PRIVILEGE[@]}" apt-get install -y python3 python3-venv mpv ffmpeg libxcb-cursor0 xdg-utils desktop-file-utils
    elif command -v dnf >/dev/null; then
        "${VIVID_PRIVILEGE[@]}" dnf install -y python3 python3-pip mpv ffmpeg-free xcb-util-cursor xdg-utils desktop-file-utils
    elif command -v pacman >/dev/null; then
        "${VIVID_PRIVILEGE[@]}" pacman -S --needed --noconfirm python python-pip mpv ffmpeg xcb-util-cursor xdg-utils desktop-file-utils
    elif command -v zypper >/dev/null; then
        "${VIVID_PRIVILEGE[@]}" zypper --non-interactive install python3 python3-pip mpv ffmpeg xcb-util-cursor xdg-utils desktop-file-utils
    else
        printf '%s\n' 'Install Python 3.10+, mpv, ffmpeg, xdg-utils and Qt XCB libraries with your package manager.' >&2
        exit 1
    fi
fi
command -v python3 >/dev/null || { printf '%s\n' 'Python 3.10+ is required.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10+ is required.")'
export VIVID_ROOT
cd -- "$VIVID_ROOT"
if [[ -e /etc/NIXOS ]]; then
    nix-build "$VIVID_ROOT/default.nix" -o "$VIVID_ROOT/result"
else
    command -v mpv >/dev/null || { printf '%s\n' 'mpv is required. Run ./install.sh --install-deps or install it manually.' >&2; exit 1; }
    if [[ ! -x .venv/bin/python ]]; then
        python3 -m venv .venv
    fi
    .venv/bin/python -m pip install --upgrade "$VIVID_ROOT"
fi
python3 - <<'PY'
import os
import shlex
from pathlib import Path
from vivid.desktop import video_mime_types
root = Path(os.environ['VIVID_ROOT'])
data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
applications = data / 'applications'
applications.mkdir(parents=True, exist_ok=True)
launcher = Path.home() / '.local/bin/vivid'
launcher.parent.mkdir(parents=True, exist_ok=True)
launcher.write_text('#!/usr/bin/env bash\nexec ' + shlex.quote(str(root / 'run.sh')) + ' "$@"\n', encoding='utf-8')
launcher.chmod(0o755)
def quote_exec(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$') + '"'
body = '\n'.join([
    '[Desktop Entry]', 'Type=Application', 'Version=1.0', 'Name=Vivid',
    'GenericName=Video Player', 'GenericName[ru]=Видеоплеер',
    'GenericName[uk]=Відеоплеєр', 'GenericName[de]=Videoplayer',
    'GenericName[es]=Reproductor de vídeo', 'GenericName[fr]=Lecteur vidéo',
    'GenericName[pt]=Reprodutor de vídeo', 'GenericName[zh_CN]=视频播放器',
    'GenericName[ja]=動画プレーヤー', 'GenericName[ar]=مشغّل الفيديو',
    'Comment=Personal Linux video player',
    'Exec=' + (quote_exec(launcher) if ' ' in str(launcher) else str(launcher)) + ' %F',
    'Icon=' + str(root / 'vivid/assets/vivid.png'),
    'Terminal=false', 'Categories=AudioVideo;Video;Player;',
    'MimeType=' + ';'.join(video_mime_types()) + ';',
    'StartupWMClass=vivid', 'StartupNotify=true', '',
])
for destination in [applications / 'io.vivid.Player.desktop', root / 'Vivid.desktop']:
    destination.write_text(body, encoding='utf-8')
    destination.chmod(0o755)
    print('Installed launcher:', destination)
(applications / 'io.luma.Player.desktop').unlink(missing_ok=True)
PY
if command -v update-desktop-database >/dev/null; then
    update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
fi
if [[ "$VIVID_DEFAULT" == 1 ]]; then
    "$VIVID_ROOT/set-default.sh"
fi
printf '%s\n' 'Vivid installed. Open it from your applications menu or run ~/.local/bin/vivid.'
