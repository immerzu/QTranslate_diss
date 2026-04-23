## Laufzeit-Smoketest vom 2026-04-22

### Verifiziert

- `QTranslate.patched.exe` startet sauber und bleibt stabil als Prozess aktiv.
- Die gepatchte Datei liegt unter:
  - `F:\Codex\QTranslate_diss\QTranslate.6.9.0\QTranslate.patched.exe`
- Der eingesetzte Test-Clipboard konnte erfolgreich gleichzeitig bereitstellen:
  - `UnicodeText`
  - `HTML Format`
- Das Test-HTML enthielt bewusst:
  - sichtbaren Text: `ЧИТАТЬ_LINKTEST3`
  - Link: `https://example.com/qtranslate-linktest-20260422-c`

### Nicht erfolgreich automatisierbar

- Ein automatischer End-to-End-Lauf ueber den globalen Clipboard-Hotkey hat in dieser Umgebung weder beim Original noch beim Patch einen neuen Verlaufseintrag erzeugt.
- Dadurch konnte der komplette GUI-Pfad `Hotkey -> TaskTranslateClipboard -> UI/History` noch nicht abschliessend bestaetigt werden.

### Interpretation

- Der Binär-Patch selbst ist statisch korrekt eingebaut und die gepatchte EXE startet.
- Die ausbleibende End-to-End-Bestaetigung spricht im Moment eher fuer ein Automatisierungsproblem beim Triggern der versteckten Tray-/Hotkey-Logik als fuer einen direkten Absturz des Patches.
- Der eigentliche Eingriffspunkt bleibt unveraendert plausibel:
  - `0x43BE7E` wurde erfolgreich durch den neuen Reader ersetzt.
  - Dieser Reader versucht zuerst `HTML Format` und faellt dann auf `CF_UNICODETEXT` zurueck.

### Empfohlener Realtest

1. `QTranslate.patched.exe` manuell starten.
2. Im Browser einen Linktext wie `ЧИТАТЬ` markieren, dessen `href` bekannt ist.
3. Den Clipboard-/Popup-Pfad ausloesen, der in der Praxis wirklich genutzt wird.
4. Pruefen, ob QTranslate als Quelltext jetzt etwa `ЧИТАТЬ (https://...)` uebernimmt.
5. Falls nicht, gezielt beobachten, ob der reale Browserpfad ueber Accessibility statt ueber Clipboard laeuft.
