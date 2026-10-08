"""JSON translation catalogs and bindings that leave native video widgets intact."""

import json
import os
from pathlib import Path

LANGUAGES = {
    "en": ("English", "en_US"), "ru": ("Русский", "ru_RU"),
    "uk": ("Українська", "uk_UA"), "de": ("Deutsch", "de_DE"),
    "es": ("Español", "es_ES"), "fr": ("Français", "fr_FR"),
    "pt": ("Português", "pt_BR"), "zh": ("简体中文", "zh_CN"),
    "ja": ("日本語", "ja_JP"), "ar": ("العربية", "ar_SA"),
}
_language = "en"
_catalog = {}


def normalize_language(code):
    return code if isinstance(code, str) and code in LANGUAGES else "en"


class TranslatedText(str):
    def __new__(cls, source="", values=None, parts=None):
        instance = super().__new__(cls, cls._render(source, values or {}, parts))
        instance.source, instance.values, instance.parts = source, values or {}, parts
        return instance

    @staticmethod
    def _render(source, values, parts):
        if parts is not None:
            return "".join(p.render() if isinstance(p, TranslatedText) else str(p) for p in parts)
        message = _catalog.get(source, source)
        if not values:
            return message
        values = {k: v.render() if isinstance(v, TranslatedText) else v for k, v in values.items()}
        return message.format(**values)

    def render(self):
        return self._render(self.source, self.values, self.parts)

    def __add__(self, other):
        return TranslatedText(parts=(self, other))

    def __radd__(self, other):
        return TranslatedText(parts=(other, self))


def tr(source, **values):
    return TranslatedText(source, values)


def bind_text(widget, method, text):
    """Record translated values; a later plain value clears a previous binding."""
    bindings = getattr(widget, "_vivid_text_bindings", None)
    if isinstance(text, TranslatedText):
        if bindings is None:
            bindings = widget._vivid_text_bindings = {}
        bindings[method] = text
        text = text.render()
    elif bindings:
        bindings.pop(method, None)
    getattr(widget, method)(text)


def retranslate(root):
    from PySide6.QtWidgets import QWidget
    for widget in [root, *root.findChildren(QWidget)]:
        for method, text in list(getattr(widget, "_vivid_text_bindings", {}).items()):
            bind_text(widget, method, text)


def set_language(code, application):
    global _language, _catalog
    from PySide6.QtCore import QLibraryInfo, QLocale, Qt, QTranslator
    _language = normalize_language(code)
    _catalog = {}
    if _language != "en":
        path = Path(__file__).parent / "locales" / (_language + ".json")
        _catalog = json.loads(path.read_text(encoding="utf-8"))
    locale = QLocale(LANGUAGES[_language][1])
    QLocale.setDefault(locale)
    application.setLayoutDirection(Qt.LayoutDirection.RightToLeft if _language == "ar" else Qt.LayoutDirection.LeftToRight)
    previous = getattr(application, "_vivid_translator", None)
    if previous is not None:
        application.removeTranslator(previous)
        previous.deleteLater()
    application._vivid_translator = None
    if _language != "en":
        translator = QTranslator(application)
        location = os.environ.get("VIVID_TRANSLATIONS_DIR", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
        if translator.load(locale, "qtbase", "_", location):
            application.installTranslator(translator)
            application._vivid_translator = translator
    return _language
