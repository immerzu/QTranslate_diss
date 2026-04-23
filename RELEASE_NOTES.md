# Release Notes

## Current stable portable

- Artifact: `QTranslate_v6.9.0.portable_DE`
- UI locale: German
- Translation direction: auto-detect source to German
- Active service path: Multi (`115`)

## Included changes

- Clipboard and browser links are preserved through the capture path.
- Popup output shows readable anchors while keeping backing URLs hidden in RichEdit text.
- Visible popup links support click fallback, hover hand cursor, stable selection, and copy.
- The active Multi/FreeTranslations path is hardened against URL splitting.
- Technical tokens such as `Common.js`, `6.9.0`, and `QTranslate.6.9.0/Services/Common.js` are protected from post-processing punctuation splitting.

## Known external limitation

- OCR text recognition depends on OCR.space. Without a user OCR API key, that external service may rate-limit requests.

## Release hygiene

- Publish finished portable archives as GitHub Release assets.
- Keep generated `.exe`, `.zip`, `.rar`, logs, and temporary probe directories out of Git.
