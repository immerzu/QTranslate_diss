# QTranslate task queue / worker pipeline

Stand: 2026-04-22

## Wichtigste Aussage

Der Weg nach dem Hotkey laeuft nicht direkt in die UI, sondern ueber eine dedizierte Task-Queue mit Worker-Thread.

Fuer unseren Fall ist damit nun statisch belegt:

1. `WM_HOTKEY` trifft im Application-Dispatcher ein
2. dort wird ein Task in die Queue bei `app + 0x13b8` eingestellt
3. der Worker-Thread fuehrt zuerst die Capture-Stufe aus
4. danach marshalt QTranslate in die UI ueber proprietaere Fenster-Messages

Damit ist der Patchpunkt `0x43BE7E` nicht nur indirekt, sondern in der echten Task-Pipeline verankert.

## ThreadTaskQueue

- Konstruktor: `0x441444`
- Destruktor: `0x44149E`
- VTable: `0x55DBD0`
- RTTI:
  - `.?AVThreadTaskQueue@base@@`

Der Queue-Konstruktor initialisiert:

- internen Event-Handle bei `+0x44`
- internen Worker-Thread-/Runnable-Unterbau ab `+0x04`
- diverse Queue-/Statusfelder ab `+0x14`

## Queue enqueue

- Enqueue: `0x43AC5C`

Verhalten:

- wenn Queue aktiv ist und gerade kein Pending-Task gesetzt ist:
  - eingehenden Task nach `+0x0C`
  - `SetEvent(queue+0x10)`
  - Rueckgabe `true`
- sonst:
  - den uebergebenen Task sofort `Release(1)`-artig freigeben
  - Rueckgabe `false`

Caller in der Application-Logik:

- `0x41600A`
- `0x417CD7`
- `0x418340`
- `0x41838D`
- `0x4183A7`
- `0x418408`
- `0x4184B0`
- `0x418555`

## Worker-Thread

- Thread entry / worker main: `0x43ACB4`
- Thread start helper: `0x43AEFF`

`0x43AEFF`:

- `CreateThread(...)`
- speichert Thread-Handle in Queue-Unterobjekt
- wartet auf initiales Signal mit `WaitForSingleObject`

`0x43ACB4`:

- `CoInitializeEx(NULL, 2)`
- ruft Initialisierungslogik `0x43AD6B`
- geht dann in eine Event-/Message-Schleife

## Worker-Schleife

In `0x43ACB4` wird fuer den aktuellen Task bei `queue+0x0C` folgende Sequenz gefahren:

1. `task->vfunc[1](&queue+0x14)`  
   statisch bei `0x43AD0C`
2. `SendMessageW(hwnd, 0x80A5, 3, task)`  
   ueber Helper `0x43AE2F`
3. `task->vfunc[2](&queue+0x14)`  
   statisch bei `0x43AD1F`
4. `SendMessageW(hwnd, 0x80A5, 4, task)`  
   wieder ueber `0x43AE2F`
5. `task` freigeben und `queue+0x0C = 0`

Zusatzsignale:

- `PostMessageW(hwnd, 0x80A5, 2, 1/0)` ueber `0x43AE5A`
- `PostMessageW(hwnd, 0x80A5, 5, 0)` einmalig beim Idle/Shutdown-Pfad

## App-Window Message `0x80A5`

Der Application-Dispatcher behandelt `0x80A5` bei:

- Vergleich: `0x415E6A`
- Handler: `0x41744F`

Der Handler differenziert die `wParam`-Phasen:

- `0`
- `1`
- `2`
- `3`
- `4`
- `5`

Wichtig fuer uns:

- `3` und `4` sind die synchronen Worker-Phasen um die eigentliche Task-Ausfuehrung herum

## TaskShowMainWindow

VTable:

- `0x54F628`
- RTTI:
  - `.?AVTaskShowMainWindow@tasks@windows@@`

Wesentliche virtuelle Methoden:

- `0x4054FA` / `0x405528`: Dtor-Varianten
- `0x4052E4`: Capture-Stufe
- `0x40533D`: UI-/Dispatch-Stufe

### Capture-Stufe `0x4052E4`

`mode` liegt in `this + 0x08`:

- `1` -> bestehender Window-Content
- `2` -> Accessibility-Pfad `0x404901`
- `3` -> Clipboard-Pfad `0x4052FA -> 0x43BE7E`

Damit ist fuer `TaskShowMainWindow(mode=3)` explizit belegt:

- erst hier wird der eigentliche Quelltext eingesammelt
- und genau hier landet unser Link-Patch

### Dispatch-Stufe `0x40533D`

Diese zweite Stufe macht keine erneute Clipboard-Erfassung.

Stattdessen:

- prueft sie, ob im Task bereits Text vorhanden ist
- iteriert ueber Ziel-/Service-Zustaende
- sendet proprietaere Fenster-Messages wie
  - `0x814F`
  - `0x816D`
  - `0x8172`

Die Zustellung laeuft ueber:

- `0x4048B7`
- `0x4054A2`

Wichtiger Befund:

- In dieser Stufe ist kein offensichtlicher Code sichtbar, der URLs gezielt entfernt oder aus dem String wieder herausparst.
- Der eigentliche Verlustpunkt fuer Browser-Links bleibt damit vor der UI-Dispatch-Stufe am wahrscheinlichsten im Capture-Pfad.

## Laufzeittest mit vorbereitetem CF_HTML

Kontrollierter Test mit:

- `QTranslate.patched.exe`
- vorbereitetem Clipboard:
  - `CF_UNICODETEXT = "ЧИТАТЬ"`
  - `HTML Format` mit
    - `<a href="https://example.com/test-link">ЧИТАТЬ</a>`
- synthetischem `WM_HOTKEY` an `QTranslate_ApplicationWindow`
  - `lParam = 0x00540003` fuer `Ctrl+Alt+T`

Befunde:

- patched EXE startet im Idle stabil
- das versteckte `QTranslate_ApplicationWindow` ist vorhanden
- das Clipboard laesst sich mit `CF_UNICODETEXT + HTML Format` vorbereiten
- nach dem synthetischen Hotkey war der Prozess in einem Lauf nicht mehr vorhanden
- ein separater Kontrolllauf ohne Trigger blieb stabil und beendete sich nur beim expliziten Schliessen

Interpretation:

- Der Trigger geht tiefer in die echte Task-Pipeline als fruehere Blindtests
- die reine Idle-Stabilitaet des gepatchten EXE ist gegeben
- die synthetische Hotkey-Automation bleibt aber noch kein sauberer End-to-End-Nachweis fuer den finalen UI-Text

## Konsequenz fuer die Link-Untersuchung

Die derzeit staerkste technische Schlussfolgerung ist:

- Der relevante Verlustpunkt liegt weiterhin im Capture-Teil vor der Service-Uebergabe.
- `TaskShowMainWindow(mode=3)` benutzt fuer diesen Teil direkt `0x43BE7E`.
- Nach erfolgreicher Capture-Stufe ist in der spaeteren UI-Dispatch-Stufe bislang kein offensichtlicher URL-Stripping-Code sichtbar.
