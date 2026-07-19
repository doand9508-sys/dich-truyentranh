# Fonts

`config.DEFAULT_FONT_PATH` points to `NotoSans-Bold.ttf` in this folder.
This repo does not ship font binaries — download one of these (both fully
support Vietnamese diacritics) and drop it here with that exact filename,
or update `DEFAULT_FONT_PATH` in `config.py`:

- Noto Sans (Bold): https://fonts.google.com/noto/specimen/Noto+Sans
- Be Vietnam Pro (Bold): https://fonts.google.com/specimen/Be+Vietnam+Pro

Without a font file here, `typesetting.py` falls back to PIL's built-in
bitmap font so the app still runs — but Vietnamese diacritics will not
render correctly, so this step is required before shipping real output.
