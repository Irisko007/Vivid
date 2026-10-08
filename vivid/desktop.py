"""User desktop integration, independent of Qt and the media engine."""

import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess


VIDEO_MIME_TYPES = (
    "video/3gpp", "video/3gpp2", "video/annodex", "video/dv", "video/isivideo",
    "video/mj2", "video/mp2t", "video/mp4", "video/mpeg", "video/ogg",
    "video/quicktime", "video/vnd.avi", "video/vnd.mpegurl",
    "video/vnd.radgamettools.bink", "video/vnd.radgamettools.smacker",
    "video/vnd.rn-realvideo", "video/vnd.vivo", "video/vnd.youtube.yt",
    "video/wavelet", "video/webm", "video/x-anim", "video/x-flic", "video/x-flv",
    "video/x-javafx", "video/x-matroska", "video/x-matroska-3d", "video/x-mjpeg",
    "video/x-mng", "video/x-ms-wmp", "video/x-ms-wmv", "video/x-nsv",
    "video/x-ogm+ogg", "video/x-sgi-movie", "video/x-theora+ogg",
    "video/x-msvideo", "video/x-m4v", "video/x-ms-asf",
)


def video_mime_types():
    result = set(VIDEO_MIME_TYPES)
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    locations = [data] + [Path(p) for p in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if p]
    for location in locations:
        try:
            result.update(line.strip() for line in (location / "mime/types").read_text().splitlines() if line.startswith("video/"))
        except OSError:
            pass
    return sorted(result)


def set_default():
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    desktop = data / "applications/io.vivid.Player.desktop"
    if not desktop.exists():
        raise SystemExit("Run ./install.sh first to install the Vivid launcher.")
    if not shutil.which("xdg-mime"):
        raise SystemExit("Install xdg-utils to set a default application.")
    types = video_mime_types()
    lines = desktop.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.startswith("MimeType=")]
    lines.append("MimeType=" + ";".join(types) + ";")
    desktop.write_text("\n".join(lines) + "\n", encoding="utf-8")
    backup = data / "vivid/association-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for group, directory in [("config", config), ("applications", data / "applications")]:
        for path in directory.glob("*mimeapps.list"):
            destination = backup / group / path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    subprocess.run(["xdg-mime", "default", "io.vivid.Player.desktop", *types], check=True)
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(desktop.parent)], check=True)
    if "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "") and shutil.which("kbuildsycoca6"):
        subprocess.run(["kbuildsycoca6", "--noincremental"], check=True, stdout=subprocess.DEVNULL)
    print(f"Vivid is now the default player for {len(types)} video MIME types.")
    if backup.exists():
        print("Previous associations backed up to:", backup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set Vivid as the default video player")
    parser.add_argument("--default", action="store_true", required=True)
    parser.parse_args()
    set_default()
