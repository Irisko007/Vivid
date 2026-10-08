# Translations

[Back to README](../README.md#languages)

## Files

- English source messages: `tr("Message")` in `vivid/`.
- Other languages: `vivid/locales/<code>.json`.
- Language names and locales: `LANGUAGES` in `vivid/i18n.py`.
- English is the fallback and the initial default, independent of system locale.

## Add or improve a language

1. Copy an existing JSON catalog.
2. Keep the English keys; translate the values.
3. Preserve placeholders such as `{path}`, `{count}`, `{extensions}` and `{error}`.
4. Preserve file patterns, keyboard shortcuts and line breaks.
5. For a new language, register its native name and locale in `LANGUAGES`.
6. Add the language to both READMEs and describe your changes in a pull request.

UI bindings refresh labels without rebuilding the native mpv surface. File names and paths are user data and are never translated. Qt standard dialogs use the installed Qt translation catalogs when available.

Language selection previews immediately across the interface and settings dialog. **Save** persists it; **Cancel** or closing settings restores the saved language. Preview state is separate from persisted settings, so background library saves cannot commit it. Settings are written atomically, and write failures keep the dialog open.

The initial translations were prepared with AI assistance. Corrections from native speakers are welcome.
