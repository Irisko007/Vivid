<div align="center">
  <img src="vivid/assets/vivid.png" alt="Vivid icon" width="88">
  <h1>Vivid</h1>
  <p>A native Linux video player with a Fluent inspired interface, Qt and mpv.</p>
  <p><strong>Created for personal use with AI assistance.</strong></p>
  <p>
    <a href="https://github.com/Irisko007/Vivid/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/Irisko007/Vivid"></a>
    <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
    <img alt="Linux" src="https://img.shields.io/badge/platform-Linux-2563eb">
    <img alt="10 languages" src="https://img.shields.io/badge/languages-10-2563eb">
  </p>
</div>

**English** · [Русский](README.ru.md)

[Install](#install) · [Features](#features) · [Languages](#languages) · [Controls](#controls) · [Data](#data) · [Development](#development) · [About](#about)

## Install

### Download and install

Requires `bash`, `curl`, Python 3.10+, `tar` and `sha256sum`.

```bash
curl -fsSL https://raw.githubusercontent.com/Irisko007/Vivid/main/scripts/download-install.sh -o /tmp/vivid-install.sh
bash /tmp/vivid-install.sh --install-deps --default
```

The script downloads the latest release, verifies its SHA-256 checksum, installs Vivid in `~/.local/share/vivid/app`, and adds an application menu entry. Running it again updates the installation. Library and settings stay in a separate data file.

| Option | Action |
|---|---|
| `--install-deps` | Install system dependencies using sudo on Debian/Ubuntu, Fedora, Arch or openSUSE; NixOS uses Nix. |
| `--default` | Make Vivid the default video viewer for the current user. |
| No options | Install Vivid using dependencies already present. |

Package availability depends on the distribution and enabled repositories. If a package is unavailable, install it manually and rerun without `--install-deps`.

### From source

```bash
git clone https://github.com/Irisko007/Vivid.git
cd Vivid
./install.sh --install-deps --default
./run.sh
```

On NixOS, `./install.sh --default` builds the included Nix package. On other distributions, the installer creates a local Python virtual environment. Requires **mpv**, **FFmpeg** for thumbnails, Qt XCB libraries and **xdg-utils** for default associations.

### Launch and defaults

```bash
~/.local/bin/vivid                    # Library
~/.local/bin/vivid '/path/video.mkv'   # Windowed viewer
~/.local/bin/vivid --viewer           # Empty viewer
./set-default.sh                     # Register video defaults later
```

Requires **X11**, or **Wayland with XWayland**. Native Wayland embedding is not supported yet. Add `~/.local/bin` to your PATH to use `vivid` without its full path.

## Features

- Windowed viewer when opening files; move and resize it like a regular desktop window.
- Hardware decoding through mpv with software fallback; no browser engine.
- Library, favorites, play queue, playback resume and automatic next video.
- Subtitles, audio tracks, screenshots and playback speed from 0.25× to 2×.
- Fit, fill with cropping, and stretch modes; no re-encoding.
- Six themes, live theme preview, and short interface transitions.
- Controls hide after 2.5 seconds of inactivity. Files opened externally stay windowed.
- Local settings saved atomically. No account, telemetry or cloud storage.

MP4, MKV, WebM, MOV, AVI and other supported formats depend on the installed mpv/FFmpeg codecs. Folder imports include files directly inside the chosen folder.

## Languages

**English is the default on first launch.** Open **Settings → Interface language**, choose a language to preview it immediately throughout the interface, including the settings dialog. Playback continues. Press **Save** to keep the choice; **Cancel** or closing settings restores the saved language. Automatic library saves do not commit a preview. The saved language is restored next time.

English · Русский · Українська · Deutsch · Español · Français · Português · 简体中文 · 日本語 · العربية

Arabic uses a right-to-left interface. Your system needs fonts for the selected language. IBM Plex Sans is bundled; Qt uses system fallback fonts for other scripts.

## Controls

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open video |
| `Space` | Play / pause |
| `←` / `→` | Seek 10 seconds |
| `↑` / `↓` | Adjust volume |
| `M` | Mute |
| `F` / `F11`, double-click video | Toggle fullscreen |
| `Esc` | Leave fullscreen |
| `Ctrl+←` / `Ctrl+→` | Previous / next video |
| `Ctrl+P` | Play queue |
| `Ctrl+S` | Save frame |
| `Ctrl+L` | Library search |
| `Ctrl+Q` | Quit |

Viewer settings and the library are also available in the **…** menu.

## Data

| Item | Default location |
|---|---|
| Library, language and settings | `~/.local/share/vivid/library.json` |
| Thumbnail cache | `~/.cache/vivid/thumbnails/` |
| Window geometry | `~/.config/Vivid/Player.conf` |
| Saved frames | `~/Pictures/Vivid/` |
| Default association backups | `~/.local/share/vivid/association-backups/` |
| Downloaded application | `~/.local/share/vivid/app/` |

`XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` are respected. Override the download destination with `VIVID_INSTALL_DIR`. Existing Luma library data is copied on first use when no Vivid library exists. Removing a library entry leaves the original video file in place.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
./run.sh
# NixOS alternative
nix-shell --run 'python3 -m vivid'
```

```bash
python3 scripts/package.py                 # Linux bundle + checksum
python3 -m pip install build
python3 -m build                           # Python wheel + source distribution
nix-build                                 # Nix package
```

[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [Translation guide](docs/translations.md) · [Assets](docs/assets.md) · [Report a bug](https://github.com/Irisko007/Vivid/issues/new/choose)

## About

Vivid is a personal project by [Irisko007](https://github.com/Irisko007), created for personal use with AI assistance. AI assisted the implementation and creation of the application icon. It is an independent project inspired by Fluent design.

Application code: [MIT](LICENSE). Qt, mpv and IBM Plex fonts retain their respective licenses. See [asset provenance](docs/assets.md) for details.
