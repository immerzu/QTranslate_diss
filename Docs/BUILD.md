# Build Guide

This repository expects a local unpacked QTranslate 6.9.0 working tree in:

- `QTranslate.6.9.0`

Generated binaries and portable packages are not tracked in Git.

## Typical local flow

Apply the capture/link patch:

```powershell
python .\scripts\patch_qtranslate_links.py --with-accessibility-main
```

Apply the popup output/link-formatting patch:

```powershell
python .\scripts\patch_qtranslate_output_links.py
```

Build a fresh clean portable:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_qtranslate_portable_clean.ps1
```

## Output

Typical output directories:

- `release/`
- `Ausgabe/`

The clean portable build is configured to:

- keep `Services` unpacked
- remove packed service `.rar` files from the portable output
- use the German portable profile with auto-detect source to German translation

## Useful helper scripts

- `scripts/run_qtranslate_smoke.ps1`
  Basic local smoke run.
- `scripts/trace_qtranslate_popup_render.py`
  Popup RichEdit tracing and diagnostics.
- `scripts/smoke_qtranslate_link_paths.py`
  Link-path smoke validation.

## Release practice

- Commit source changes only.
- Publish finished portable archives through GitHub Releases.
- Do not commit `.exe`, `.zip`, `.rar`, trace logs, or temporary probe folders.
