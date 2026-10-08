from pathlib import Path
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

LIGHT = {"bg": "#f7f9fc", "panel": "#ffffff", "sidebar": "#f0f4fa", "text": "#18243b", "muted": "#66758e", "border": "#e5eaf3", "hover": "#edf2fc", "blue": "#2563eb", "accent": "#2563eb", "selected": "#e1ebfe"}
DARK = {"bg": "#111827", "panel": "#192235", "sidebar": "#141d2e", "text": "#edf2fc", "muted": "#a4b2ca", "border": "#2c3850", "hover": "#25324b", "blue": "#8eb4ff", "accent": "#376bd4", "selected": "#253b61"}
THEMES = {
    "light": {"name": "Light", "dark": False, "colors": LIGHT},
    "dark": {"name": "Dark", "dark": True, "colors": DARK},
    "graphite": {"name": "Graphite", "dark": True, "colors": {"bg": "#18191c", "panel": "#23252a", "sidebar": "#1e2024", "text": "#f0f1f4", "muted": "#a8adb9", "border": "#363941", "hover": "#30333b", "blue": "#b5c7fb", "accent": "#566db0", "selected": "#353e56"}},
    "ocean": {"name": "Ocean", "dark": True, "colors": {"bg": "#0d1e2a", "panel": "#142c3c", "sidebar": "#102432", "text": "#e4f3fa", "muted": "#98b9cb", "border": "#28495c", "hover": "#1d3a4d", "blue": "#75d3ed", "accent": "#176b8d", "selected": "#1c4b60"}},
    "forest": {"name": "Forest", "dark": True, "colors": {"bg": "#12211d", "panel": "#1c3029", "sidebar": "#172822", "text": "#eaf4ee", "muted": "#a1bcad", "border": "#334e41", "hover": "#2b4236", "blue": "#94d4b2", "accent": "#2b7752", "selected": "#2c5140"}},
    "sand": {"name": "Sand", "dark": False, "colors": {"bg": "#faf7f1", "panel": "#fffdf9", "sidebar": "#f2ede3", "text": "#342f29", "muted": "#7c7163", "border": "#e7ded0", "hover": "#f3ece0", "blue": "#936132", "accent": "#936132", "selected": "#eddfc9"}},
}
_fonts_loaded = False


def load_fonts(application):
    global _fonts_loaded
    if not _fonts_loaded:
        for path in (Path(__file__).parent / "assets/fonts").glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(path))
        _fonts_loaded = True
    font = QFont("IBM Plex Sans")
    font.setPixelSize(13)
    application.setFont(font)


def palette(theme="light"):
    c = THEMES.get(theme, THEMES["light"])["colors"]
    result = QPalette()
    roles = {"Window": "bg", "WindowText": "text", "Base": "panel", "AlternateBase": "hover", "Text": "text", "Button": "panel", "ButtonText": "text", "ToolTipBase": "panel", "ToolTipText": "text", "Highlight": "accent", "Link": "blue", "PlaceholderText": "muted", "Accent": "accent", "Light": "panel", "Mid": "border", "Dark": "border"}
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        for role, key in roles.items():
            color = c["muted"] if group == QPalette.ColorGroup.Disabled and key in {"text", "blue"} else c[key]
            result.setColor(group, getattr(QPalette.ColorRole, role), QColor(color))
        result.setColor(group, QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    return result


def stylesheet(theme="light"):
    if isinstance(theme, bool):
        theme = "dark" if theme else "light"
    c = THEMES.get(theme, THEMES["light"])["colors"]
    return """
    QWidget { font-family: "IBM Plex Sans", "Noto Sans"; font-size: 13px; color: %(text)s; }
    QMainWindow, #root, #page { background: %(bg)s; }
    #sidebar { background: %(sidebar)s; border-right: 1px solid %(border)s; }
    #header { background: %(panel)s; border-bottom: 1px solid %(border)s; }
    QLabel { background: transparent; }
    #brand { font-size: 23px; font-weight: 600; letter-spacing: -0.5px; }
    #brandTag { color: %(muted)s; font-size: 10px; letter-spacing: 2px; }
    #heading { font-size: 29px; font-weight: 600; letter-spacing: -0.5px; }
    #sectionTitle { font-size: 18px; font-weight: 600; }
    #muted { color: %(muted)s; }
    #eyebrow { color: %(muted)s; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
    #badge { background: %(hover)s; color: %(blue)s; border-radius: 10px; padding: 5px 10px; font-size: 11px; }
    QPushButton, QToolButton { border: 1px solid transparent; border-radius: 7px; background: transparent; padding: 9px 12px; }
    QPushButton:hover, QToolButton:hover { background: %(hover)s; }
    QPushButton:pressed, QToolButton:pressed { background: %(selected)s; }
    QPushButton[active="true"] { background: %(selected)s; border-color: %(blue)s; }
    QPushButton:disabled, QToolButton:disabled { color: %(muted)s; }
    QPushButton:focus, QToolButton:focus { border: 1px solid %(blue)s; }
    QPushButton#primary { background: %(accent)s; color: white; font-weight: 500; padding: 10px 16px; }
    QPushButton#primary:hover { background: %(blue)s; }
    QPushButton#secondary { background: %(panel)s; border: 1px solid %(border)s; padding: 11px 18px; }
    QPushButton#secondary:hover { background: %(hover)s; border-color: %(blue)s; }
    QPushButton#nav { text-align: left; padding: 12px 15px; color: %(muted)s; font-weight: 500; }
    QPushButton#nav:checked { background: %(selected)s; color: %(blue)s; font-weight: 600; }
    QPushButton#nav:hover { background: %(hover)s; }
    #sidebarButton { text-align: left; padding: 0; border: none; border-radius: 8px; }
    #sidebarButton:hover { background: %(hover)s; }
    #sidebarButton:checked { background: %(selected)s; }
    #sidebarButton QLabel { color: %(muted)s; }
    #sidebarButton:focus { background: %(hover)s; border: none; }
    #sidebarDivider { background: %(border)s; border: none; }
    #currentTrack { background: %(panel)s; border: 1px solid %(border)s; border-radius: 9px; }
    #currentTrack QLabel { color: %(text)s; }
    #currentTrack #trackStatus { color: %(muted)s; font-size: 10px; }
    #playButton { background: %(accent)s; border: none; border-radius: 20px; padding: 9px; }
    #playButton:hover { background: %(blue)s; }
    #speedButton { background: %(hover)s; border: 1px solid %(border)s; padding: 6px 11px; font-weight: 500; }
    #speedButton[active="true"] { background: %(selected)s; border-color: %(blue)s; color: %(blue)s; }
    #speedPopup { background: %(panel)s; border: 1px solid %(border)s; border-radius: 12px; }
    #speedOption { background: %(bg)s; border: 1px solid %(border)s; font-size: 15px; font-weight: 500; padding: 10px; }
    #speedOption:hover { border-color: %(blue)s; background: %(hover)s; }
    #speedOption[selected="true"] { border-color: %(blue)s; background: %(selected)s; color: %(blue)s; }
    #themeChoice { border: 1px solid %(border)s; background: %(panel)s; padding: 5px; text-align: left; }
    #themeChoice:hover { border-color: %(blue)s; }
    #themeChoice[selected="true"] { border: 2px solid %(blue)s; background: %(hover)s; }
    #panel, #mediaCard, #settingRow { background: %(panel)s; border: 1px solid %(border)s; border-radius: 12px; }
    #mediaCard:hover { border-color: %(blue)s; }
    #queuePanel { background: %(panel)s; border-left: 1px solid %(border)s; }
    #controls { background: %(panel)s; border: 1px solid %(border)s; border-radius: 12px; }
    #footer { border-top: 1px solid %(border)s; color: %(muted)s; }
    QLineEdit { background: %(bg)s; border: 1px solid %(border)s; border-radius: 8px; padding: 9px 14px; selection-background-color: %(accent)s; selection-color: white; }
    QLineEdit:focus { border-color: %(blue)s; }
    QComboBox { background: %(panel)s; border: 1px solid %(border)s; border-radius: 6px; padding: 7px 12px; min-width: 100px; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox QAbstractItemView { background: %(panel)s; color: %(text)s; selection-background-color: %(accent)s; selection-color: white; padding: 6px; border: 1px solid %(border)s; }
    QAbstractItemView, QTreeView, QListView, QTableView { background: %(panel)s; color: %(text)s; alternate-background-color: %(hover)s; selection-background-color: %(accent)s; selection-color: white; border: 1px solid %(border)s; border-radius: 6px; }
    QTreeView::item, QListView::item { min-height: 26px; padding: 3px; }
    QTreeView::item:selected, QListView::item:selected { color: white; background: %(accent)s; }
    QTreeView::item:hover, QListView::item:hover { background: %(hover)s; color: %(text)s; }
    QHeaderView::section { background: %(sidebar)s; color: %(muted)s; border: none; border-bottom: 1px solid %(border)s; padding: 8px; }
    QFileDialog { background: %(bg)s; }
    QFileDialog QToolButton { color: %(text)s; background: %(panel)s; border: 1px solid %(border)s; padding: 6px; }
    QFileDialog QPushButton { background: %(panel)s; color: %(text)s; border: 1px solid %(border)s; min-width: 80px; }
    QMenu { background: %(panel)s; border: 1px solid %(border)s; padding: 6px; border-radius: 8px; }
    QMenu::item { padding: 9px 22px; border-radius: 5px; }
    QMenu::item:selected { background: %(selected)s; }
    QMenu::separator { height: 1px; background: %(border)s; margin: 5px; }
    QSlider::groove:horizontal { height: 4px; background: %(border)s; border-radius: 2px; }
    QSlider::sub-page:horizontal { background: %(accent)s; border-radius: 2px; }
    QSlider::handle:horizontal { background: %(accent)s; width: 12px; margin: -4px 0; border-radius: 6px; }
    QScrollArea { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 6px; margin: 3px; }
    QScrollBar::handle:vertical { background: %(border)s; border-radius: 3px; min-height: 25px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QListWidget { background: transparent; border: none; outline: none; }
    QListWidget::item { padding: 13px 10px; border-radius: 7px; margin-bottom: 4px; }
    QListWidget::item:selected { background: %(selected)s; color: %(blue)s; }
    QListWidget::item:hover { background: %(hover)s; }
    QCheckBox { spacing: 10px; }
    QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid %(border)s; border-radius: 5px; background: %(bg)s; }
    QCheckBox::indicator:checked { background: %(accent)s; border-color: %(accent)s; image: url(%(check)s); }
    QDialog { background: %(bg)s; }
    QToolTip { background: %(text)s; color: %(panel)s; padding: 6px; border: none; }
    """ % {**c, "check": str(__import__("pathlib").Path(__file__).parent / "assets/icons/check-white.svg")}
