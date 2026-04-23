# Accessibility-Pfad in `QTranslate.exe`

Stand: 2026-04-22

## Ziel

Neben dem bereits gepatchten `CF_HTML`-/Clipboard-Pfad sollte auch der MSAA-/Accessibility-Pfad untersucht werden:

- Originalfunktion: `0x404901`
- echter Main-Window-Capture-Call fuer `mode=2`: `0x40531D -> 0x404901`

Zielbild waere auch hier:

- `ЧИТАТЬ (https://...)`

statt nur sichtbarem Linktext.

## Statischer Kernbefund

Die Originalfunktion `0x404901` arbeitet konservativ:

1. `AccessibleObjectFromPoint`
2. `get_accName`
3. nur wenn `accName` leer ist:
   - `get_accValue`

Damit ist statisch klar:

- sobald ein Browser-Link oder aehnliches Element bereits einen sichtbaren Namen liefert,
- geht eine zusaetzliche URL aus `accValue` im Originalpfad verloren.

## Reproduzierbare Probe

Neues Skript:

- `F:\Codex\QTranslate_diss\scripts\probe_qtranslate_accessibility.py`
- `F:\Codex\QTranslate_diss\scripts\inspect_accessible_point.py`

Es:

- erzeugt lokal ein kleines `SysLink`-Host-Fenster
- setzt den Mauszeiger auf den Link
- triggert den echten `HotKeyMainWindow`-Pfad
- liest den sichtbaren QTranslate-Text aus den `RICHEDIT50W`-Feldern

Das zweite Skript inspiziert denselben Punkt direkt ueber `AccessibleObjectFromPoint`, also ohne QTranslate dazwischen.

Zusaetzlich gibt es jetzt noch:

- `F:\Codex\QTranslate_diss\scripts\inspect_edge_link_accessibility.py`
- `F:\Codex\QTranslate_diss\scripts\inspect_edge_accessibility_tree.py`
- `F:\Codex\QTranslate_diss\scripts\inspect_edge_uia.ps1`

Dieses Skript startet eine lokale Testseite in Microsoft Edge und scannt das Browserfenster direkt ueber `AccessibleObjectFromPoint`.
Das neue Tree-Skript traversiert dagegen den MSAA-Baum ab einem per `AccessibleObjectFromWindow` geholten Root und fasst zusaetzlich die Accessibility-Roots der echten Kindfenster von Edge zusammen.
Das UIA-Skript prueft denselben Browserfall ueber `UIAutomationClient`.

## Ergebnis ohne Accessibility-Patch

Mit

- `QTranslate.exe`
- `QTranslate.patched.exe` im Standardmodus

bleibt der Main-Window-Accessibility-Test stabil, aber liefert nur leere RichEdit-Felder:

- Quelltext: `""`
- Zieltext: `""`

Wichtig:

- der funktionierende Clipboard-/HTML-Patch bleibt dabei voll intakt
- der Accessibility-Test beweist aber noch keinen URL-Gewinn

Direktinspektion des lokalen `SysLink`-Hosts ueber `AccessibleObjectFromPoint` ergab:

- `accName = "ЧИТАТЬ"`
- `accValue = NULL` mit `HRESULT = 1`
- `accRole = 10`

Schluss:

- der lokale `SysLink` ist **kein** guter Stellvertreter fuer den eigentlichen Browser-Link-Fall
- er liefert sichtbaren Linktext, aber gerade **keine** URL in `accValue`

## Echter Chromium-Test

Mit Microsoft Edge auf einer lokalen Testseite ergab der Punkt-Scan:

- es wurde ueber viele Punkte hinweg nur
  - `accName = "Chrome Legacy Window"`
  - `accValue = NULL`
  - Rolle `10`
  gefunden
- der sichtbare Linktext `ЧИТАТЬ` wurde ueber `AccessibleObjectFromPoint` am Cursor in diesem Chromium-Fall gerade **nicht direkt** erreicht

Schluss:

- fuer Chromium reicht ein bloesser `AccessibleObjectFromPoint`-Blick auf den Cursorpunkt wahrscheinlich nicht aus
- der Browser-Link steckt entweder tiefer im Accessibility-Baum
- oder Chromium exponiert den relevanten Link hier eher ueber einen anderen Pfad als den simplen MSAA-Punktzugriff

## Echter Chromium-Baumtest

Mit

- `F:\Codex\QTranslate_diss\scripts\inspect_edge_accessibility_tree.py`

ist jetzt zusaetzlich der MSAA-Baum ab einem per `AccessibleObjectFromWindow` geholten Root inspizierbar.

Reproduzierbare Befunde:

- Top-Level `Chrome_WidgetWin_1` mit `OBJID_CLIENT`
  - Root-Name: Seitentitel
  - Rolle `16`
  - Traversierung liefert nur einen sehr kleinen Baum
  - sichtbare Browser-Chrome-Knoten wie `Minimieren` und `Wiederherstellen` tauchen auf
  - der Linktext `ЧИТАТЬ` taucht **nicht** auf
- Top-Level `Chrome_WidgetWin_1` mit `OBJID_WINDOW`
  - Root-Rolle `9`
  - ebenfalls nur Browser-Chrome-nahe Knoten
  - kein Linktext, keine URL
- Kindfenster unter Edge:
  - `Chrome_RenderWidgetHostHWND`
  - `Intermediate D3D Window`
- Besonders wichtig:
  - `Chrome_RenderWidgetHostHWND` ist als Kandidat fuer den eigentlichen Seiteninhalt gefunden
  - dessen `OBJID_CLIENT`-Root hat aber nur
    - `name = NULL`
    - `value = ""`
    - Rolle `15`
  - und in der aktuellen Traversierung **keine** nutzbaren Kinder

Schluss aus dem Baumtest:

- nicht nur der Punktzugriff, sondern auch der offensichtliche MSAA-Baum von Edge/Chromium fuehrt hier nicht sauber bis zum DOM-Link
- der aktuelle `QTranslate`-MSAA-Pfad ueber `AccessibleObjectFromPoint` ist fuer Chromium daher sehr wahrscheinlich strukturell zu schwach, um `name + URL` verlaesslich zu gewinnen
- wenn der Browser-Fall weiter verfolgt wird, ist ein UIA-/IA2-/browser-spezifischer Pfad aussichtsreicher als weiteres generisches MSAA-Nachziehen

## Echter Chromium-UIA-Test

Mit

- `F:\Codex\QTranslate_diss\scripts\inspect_edge_uia.ps1`

ist jetzt derselbe Edge-Fall ueber Windows UI Automation vermessen.

Reproduzierbare Befunde:

- Top-Level `Chrome_WidgetWin_1`
  - liefert ueber UIA viele Browser-Chrome-Elemente
  - z. B. Adressleiste, Caption-Buttons, Toolbar
  - der eigentliche Seitenlink taucht dort nicht als naheliegender Top-Level-Treffer auf
- Kindfenster `Chrome_RenderWidgetHostHWND`
  - liefert ueber UIA einen einzelnen Descendant
  - `ControlType = Hyperlink`
  - `Name = ЧИТАТЬ`
  - `Value = https://browser.example/test-link`
  - `ClassName = probe`
  - `LegacyIAccessiblePattern.Value = NULL`
- zusaetzlicher Punktprobe-Befund:
  - `AutomationElement.FromPoint` auf dem Mittelpunkt dieses Hyperlinks liefert wieder denselben `Hyperlink`
  - dabei bleibt `Value = https://browser.example/test-link` erhalten
- derselbe Befund wurde auch unter
  - `C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`
  reproduziert
  - also in einer 32-Bit-Umgebung, naeher an `QTranslate.exe`

Schluss aus dem UIA-Test:

- fuer Chromium ist der Link inklusive URL **praktisch erreichbar**
- aber nicht ueber den bisherigen generischen MSAA-Pfad
- sondern ueber UIA auf bzw. innerhalb des `Chrome_RenderWidgetHostHWND`
- die URL steckt dabei im Chromium-Test in `ValuePattern`, nicht im Legacy-MSAA-Pattern

Damit ist die Lage jetzt deutlich klarer:

- der Browserfall ist nicht grundsaetzlich unloesbar
- `QTranslate` verliert die URL im Chromium-Fall sehr wahrscheinlich deshalb, weil es beim alten MSAA-Zugriff stehen bleibt
- ein browsernaher UIA-Fallback am Punkt bzw. Render-Widget ist jetzt der erste wirklich belastbare Kandidat fuer einen spaeteren Binairypatch

Die konkrete Entwurfsrichtung ist separat dokumentiert in:

- `F:\Codex\QTranslate_diss\notes\qtranslate_uia_fallback_design.md`

Zusatzlich ist der UIA-Pfad inzwischen auch als nativer 32-Bit-Prototyp verifiziert:

- `F:\Codex\QTranslate_diss\native\inspect_edge_uia_x86.cpp`
- `F:\Codex\QTranslate_diss\scripts\build_inspect_edge_uia_x86.ps1`
- `F:\Codex\QTranslate_diss\tmp_patch\inspect_edge_uia_x86.exe`

Der native Lauf liefert reproduzierbar:

- `link_name=ЧИТАТЬ`
- `link_value=https://browser.example/test-link`
- `point_name=ЧИТАТЬ`
- `point_value=https://browser.example/test-link`

Damit ist der UIA-Weg jetzt nicht nur konzeptionell, sondern auch in einer echten x86-Umgebung nativ bestaetigt.

## Experimenteller Hook

Ein experimenteller Hook wurde als enger Callsite-Patch aufgebaut:

- nicht global auf `0x404901`
- sondern nur am Main-Window-Call
  - `0x40531D`

Die experimentelle Hilfsroutine versucht:

1. `accName` zu lesen
2. zusaetzliche MSAA-Infos wie Link-/Value-Daten zu gewinnen
3. daraus `name (value)` zu bauen

Zusatzlich wurden vier Callsite-Varianten gegeneinander getestet:

- `delegate`
  - Wrapper ruft einfach die originale `0x404901` auf
- `noop`
  - Hook-Punkt selbst, aber ohne echte MSAA-Logik
- `name-only`
  - eigener Clone nur fuer `get_accName`
- `experimental`
  - erweiterter Clone mit weiteren MSAA-Abfragen

## Laufzeitbefund des Experiments

Der experimentelle Accessibility-Hook ist derzeit **nicht produktionsreif**.

Reproduzierbarer Effekt:

- `QTranslate.patched.exe --with-accessibility-main`
- z. B. gebaut als
  - `F:\Codex\QTranslate_diss\QTranslate.6.9.0\QTranslate.accessibility.experimental.exe`
- echter `HotKeyMainWindow`-Pfad
- Prozess beendet sich mit
  - `0xC000001D`

Interpretation:

- zusaetzliche COM-/MSAA-Abfragen jenseits des originalen `get_accName`-Pfads sind auf generischen Objekten instabil
- ein naives Nachziehen von `accValue` ist deshalb deutlich riskanter als der HTML-Clipboard-Patch

Praezisierung nach Variantentests:

- `delegate` bleibt stabil
- `noop` bleibt stabil
- schon `name-only` crasht reproduzierbar
- `experimental` crasht ebenfalls

Damit ist jetzt deutlich enger eingegrenzt:

- der Callsite-Hook selbst ist **nicht** das Problem
- die Instabilitaet sitzt im eigenen Accessibility-Clone
- fuer weitere Arbeit ist ein Wrapper-Ansatz um die originale `0x404901` deutlich aussichtsreicher als ein kompletter Rebuild der Funktion in Shellcode

## Konsequenz

Darum ist der Standard-Patch-Builder jetzt absichtlich konservativ:

- `scripts/patch_qtranslate_links.py`
  - patcht standardmaessig **nur** den stabilen Clipboard-/HTML-Pfad
  - der Accessibility-Hook ist nur noch ueber
    - `--with-accessibility-main`
    - als explizites Experiment aktivierbar

Damit bleibt der verifizierte funktionierende Stand erhalten:

- `QTranslate.patched.exe`
  - HTML-/Clipboard-Link-Erhalt aktiv
  - Accessibility-Experiment standardmaessig aus

## Technische Zwischenbewertung

Die Untersuchung hat trotzdem einen klaren Mehrwert gebracht:

1. Der Verlustpunkt im Accessibility-Pfad ist statisch belegt.
2. Der relevante Main-Window-Callsite ist konkret lokalisiert:
   - `0x40531D`
3. Ein direkter Funktions- oder Callsite-Hook ist machbar.
4. Die naechste Huerde ist jetzt nicht mehr Lokalisierung, sondern sichere COM-/MSAA-Haertung.

## Naechster sinnvoller Schritt

Wenn dieser Pfad weiter verfolgt wird, dann nicht mehr mit blindem `accValue`-Nachziehen, sondern eher mit:

- gezielter Browser-spezifischer Eingrenzung
- einem UIA-Fallback fuer `Chrome_RenderWidgetHostHWND`
- oder robuster Exception-/SEH-Abschirmung um zusaetzliche Aufrufe

## Update 2026-04-23: UIA-Stub stabilisiert

Der experimentelle `uia-point`-Zweig wurde danach noch einmal strukturell ueberarbeitet.

Wichtige technische Fixes:

- kein fruehes `ClearWide` mehr vor dem UIA-Versuch
- GUID-/URL-String-Basis fuer den UIA-Stub getrennt vom normalen Accessibility-Stub behandelt
- COM-Abbau erst nach moeglichem Fallback
- offener Parserfehler im HTML-Stub behoben:
  - `.Lskip_pre_eq_consume` fehlte
  - dadurch enthielt das COFF-Objekt zuvor Relocations und war nicht vollstaendig selbstaufgeloest
- aktueller Assemblerstand ist jetzt wieder sauber:
  - `.text` = `3877` Bytes
  - `RelocationCount = 0`

Laufzeitbefund des stabilisierten UIA-Experiments:

- `QTranslate.accessibility.uia_point.exe` startet im echten `HotKeyMainWindow`-Pfad jetzt stabil
- kein reproduzierbarer `0xC000001D`-/`0xC0000005`-Absturz mehr
- in wiederholten Edge-End-to-End-Laeufen erscheinen echte Browser-Links mit URL direkt im QTranslate-Hauptfenster, z. B.
  - `Mitteilungen (https://x.com/notifications)`
  - Uebersetzung: `Notifications (https://x.com/notifications)`

Wichtige Einschraenkung:

- das aktuelle Edge-Harness trifft den beabsichtigten Probe-Link noch nicht deterministisch
- deshalb war der positive End-to-End-Nachweis zwischenzeitlich ueber reale, aber wechselnde Browser-Links erbracht
- der native Helfer wurde danach so nachgeschärft, dass er den Ziel-Link auch ohne `Chrome_RenderWidgetHostHWND` direkt aus dem UIA-Baum des Top-Level-Fensters findet
- damit ist der Browser-Punkt jetzt deterministisch genug fuer den QTranslate-Hotkey-Test

Aktueller Endzustand:

- `inspect_edge_uia_x86.exe --leave-open` liefert nun fuer den Testlink direkt
  - `link_name=ЧИТАТЬ`
  - `link_value=https://browser.example/test-link`
  - `point_name=ЧИТАТЬ`
  - `point_value=https://browser.example/test-link`
- der QTranslate-End-to-End-Lauf zeigt dadurch den erwarteten Text
  - Source: `ЧИТАТЬ (https://browser.example/test-link)`
  - Translation: `LESEN (https://browser.example/test-link)`

Standardisierung:

- `scripts/patch_qtranslate_links.py --with-accessibility-main` verwendet jetzt ohne weitere Angabe den funktionierenden `uia-point`-Pfad
- der alte experimentelle Default bleibt als explizite Variante erhalten, wird aber nicht mehr automatisch benutzt
- ohne `--output` schreibt der Builder jetzt direkt nach
  - `F:\\Codex\\QTranslate_diss\\QTranslate.6.9.0\\QTranslate.accessibility.default_uia.exe`
- ein Smoke-Test fuer beide stabilen Pfade liegt jetzt in
  - `F:\\Codex\\QTranslate_diss\\scripts\\smoke_qtranslate_link_paths.py`
- der bevorzugte Ein-Kommando-Start ist
  - `powershell -ExecutionPolicy Bypass -File F:\\Codex\\QTranslate_diss\\scripts\\run_qtranslate_smoke.ps1`
- alternativ per Doppelklick:
  - `F:\\Codex\\QTranslate_diss\\run_qtranslate_smoke.cmd`
