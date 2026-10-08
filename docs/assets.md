# Asset provenance

[Back to README](../README.md#about)

Vivid was created for personal use with AI assistance. The application icon was generated with AI; the control icons are original programmatically generated SVG assets.

## Application icon

- File: `vivid/assets/vivid.png`.
- Original transparent PNG, generated with OpenAI image generation.
- Retained when the application was renamed from Luma to Vivid.
- Contains no lettering and no Microsoft logos.

Original prompt:

> Use case: logo-brand. Asset type: Linux desktop video player application icon, transparent PNG. Primary request: create one original polished Microsoft 365 Fluent inspired app icon for a video player called Luma. Subject: a rounded square formed from flowing folded translucent blue and indigo ribbons, with a clean luminous white triangular play symbol in the center, three dimensional soft sculpted glass depth, restrained premium corporate design, very legible at 32 pixels. Color palette: azure blue #2563eb, cyan highlights, deep violet #5b42ce. Composition: square, single large centered icon with generous transparent margin around the silhouette. Constraints: genuine transparent background, no lettering, no Microsoft logos, no shadows outside the icon, no other objects, no watermark.

## Control icons

Original SVG files in `vivid/assets/icons/`, defined in `vivid/icons.py`. A shared 24 × 24 grid, rounded strokes and theme-aware colors. Qt caches rasterized sizes. No external icon pack is included.

## Fonts

IBM Plex Sans Regular, Medium and SemiBold are included in `vivid/assets/fonts/`. Original font files come from the [official IBM Plex repository](https://github.com/IBM/plex/tree/master/packages/plex-sans/fonts/complete/ttf). Their [SIL Open Font License](../vivid/assets/fonts/OFL.txt) is included and preserved.

Qt uses installed system fallback fonts for Chinese, Japanese, Arabic and other scripts not covered by IBM Plex Sans.
