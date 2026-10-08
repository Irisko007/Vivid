"""Original generated SVG controls; scalable, cached and theme aware."""

from pathlib import Path
from functools import lru_cache
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).parent / "assets"
PATHS = {
    "aspect": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M5 12h14m-11-3-3 3 3 3m8-6 3 3-3 3"/>',
    "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
    "library": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "star": '<path d="m12 3 2.8 5.8 6.4.9-4.6 4.5 1.1 6.4-5.7-3-5.7 3 1.1-6.4L2.8 9.7l6.4-.9Z"/>',
    "queue": '<path d="M4 5h16M4 10h16M4 15h8M4 20h8"/><path d="m16 14 5 3-5 3Z"/>',
    "settings": '<path d="m10 3-.6 2.2-2 .9-2-.6-2 3.4 1.5 1.6v3l-1.5 1.6 2 3.4 2-.6 2 .9.6 2.2h4l.6-2.2 2-.9 2 .6 2-3.4-1.5-1.6v-3l1.5-1.6-2-3.4-2 .6-2-.9L14 3Z"/><circle cx="12" cy="12" r="3"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "plus": '<path d="M12 4v16M4 12h16"/>',
    "folder": '<path d="M3 7V5a1 1 0 0 1 1-1h5l2 3h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/>',
    "file": '<path d="M14 3H5v18h14V8Z"/><path d="M14 3v5h5m-10 4 5 3-5 3Z"/>',
    "play": '<path d="m8 4 12 8-12 8Z" fill="currentColor" stroke-linejoin="round"/>',
    "pause": '<rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor"/>',
    "previous": '<path d="M5 5v14m14-14L8 12l11 7Z"/>',
    "next": '<path d="M19 5v14M5 5l11 7-11 7Z"/>',
    "rewind": '<path d="M4 9a8 8 0 1 1 1 9M4 4v5h5"/><text x="7" y="16" stroke="none" fill="currentColor" font-family="sans-serif" font-size="9" font-weight="600">10</text>',
    "forward": '<path d="M20 9a8 8 0 1 0-1 9m1-14v5h-5"/><text x="7" y="16" stroke="none" fill="currentColor" font-family="sans-serif" font-size="9" font-weight="600">10</text>',
    "volume": '<path d="M3 9v6h4l5 4V5L7 9Zm13-1a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
    "mute": '<path d="M3 9v6h4l5 4V5L7 9Zm13 0 6 6m0-6-6 6"/>',
    "fullscreen": '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
    "collapse": '<path d="M3 8h5V3m13 5h-5V3M8 21v-5H3m13 5v-5h5"/>',
    "subtitle": '<rect x="2" y="4" width="20" height="16" rx="3"/><path d="M6 12h4m4 0h4M6 16h7m3 0h2"/>',
    "audio": '<path d="M5 15v-3a7 7 0 0 1 14 0v3"/><rect x="3" y="12" width="4" height="8" rx="2"/><rect x="17" y="12" width="4" height="8" rx="2"/>',
    "more": '<circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "chevron": '<path d="m9 5 7 7-7 7"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>',
    "moon": '<path d="M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11Z"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    "repeat": '<path d="M4 10V8a3 3 0 0 1 3-3h13m-4-3 4 3-4 3M20 14v2a3 3 0 0 1-3 3H4m4-3-4 3 4 3"/>',
    "camera": '<path d="M8 5 6 8H3v12h18V8h-3l-2-3Z"/><circle cx="12" cy="13" r="4"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.2"/>',
    "keyboard": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M6 9h.1m4 0h.1m4 0h.1m4 0h.1M6 13h.1m4 0h.1m4 0h.1m4 0h.1M8 16h8"/>',
}
_cache = {}


def svg(name, color="#475569"):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" color="{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["film"])}</svg>'


def icon(name, color="#475569"):
    key = (name, color)
    if key not in _cache:
        result = QIcon()
        renderer = QSvgRenderer(QByteArray(svg(name, color).encode()))
        for size in (20, 24, 32, 48, 64):
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            renderer.render(painter)
            painter.end()
            result.addPixmap(pix)
        _cache[key] = result
    return _cache[key]


@lru_cache(maxsize=1)
def app_icon():
    return QIcon(str(ASSETS / "vivid.png")) if (ASSETS / "vivid.png").exists() else icon("play", "#2563eb")
