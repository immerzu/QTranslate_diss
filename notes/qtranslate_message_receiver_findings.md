## Message-/Hotkey-Empfaenger: Befunde vom 2026-04-22

### Versteckte Fenster der laufenden `QTranslate.patched.exe`

Bei einem real gestarteten Prozess wurden stabil diese relevanten Fenster gefunden:

- `QTranslate_ApplicationWindow`
  - verstecktes Top-Level-Fenster
- `QTranslateClipboardWindowClass`
  - Message-Only-Fenster
- daneben nur Hilfsfenster wie `GDI+ Hook Window Class`, `IME`, `OleMainThreadWndClass`

### `QTranslateClipboardWindowClass`

- Klassenname-String liegt bei `0x5534fc`
- Registriert bei `0x43ebea`
- Erzeugt bei `0x43ec06`
- Window-Proc ist `0x43eb6d`

Der Proc bei `0x43eb6d` behandelt sehr wahrscheinlich nur diese Messages:

- `0x0002` = `WM_DESTROY`
- `0x0305`
- `0x0306`
- `0x0308` = `WM_DRAWCLIPBOARD`
- `0x030D` = `WM_CHANGECBCHAIN`

Schluss:

- `QTranslateClipboardWindowClass` ist Clipboard-Chain-/Clipboard-Infra
- nicht der eigentliche Hotkey-Empfaenger

### Hotkey-Registrierung

Die echte `RegisterHotKey`-Import-Callsite liegt im Helper `0x405a17`.

Wichtige Beobachtung:

- QTranslate benutzt als `id` fuer `RegisterHotKey` nicht kleine Werte wie `0..16`
- stattdessen wird das komplette 16-Bit-Hotkey-Wort selbst als `id` registriert
- der Helper liest:
  - `vk` aus dem Low-Byte
  - `modifiers` aus dem High-Byte-Nibble
  - `id` = komplettes Hotkey-Wort

Der zentrale Registrierungsblock liegt bei:

- `0x418bc9` bis `0x418cb9`

Er registriert 17 globale Hotkeys aus dem Speicherbereich:

- `0x5844ce` bis `0x5844ee`

Das passt zur bekannten Liste von 17 QTranslate-Aktionen.

### Direktversuche mit `WM_HOTKEY`

Getestet wurden direkte `WM_HOTKEY`-Zustellungen an:

- `QTranslate_ApplicationWindow`
- `QTranslateClipboardWindowClass`

Zuerst mit falschen Test-IDs `0..23`, dann mit der korrekten echten Hotkey-ID:

- `0x354` fuer `Ctrl+Alt+T`

Zusammen mit passendem `lParam`:

- `mods = 0x0003`
- `vk = 0x54`
- `lParam = 0x00030054`

Ergebnis:

- weder `PostMessageW` noch `SendMessageW` loesten eine Uebernahme des Test-Clipboard-Inhalts in `EditSource` oder `History` aus

### Arbeitsfolgerung

Der eigentliche Hotkey-Empfangspfad ist damit noch nicht komplett getroffen.

Am plausibelsten sind jetzt nur noch diese Varianten:

1. Die Hotkeys werden threadgebunden mit `hWnd = NULL` registriert und an die GUI-Thread-Queue geliefert.
2. Es gibt einen weiteren internen/ATL-bezogenen Empfaenger, der bei der einfachen Fensterenumeration nicht als eigener QTranslate-Klassenname sichtbar wurde.
3. `QTranslate_ApplicationWindow` nimmt `WM_HOTKEY` zwar an, erwartet aber einen weiteren internen Zustandspfad vor der eigentlichen Aktion.

### Wichtig fuer das Link-Problem

Diese Befunde aendern nichts an der bereits isolierten Kernursache:

- der URL-Verlust passiert weiterhin vor der Uebersetzung im Eingabepfad
- konkret im Plaintext-Import ueber `0x43be7e`
- der neue Patch an `QTranslate.patched.exe` bleibt deshalb der richtige technische Ansatz fuer die Link-Erhaltung
