## Hotkey-Dispatch-Map in `QTranslate.exe`

Stand: 2026-04-22

### Zentrale Befunde

- Das versteckte Fenster `QTranslate_ApplicationWindow` benutzt als echten Window-Proc:
  - Laufzeit: `0xEE51FB`
  - statisch: `0x4351FB`
- Der eigentliche Message-Dispatcher des Application-Objekts liegt bei:
  - `0x415E1D`
- `WM_HOTKEY` wird dort explizit erkannt:
  - Vergleich auf `0x312` bei `0x415EA0`
  - Weiterleitung an Handler `0x41779B`

### Wichtige Praezisierung zu `WM_HOTKEY`

Der Handler `0x41779B` benutzt fuer die Hotkey-Erkennung **nicht** `wParam`.

Stattdessen:

- `lParam` wird im echten `WM_HOTKEY`-Format ausgewertet
- also:
  - `LOWORD(lParam)` = Modifier-Flags
  - `HIWORD(lParam)` = Virtual-Key

Beispiel fuer `Ctrl+Alt+T`:

- Modifier = `0x0003`
- VK = `0x0054`
- korrektes `lParam`:
  - `0x00540003`

Der Handler rekonstruiert daraus das interne 16-Bit-Hotkey-Wort:

- `0x0354`
- dezimal `852`

### Hotkey-Slot-Vergleich

Der Vergleichshelper ist:

- `0x417CFE`

Er vergleicht den rekonstruierten Hotkey gegen die Laufzeit-Slots:

- `0x5844CE`
- `0x5844D0`
- `0x5844D2`
- `0x5844D4`
- `0x5844D6`
- `0x5844D8`
- `0x5844DA`
- `0x5844DC`
- `0x5844DE`
- `0x5844E0`
- `0x5844E2`
- `0x5844E4`
- `0x5844E6`
- `0x5844E8`
- `0x5844EA`
- `0x5844EC`
- `0x5844EE`

Zusatz:

- `0x5844CC` aktiviert/deaktiviert die gesamte Hotkey-Registrierung

### Zur Laufzeit gelesene Slot-Werte

Bei laufender `QTranslate.patched.exe` mit temporaer gesetztem Test-Hotkey:

- `0x5844CC = 1`
- `0x5844CE = 33280`
- `0x5844D0 = 593`
- `0x5844D2 = 1617`
- `0x5844D8 = 581`
- `0x5844E6 = 852`
- alle anderen Slots in diesem Test = `0`

Das zeigt:

- der Test-Hotkey `Ctrl+Alt+T` wurde korrekt in die Runtime geladen
- und zwar in Slot `0x5844E6`

### Zuordnung wichtiger Slots zu Tasks

Per Handler `0x41779B` und RTTI/VTable:

- `0x5844CE` -> `TaskShowMainWindow`
- `0x5844D0` -> `TaskShowPopupWindow`
- `0x5844D2` -> `TaskDictionary`
- `0x5844D8` -> `TaskListenText`
- `0x5844DC` -> `TaskConvertTextLayout`
- `0x5844E0` -> `TaskReplaceSelection`
- `0x5844E4` -> `TaskTranslateClipboard`
- `0x5844E6` -> `TaskShowMainWindow(mode=3)`
- `0x5844E8` -> `TaskShowPopupWindow(mode=3)`
- `0x5844EA` -> `TaskDictionary(mode=3)`

### Warum `0x5844E6` fuer uns wichtig ist

`0x5844E6` ist der Slot, in den der Testwert `852` geladen wurde.

Der dazu erzeugte Task ist:

- `TaskShowMainWindow`

mit:

- `mode = 3`

Und genau dieser `mode = 3` fuehrt in `TaskShowMainWindow::...` bei `0x4052E4` zu:

- `0x4052FA` -> Aufruf von `0x43BE7E`

Das ist derselbe Clipboard-Reader, den wir gepatcht haben.

Schluss:

- Wenn `Translate clipboard in main window` sauber durchlaeuft,
- landet der Eingabepfad tatsaechlich bei unserem Patchpunkt `0x43BE7E`

### Task-VTable-Namen

- `0x54F608` -> `TaskTranslateClipboard`
- `0x54F618` -> `TaskListenText`
- `0x54F628` -> `TaskShowMainWindow`
- `0x54EF00` -> `TaskShowPopupWindow`
- `0x54EEC4` -> `TaskDictionary`
- `0x54F648` -> `TaskReplaceSelection`
- `0x54F668` -> `TaskConvertTextLayout`

### Offene Frage

Der direkte synthetische `WM_HOTKEY`-Versuch an `QTranslate_ApplicationWindow` mit korrekt formatiertem `lParam` zeigte in dieser Umgebung noch keine sichtbare Uebernahme in `EditSource` oder `History`.

Das aendert aber nichts am strukturellen Befund:

- Der Hotkey wird im Application-Dispatcher erkannt.
- Der Slot `0x5844E6` ist korrekt geladen.
- Der daraus erzeugte Task fuehrt bei `mode = 3` direkt in den gepatchten Clipboard-Reader `0x43BE7E`.
