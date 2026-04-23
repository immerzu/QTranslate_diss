# Release notes

## Current stable local build

Portable artifact name:

- `QTranslate_v6.9.0.portable_DE`

Default profile:

- UI locale: German
- Translation direction: auto-detect source to German
- Active service: Multi (`115`)

Main changes:

- Preserves selected HTML/clipboard links by keeping the URL in hidden backing text.
- Shows only the readable anchor in the popup while keeping the backing URL available.
- Adds a stable RichEdit click fallback for hidden URL anchors.
- Adds hand cursor behavior over visible link anchors.
- Keeps text selection and copy stable in the subclassed RichEdit control.
- Hardens the active Multi/FreeTranslations path against URL splitting.
- Protects technical tokens such as `Common.js`, `6.9.0`, and `QTranslate.6.9.0/Services/Common.js` from post-processing sentence splitting.

Known external limitation:

- OCR text recognition uses the external OCR.space service. Without a user API key, OCR.space may rate-limit requests.

GitHub release guidance:

- Upload the final portable archive as a Release asset.
- Do not commit generated `.exe`, `.zip`, `.rar`, logs, or temporary probe directories.
