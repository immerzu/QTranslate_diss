# UIA-Fallback-Design fuer `QTranslate.exe`

Stand: 2026-04-22

## Zweck

Diese Notiz beschreibt den naechsten realistischen Accessibility-Fallback fuer Browser-Links in `QTranslate.exe`, nachdem der generische MSAA-Pfad fuer Chromium als zu schwach eingegrenzt wurde.

Zielbild:

- `ЧИТАТЬ (https://...)`

auch dann, wenn der Browser-Link nicht ueber den bisherigen `AccessibleObjectFromPoint`-/`accName`-/`accValue`-Pfad aufloesbar ist.

## Relevanter Befund

Der bisherige Chromium-Browserfall ist jetzt in drei Stufen vermessen:

1. generischer MSAA-Punktzugriff
   - liefert im Chromium-Fall nur `Chrome Legacy Window`
   - kein direkter Linktext
   - keine URL
2. generischer MSAA-Baum
   - erreicht nur Browser-Chrome-nahe Knoten
   - nicht den eigentlichen DOM-Link
3. UIA auf Chromium
   - findet im `Chrome_RenderWidgetHostHWND` einen echten `Hyperlink`
   - `Name = ЧИТАТЬ`
   - `Value = https://browser.example/test-link`
   - `AutomationElement.FromPoint` auf dem Mittelpunkt des Links liefert denselben `Hyperlink` zurueck

Schluss:

- fuer Chromium ist der Link samt URL nicht generell verborgen
- aber der alte MSAA-Pfad in `QTranslate.exe` sieht ihn nicht
- ein UIA-Punkt-Fallback ist der erste wirklich belastbare Kandidat fuer einen Binary-Patch

## x86-Verifikation

Wichtig fuer die Realisierbarkeit:

- `QTranslate.exe` ist 32-Bit
- der UIA-Nachweis wurde nicht nur unter normaler PowerShell, sondern auch unter
  - `C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`
  reproduziert

Damit ist belegt:

- der UIA-Pfad funktioniert auch in einer 32-Bit-Prozessumgebung
- es handelt sich also nicht nur um einen 64-Bit-Sonderfall des Diagnosewerkzeugs

## Bereits vorhandene Infrastruktur in `QTranslate.exe`

`QTranslate.exe` importiert bereits aus `ole32.dll`:

- `CoInitializeEx`
- `CoCreateInstance`
- `CoUninitialize`
- `CoTaskMemAlloc`
- `CoTaskMemFree`

Zusatzbefund:

- `UIAutomationCore.dll` ist nicht als statischer Import vorhanden
- das ist fuer einen COM-basierten UIA-Fallback aber **nicht zwingend** ein Blocker
- `CoCreateInstance(CLSID_CUIAutomation, ...)` kann die UIA-Implementierung zur Laufzeit bereitstellen

Damit ist ein UIA-Fallback grundsaetzlich moeglich, ohne die bestehende Importtabelle von `QTranslate.exe` erweitern zu muessen.

## Wahrscheinlich einfachster Laufzeitpfad

Der naheliegendste Patch waere **nicht**:

- Browserfenster suchen
- `Chrome_RenderWidgetHostHWND` enumerieren
- dort einen komplizierten UIA-Baum traversieren

sondern deutlich kleiner:

1. Cursorpunkt bestimmen
   - `GetCursorPos` ist bereits vorhanden
2. UIA initialisieren
   - `CoInitializeEx`
3. `IUIAutomation` erzeugen
   - `CoCreateInstance(CLSID_CUIAutomation, IID_IUIAutomation, ...)`
4. `ElementFromPoint`
   - UIA-Punktzugriff direkt auf den Cursorpunkt
5. `CurrentControlType`
   - erwarteter Wert fuer Link: `UIA_HyperlinkControlTypeId = 50005`
6. `CurrentName`
   - sichtbarer Linktext
7. `ValuePattern`
   - URL aus `CurrentValue`
8. bei Erfolg:
   - `name (value)` bauen
9. sonst:
   - beim bisherigen Verhalten bleiben

Wichtig:

- die PowerShell-Probe zeigt bereits, dass `FromPoint` am Linkzentrum denselben Hyperlink samt URL liefert
- fuer den eigentlichen QTranslate-Hotkeypfad passt ein UIA-Punkt-Fallback damit deutlich besser als ein render-widget-basierter Baumlauf

## Empfohlene Integrationsstrategie

Der UIA-Pfad sollte **nicht** den stabilen HTML-/Clipboard-Patch ersetzen.

Sinnvolle Reihenfolge im Binary:

1. vorhandenen stabilen `CF_HTML`-/Clipboard-Pfad unveraendert lassen
2. beim Main-Window-Accessibility-Capture den alten Pfad nicht blind ersetzen
3. stattdessen:
   - zuerst originalen MSAA-Weg weiterverwenden
   - nur wenn dort kein brauchbares `name (url)` entsteht:
     - UIA-Fallback probieren

So bleibt erhalten:

- bestehende Stabilitaet
- keine Regression fuer Nicht-Browser-Faelle
- Browser-spezifische Verbesserung nur dort, wo MSAA sichtbar zu kurz greift

## Technische Minimalanforderungen im Shellcode

Ein spaeterer UIA-Stub muesste mindestens mit folgenden COM-Objekten und Properties arbeiten:

- `CLSID_CUIAutomation`
- `IID_IUIAutomation`
- `IUIAutomation::ElementFromPoint`
- `IUIAutomationElement::get_CurrentControlType`
- `IUIAutomationElement::get_CurrentName`
- `IUIAutomationElement::GetCurrentPattern` oder `GetCurrentPatternAs`
- `IUIAutomationValuePattern::get_CurrentValue`

Zusatzdaten:

- `UIA_HyperlinkControlTypeId = 50005`
- `UIA_ValuePatternId = 10002`

Noetig ist ausserdem:

- sauberes `BSTR`-Freigeben
- COM-`Release`
- defensiver Fehlerpfad bei `HRESULT < 0`

## Erwartete Hauptrisiken

Die groessten Risiken sind nicht mehr fachlich, sondern implementatorisch:

- COM-vtable-Aufrufe im Shellcode sind fehleranfaellig
- UIA-Interfaces sind deutlich umfangreicher als der bisherige MSAA-Pfad
- falsche `stdcall`-/COM-Signaturen fuehren schnell zu harten Abstuerzen
- `CoInitializeEx`-Semantik im bestehenden Thread muss sauber behandelt werden
- Punktobjekt unter dem Cursor kann je nach Browser-Zustand schwanken

Deshalb waere die sinnvolle Reihenfolge:

1. nativen Minimal-Prototyp ausserhalb von `QTranslate.exe` bauen
2. denselben UIA-Punktpfad auf x86 stabil verifizieren
3. erst danach den kleinsten moeglichen Binary-Stub planen

## Kurzfazit

Der Chromium-Browserfall ist jetzt erstmals nicht nur analysiert, sondern in eine konkrete Patch-Richtung uebersetzt:

- MSAA erklaert den Verlust
- UIA zeigt den Link mit URL wirklich an
- x86 ist verifiziert
- `QTranslate.exe` hat bereits die entscheidenden `ole32`-Imports

Der naechste echte Implementierungsschritt ist daher kein weiteres MSAA-Experiment, sondern ein nativer x86-UIA-Minimalprototyp fuer:

- `GetCursorPos`
- `CoCreateInstance(CUIAutomation)`
- `ElementFromPoint`
- `Hyperlink + ValuePattern`

## Nativer x86-Prototyp

Dieser Schritt ist jetzt umgesetzt:

- Quelle:
  - `F:\Codex\QTranslate_diss\native\inspect_edge_uia_x86.cpp`
- Build-Wrapper:
  - `F:\Codex\QTranslate_diss\scripts\build_inspect_edge_uia_x86.ps1`
- erzeugte Test-EXE:
  - `F:\Codex\QTranslate_diss\tmp_patch\inspect_edge_uia_x86.exe`

Der Prototyp ist bewusst klein gehalten und macht genau den relevanten Laufzeitpfad:

1. lokale Edge-Testseite starten
2. Top-Level-Fenster finden
3. `Chrome_RenderWidgetHostHWND` finden
4. `CoInitializeEx`
5. `CoCreateInstance(CLSID_CUIAutomation, ...)`
6. `ElementFromHandle` auf Top-Level und Render-Widget
7. `FindAll(TreeScope_Descendants, TrueCondition)` auf dem Render-Widget
8. `Hyperlink` mit Name `ЧИТАТЬ` finden
9. `ValuePattern` lesen
10. `ElementFromPoint` auf dem Mittelpunkt des Links pruefen

Reproduzierbarer Laufzeitbefund der nativen x86-EXE:

- `coinit_hr=0x00000000`
- `top_descendants=66`
- `render_descendants=1`
- `link_name=ЧИТАТЬ`
- `link_value=https://browser.example/test-link`
- `point_name=ЧИТАТЬ`
- `point_value=https://browser.example/test-link`

Das ist der bisher staerkste technische Nachweis in diesem Strang:

- nicht nur PowerShell/.NET
- nicht nur 64-Bit
- sondern ein nativer 32-Bit-UIA-Client liefert den Browser-Link samt URL stabil

## Konsequenz fuer einen spaeteren Binary-Patch

Die wesentliche Unsicherheit hat sich damit verschoben:

- **fachlich** ist der Chromium-Fall jetzt ausreichend geklaert
- die Restarbeit ist primaer **Binary-Engineering**

Was jetzt noch offen bleibt:

- wie klein ein UIA-Stub in der vorhandenen Code-Cave realistisch gehalten werden kann
- ob `ElementFromPoint` direkt im QTranslate-Hotkeypfad schon reicht oder ob ein Render-Widget-Fallback noetig wird
- wie COM-/BSTR-/Release-Pfade ohne Instabilitaet in den Shellcode gebracht werden

## Compiler-abgeleiteter x86-Call-Skeleton

Fuer den wirklich patchnahen Teil gibt es jetzt auch einen isolierten Minimalpfad:

- Quelle:
  - `F:\Codex\QTranslate_diss\native\uia_point_pipeline.cpp`
- Build:
  - `F:\Codex\QTranslate_diss\scripts\build_uia_point_pipeline_asm.ps1`
- Disassembly:
  - `F:\Codex\QTranslate_diss\tmp_patch\uia_point_pipeline_x86.asm`

Diese kleine Funktion macht nur den eigentlichen UIA-Punktlauf:

1. `IUIAutomation::ElementFromPoint`
2. `IUIAutomationElement::get_CurrentControlType`
3. `IUIAutomationElement::get_CurrentName`
4. `IUIAutomationElement::GetCurrentPatternAs(UIA_ValuePatternId, IID_IUIAutomationValuePattern, ...)`
5. `IUIAutomationValuePattern::get_CurrentValue`
6. `Release`

Aus der x86-Disassembly des kompilierten Minimalpfads ergeben sich jetzt die entscheidenden VTable-Offets:

- `IUIAutomation::ElementFromPoint`
  - `vtbl + 0x1C`
- `IUIAutomationElement::GetCurrentPatternAs`
  - `vtbl + 0x38`
- `IUIAutomationElement::get_CurrentControlType`
  - `vtbl + 0x54`
- `IUIAutomationElement::get_CurrentName`
  - `vtbl + 0x5C`
- `IUnknown::Release`
  - `vtbl + 0x08`
- `IUIAutomationValuePattern::get_CurrentValue`
  - `vtbl + 0x10`

Zusaetzliche Konstante aus demselben Minimalpfad:

- `UIA_ValuePatternId = 0x2712` dezimal `10002`

Groessenbefund des isolierten Minimalpfads:

- `.text`-Laenge des kompilierten COFF-Objekts:
  - `303` Bytes
- zusaetzliche `.rdata` fuer `IID_IUIAutomationValuePattern`:
  - `16` Bytes
- Relocations im `.text` dieses Minimalpfads:
  - `1`
  - genau fuer den GUID-Zeiger auf `IID_IUIAutomationValuePattern`

Das ist wichtig:

- der nackte UIA-Punktpfad ist nicht winzig
- aber auch nicht so gross, dass er prinzipiell ausscheidet
- grob gesprochen liegt der Minimalpfad in einer Groessenordnung von rund `319` Bytes plus Integrations-Glue

Wichtig fuer spaeteren Shellcode:

- der `GetCurrentPatternAs`-Aufruf braucht neben `patternId`
  - auch einen Zeiger auf `IID_IUIAutomationValuePattern`
- in der Disassembly erscheint dieser GUID-Parameter als Relocation-Stelle
- das heisst:
  - fuer einen Binary-Stub muessen die benoetigten GUIDs entweder
    - im Cave-Datenbereich mitgefuehrt
    - oder anderweitig adressierbar gemacht werden

Damit ist der UIA-Pfad nicht mehr nur logisch, sondern auch in den konkreten x86-COM-Aufrufoffets greifbar.
