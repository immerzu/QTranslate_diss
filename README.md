# QTranslate 6.9.0 patch workspace

This repository contains the source-level patch work for a modified QTranslate 6.9.0 portable build.

The repository intentionally tracks patch sources and service JavaScript only. Prebuilt executables, portable archives, service `.rar` files, temporary traces, and local runtime data are excluded from Git and should be published as GitHub Release assets when needed.

## Current focus

- Preserve browser and clipboard links through QTranslate capture paths.
- Render translated output links with visible anchors and hidden URL backing text.
- Keep popup link clicks, selection, copy, and cursor behavior stable.
- Protect URLs, file names, versions, and technical paths from service/post-processing punctuation splitting.
- Keep service text transformations lossless and format-oriented only.

## Important files

- `asm/read_html_or_unicode_clipboard.s`: clipboard and HTML link preservation hook.
- `asm/format_output_links.s`: output RichEdit link formatting, hidden URL suffixes, and click fallback.
- `scripts/patch_qtranslate_links.py`: binary patcher for capture/accessibility link preservation.
- `scripts/patch_qtranslate_output_links.py`: binary patcher for output RichEdit link rendering.
- `scripts/build_qtranslate_portable_clean.ps1`: local portable builder.
- `QTranslate.6.9.0/Services/Common.js`: shared service helpers.
- `QTranslate.6.9.0/Services/Multi/Service.js`: active Multi/FreeTranslations service path hardening.

## Build notes

This workspace expects an unpacked local QTranslate 6.9.0 tree at `QTranslate.6.9.0`. The Git repository does not store QTranslate binaries or generated portable packages.

Typical local flow:

```powershell
python .\scripts\patch_qtranslate_links.py --with-accessibility-main
python .\scripts\patch_qtranslate_output_links.py
powershell -ExecutionPolicy Bypass -File .\scripts\build_qtranslate_portable_clean.ps1
```

The clean portable builder removes packed service archives from the output and sets the default portable profile to German UI with automatic source detection to German translation.

## Release handling

Do not commit generated packages to Git. Put final portable archives on GitHub Releases instead.

Local release artifacts may exist under:

- `Ausgabe/`
- `release/`

Both directories are ignored by Git.
