"""Small, atomic local library. No media content is copied into the library."""

import json
import os
from pathlib import Path
import tempfile
import time
from .i18n import normalize_language

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mpeg", ".mpg", ".ts", ".m2ts", ".wmv", ".flv", ".ogv", ".3gp"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}


class Library:
    def __init__(self):
        self.root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "vivid"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "library.json"
        self.entries = {}
        self.queue = []
        self.settings = {"theme": "light", "volume": 75, "hwdec": True, "resume": True, "autoplay": True, "video_fit": "fit", "auto_fullscreen": True, "language": "en"}
        legacy_path = self.root.parent / "luma/library.json"
        source = self.path if self.path.exists() else legacy_path
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.entries = {p: e for p, e in data.get("entries", {}).items() if isinstance(p, str) and isinstance(e, dict)}
                self.queue = [p for p in data.get("queue", []) if isinstance(p, str)]
                self.settings.update({k: v for k, v in data.get("settings", {}).items() if k in self.settings})
                if source == legacy_path:
                    self.save()
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        self.settings["language"] = normalize_language(self.settings.get("language"))

    def save(self):
        data = {"version": 1, "entries": self.entries, "queue": self.queue, "settings": self.settings}
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.root, delete=False) as f:
                name = f.name
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def add(self, paths):
        added = []
        for raw in paths:
            path = Path(raw).expanduser().resolve()
            if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue
            key = str(path)
            if key not in self.entries:
                self.entries[key] = {"name": path.stem, "added": time.time(), "played": 0, "position": 0, "duration": 0, "favorite": False}
            added.append(key)
        return added

    def recent(self, favorites=False, query=""):
        entries = [(p, e) for p, e in self.entries.items() if (not favorites or e.get("favorite")) and query.casefold() in e.get("name", "").casefold()]
        return sorted(entries, key=lambda pair: pair[1].get("played") or pair[1].get("added", 0), reverse=True)


def timestamp(value):
    seconds = max(0, int(value or 0))
    h, remaining = divmod(seconds, 3600)
    m, s = divmod(remaining, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
