# End-to-End-Verifikation des Link-Patches

Stand: 2026-04-22

## Kurzfazit

Der Patch in `QTranslate.patched.exe` funktioniert im echten Main-Window-Clipboard-Pfad.

Bei vorbereitetem Clipboard mit:

- `CF_UNICODETEXT = "QTLINK_xxx ЧИТАТЬ QTLINK_xxx"`
- `HTML Format` mit
  - `<a href="https://example.com/test-link">ЧИТАТЬ</a>`

zeigt die gepatchte EXE im sichtbaren Quelltextfeld:

- `QTLINK_xxx ЧИТАТЬ QTLINK_xxx (https://example.com/test-link)`

Das Original zeigt unter denselben Bedingungen nur:

- `QTLINK_xxx ЧИТАТЬ QTLINK_xxx`

Damit ist praktisch bestaetigt:

- der Verlust der URL passiert vor der Uebersetzung im Clipboard-/HTML-Capture
- der Patch am Reader `0x43BE7E` behebt genau diesen Verlustpunkt

## Testmethode

Verwendetes Harness:

- `F:\Codex\QTranslate_diss\scripts\probe_qtranslate_capture.py`

Wichtige Beobachtung:

- ein direkt gepostetes synthetisches `WM_HOTKEY` ist in dieser Umgebung nicht der verlaesslichste Trigger
- robust funktionierte dagegen ein realer Hotkey-Trigger ueber
  - `WScript.Shell.SendKeys("^%t")`

Der erfolgreiche Pfad war:

1. `Options.json` temporaer auf Hotkeys aktiv und `HotKeyTranslateClipboardInMainWindow = 852`
2. Clipboard mit Testdaten vorbereiten
3. `QTranslate.exe` bzw. `QTranslate.patched.exe` starten
4. realen Hotkey `Ctrl+Alt+T` senden
5. sichtbares Hauptfenster oeffnen lassen
6. Quell-/Zieltext direkt aus den sichtbaren `RICHEDIT50W`-Controls per `WM_GETTEXT` lesen

## Vergleich Original vs Patch

### Original EXE + Unicode-only

Quellfeld:

- `QTLINK_... ЧИТАТЬ QTLINK_...`

Zielfeld:

- `[FreeTranslations]`
- `QTLINK_... READ QTLINK_...`

### Original EXE + HTML

Quellfeld:

- `QTLINK_... ЧИТАТЬ QTLINK_...`

Zielfeld:

- `[FreeTranslations]`
- `QTLINK_... READ QTLINK_...`

Befund:

- `HTML Format` bringt im Original keine sichtbare URL ins Quellfeld

### Gepatchte EXE + Unicode-only

Quellfeld:

- `QTLINK_... ЧИТАТЬ QTLINK_...`

Zielfeld:

- `[FreeTranslations]`
- `QTLINK_... READ QTLINK_...`

Befund:

- Fallback auf `CF_UNICODETEXT` bleibt unveraendert

### Gepatchte EXE + HTML

Quellfeld:

- `QTLINK_... ЧИТАТЬ QTLINK_... (https://example.com/test-link)`

Zielfeld:

- `[FreeTranslations]`
- `QTLINK_... READ QTLINK_... (https://example.com/test-link)`

Befund:

- nur diese Kombination fuegt die URL an
- die angehaengte URL ueberlebt auch die weitere Uebergabe in das sichtbare Ziel-/Uebersetzungsfeld

## Wichtig fuer die Interpretation

`Options.json` und `History.json` waren in diesem Automationslauf kein guter Wahrheitsanker:

- `Contents.EditSource` blieb auf der gesetzten Baseline
- `History.json` bekam keinen passenden Testeintrag

Das spricht dafuer, dass bei diesem halbautomatisierten Schliessen:

- entweder kein normaler Persistenzpfad mehr ausgefuehrt wurde
- oder dieser Pfad spaeter/anders laeuft als die sichtbare UI-Befuellung

Fuer die technische Kernfrage ist das aber ausreichend, denn die sichtbaren `RICHEDIT50W`-Controls belegen direkt:

- welches Quelltext-Payload im Main Window ankommt
- und dass der Patch genau dort greift

## Schlussfolgerung fuer die weitere Arbeit

Der aktuelle Patchstand ist funktional richtig:

- Original verliert `href`
- Patch erhaelt `href` als angehaengtes ` (URL)`
- Unicode-only bleibt unveraendert

Damit verschiebt sich die Aufgabe von der Ursachenanalyse zur Produktisierung:

- Patch robust dokumentieren
- ggf. HTML-Parser noch auf komplexere Linkfaelle absichern
- optional weitere Pfade pruefen, etwa Popup-Window oder Browser-Selection ueber Accessibility

## Relevante Dateien

- `F:\Codex\QTranslate_diss\QTranslate.6.9.0\QTranslate.patched.exe`
- `F:\Codex\QTranslate_diss\asm\read_html_or_unicode_clipboard.s`
- `F:\Codex\QTranslate_diss\scripts\probe_qtranslate_capture.py`
