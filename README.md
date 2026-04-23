# QTranslate 6.9.0 Patch Workspace

Source-level patch workspace for a hardened QTranslate 6.9.0 portable build.

This repository focuses on the parts that were actually changed: ASM hooks, patch/build scripts, native helper code, notes, and the unpacked service sources used by the runtime. Generated binaries, portable archives, packed service `.rar` files, traces, and local runtime state stay out of Git and belong in GitHub Releases instead.

## What this repo improves

- Preserves browser and clipboard links through QTranslate capture paths.
- Renders translated popup links as readable anchors with hidden backing URLs.
- Keeps popup click, hover cursor, selection, and copy behavior stable.
- Protects URLs, file names, version strings, and technical paths from punctuation splitting in the active service path.
- Keeps service-side text handling lossless and format-oriented instead of semantically rewriting content.

## Repository layout

- `asm/`
  Binary patch payloads for clipboard capture and popup output behavior.
- `scripts/`
  Patchers, probes, tracing helpers, smoke tests, and portable build scripts.
- `native/`
  Small native helpers used during accessibility and UIA experiments.
- `notes/`
  Investigation notes and findings from the reverse-engineering and validation work.
- `QTranslate.6.9.0/Services/`
  Unpacked service sources used for the JavaScript-side fixes.

## Key files

- `asm/read_html_or_unicode_clipboard.s`
  Preserves HTML/clipboard links in the capture path.
- `asm/format_output_links.s`
  Formats popup RichEdit output, keeps hidden URL backing text, and handles click/hover fallback logic.
- `scripts/patch_qtranslate_links.py`
  Applies the capture/accessibility-side binary patch.
- `scripts/patch_qtranslate_output_links.py`
  Applies the popup output RichEdit patch.
- `scripts/build_qtranslate_portable_clean.ps1`
  Builds a fresh portable package from the patched local tree.
- `QTranslate.6.9.0/Services/Common.js`
  Shared service helpers.
- `QTranslate.6.9.0/Services/Multi/Service.js`
  The active Multi/FreeTranslations runtime path that needed URL/token hardening.

## Quick start

Prerequisite: an unpacked local QTranslate 6.9.0 tree at `QTranslate.6.9.0`.

```powershell
python .\scripts\patch_qtranslate_links.py --with-accessibility-main
python .\scripts\patch_qtranslate_output_links.py
powershell -ExecutionPolicy Bypass -File .\scripts\build_qtranslate_portable_clean.ps1
```

The clean portable builder:

- removes packed service archives from the portable output
- keeps services unpacked under `Services`
- prepares the German portable profile with auto-detect source to German translation

## Build and release

- Short local build guide: [Docs/BUILD.md](Docs/BUILD.md)
- Current release notes: [RELEASE_NOTES.md](RELEASE_NOTES.md)
- Portable packages should be published as GitHub Release assets, not committed into the repo

Ignored local output directories:

- `Ausgabe/`
- `release/`

## Notes

- OCR text recognition depends on the external OCR.space service. Without a personal OCR API key, OCR requests can be rate-limited by that external service.
- The repository intentionally excludes original QTranslate binaries and generated archives.
