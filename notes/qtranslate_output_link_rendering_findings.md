# QTranslate Output Link Rendering Findings

Stand: 2026-04-23

## Kurzbefund

Die bisherigen `QTranslate.exe`-Binary-Patches sind Eingabe-/Capture-Patches.

- `QTranslate.patched.exe`
  - patcht den Clipboard-/HTML-Pfad
  - Ziel: URL aus Browser-/Clipboard-HTML in den Quelltext retten
- `QTranslate.accessibility.default_uia.exe`
  - patcht zusaetzlich den Browser/UIA-Pfad
  - Ziel: Linktext plus URL aus echter Browser-Selektion gewinnen

Diese Patches erzeugen noch keine versteckten klickbaren Links im uebersetzten Ergebnis.

## Sichtbarer Fehler

Wenn `Service.js` HTML wie

```html
<a href="https://example.test">READ</a>
```

zurueckgibt, rendert QTranslate das im Popup/Hauptfenster nicht als Link.
Es erscheint literal als Text:

```text
<a href="https://example.test">READ</a>
```

Dasselbe gilt fuer `<br/>`.

Damit ist `Service.js` allein nicht der richtige Ort fuer das Ziel
"blaues Wort, URL im Hintergrund".

## RichEdit-Probe

Neuer Test:

```text
F:\Codex\QTranslate_diss\scripts\probe_qtranslate_output_richedit_link.py
```

Der Test startet die portable Release-EXE, oeffnet per Hotkey das echte
QTranslate-Fenster, findet die sichtbaren `RICHEDIT50W`-Felder und setzt
Testtext in das Ergebnisfeld.

Ergebnis:

- `WM_SETTEXT` funktioniert
- das Ergebnisfeld zeigt Plaintext korrekt
- `<a>READ</a>` wird nicht als Link geparst
- `<a href="...">READ</a>` wird nicht als Link geparst
- externer Versuch mit `EM_SETCHARFORMAT/CFE_LINK` auf `READ` wird vom
  Ziel-Control nicht akzeptiert

Relevanter Probelauf:

```json
{
  "plain_text": "FreeTranslations nutzt translate-pa.googleapis.com READ und bleibt sauber.",
  "link_range": [51, 55],
  "after_text": "FreeTranslations nutzt translate-pa.googleapis.com READ und bleibt sauber.",
  "format_probe": {
    "setcharformat_return": 0,
    "settextmode_rich_return": 0,
    "has_cfe_link": false
  }
}
```

Interpretation:

- Von aussen kann das QTranslate-Ergebnisfeld nicht einfach nachtraeglich
  in einen klickbaren Link umformatiert werden.
- Falls es intern doch moeglich ist, braucht es einen echten Patch im
  QTranslate-Prozess, nicht nur Service-JavaScript.

## Statische Ausgabe-Spuren

`QTranslate.exe` importiert:

- `USER32.dll!SetWindowTextW`
- `USER32.dll!SendMessageW`
- `SHELL32.dll!ShellExecuteW`

Es gibt 13 direkte `SetWindowTextW`-Callsites.

Einige davon sehen wie RichEdit-Setzer aus, weil sie nach `SetWindowTextW`
direkt `SendMessageW(..., EM_SETSEL, ...)` ausfuehren:

- `0x40AA63`
- `0x41203B`
- `0x412716`
- `0x4252EC`

Andere Callsites mit `<a>...</a>`-Formatstrings arbeiten wahrscheinlich mit
SysLink-/UI-Beschriftungen, nicht mit dem Uebersetzungsergebnis:

- `0x42F141`
- `0x42F27E`

Die im Binary gefundenen Strings wie `<a>%s</a>` beweisen deshalb nicht, dass
das Translation-RichEdit HTML oder Links rendert.

## SetWindowTextW-Callsite-Probe

Um den Ergebnis-Schreibpunkt weiter einzugrenzen, wurden temporaere EXE-
Varianten gebaut. In jeder Variante wurde genau ein direkter
`SetWindowTextW`-Call ersetzt durch:

```asm
add esp, 8
nop
nop
nop
```

Damit wird der jeweilige Call uebersprungen, ohne den Stack zu zerstoeren.

Getestete Callsites:

```text
0x401D60
0x402DD3
0x40AA63
0x40AE8B
0x41203B
0x412716
0x4252EC
0x42BCEB
0x42F141
0x42F27E
0x42FB13
0x45206E
0x4520CE
```

Ergebnis:

- Bei `0x401D60` wird statt der FreeTranslations-Ausgabe eine
  Spracherkennungs-/Auswahlmeldung sichtbar.
- Bei `0x42F141`, `0x42FB13`, `0x45206E`, `0x4520CE` entsteht kein sichtbares
  Hauptfenster mit zwei `RICHEDIT50W`-Feldern.
- Bei den anderen direkten `SetWindowTextW`-Callsites bleibt das
  Translation-RichEdit trotzdem gefuellt.

Zwischenbefund:

- Der eigentliche Translation-Text haengt nicht einfach an einem der
  13 direkten `SetWindowTextW`-Calls.
- Der relevante Schreibpfad laeuft wahrscheinlich ueber `SendMessageW`,
  einen Wrapper oder eine RichEdit-spezifische Routine.
- Der naechste statische Suchraum sind deshalb `SendMessageW`-Aufrufe mit
  RichEdit-Messages und die internen `RichEditCtrl`-Methoden.

## Konsequenz

Der naechste sinnvolle Binary-Patch waere ein Output-Patch:

1. Den konkreten Callsite identifizieren, der `EditTranslation` in das
   Ergebnis-`RICHEDIT50W` schreibt.
2. Dort vor oder nach dem Setzen des Textes Link-Marker auswerten.
3. Den sichtbaren Text ohne Marker/URL schreiben.
4. Innerhalb des QTranslate-Prozesses RichEdit-Linkformat anwenden oder eine
   eigene Link-Klickbehandlung nachziehen.

Wichtig:

- `Service.js` kann aktuell nur sauberen Plaintext liefern oder sichtbare URL
  ausschreiben.
- Versteckte klickbare Anker erfordern eine Ausgabe-/RichEdit-Aenderung in
  `QTranslate.exe`.
- Der bereits erledigte Binary-Patch ist nicht verloren, aber er sitzt auf der
  Eingabe-Seite.

## Update 2026-04-23: Output-Patch erster Stand

Der erste Output-Patch ist jetzt umgesetzt in:

```text
F:\Codex\QTranslate_diss\scripts\patch_qtranslate_output_links.py
F:\Codex\QTranslate_diss\asm\format_output_links.s
F:\Codex\QTranslate_diss\QTranslate.6.9.0\QTranslate.output_links.exe
```

Technische Aenderungen:

- RichEdit-Initialisierung wird von `TM_PLAINTEXT` auf `TM_RICHTEXT` gepatcht:
  - `0x408C27`: `push 1` -> `push 0`
- Es wird eine neue executable PE-Section `.qtlnk` angehaengt.
- Ein Wrapper um den internen RichEdit-SetText-Helfer `0x408924` wird fuer
  stabile Translation-Callsites eingesetzt:
  - `0x42EDA4`
  - `0x42EF17`
- Der Wrapper sucht nach Mustern wie:
  - `READ (https://...)`
  - `LESEN (https://...)`
  - allgemein `WORD (http...)` / `WORD (www...)`
- Danach wird:
  - der Gesamtbereich `WORD (URL)` mit `CFE_LINK` markiert
  - der Suffix ` (URL)` mit `CFE_HIDDEN` versteckt

Wichtige Einschraenkung:

- `WM_GETTEXT` liest versteckten RichEdit-Text weiterhin mit aus.
- Darum zeigt die technische Probe weiterhin `READ (https://...)`, auch wenn
  der URL-Teil visuell im RichEdit versteckt sein kann.
- Ob QTranslate beim Klick den versteckten URL-Teil korrekt an seinen
  vorhandenen Link-Handler weitergibt, muss noch manuell im UI geprueft werden.

Verifizierter Smoke-Test nach Release-Build:

```text
F:\Codex\QTranslate_diss\release\QTranslate_portable_clean\QTranslate.exe
```

Quelle:

```text
FreeTranslations использует translate-pa.googleapis.com ЧИТАТЬ
```

HTML-Quelle:

```html
<div>FreeTranslations использует translate-pa.googleapis.com <a href="https://www.perplexity.ai/search/test-free">ЧИТАТЬ</a></div>
```

Gelesenes Ergebnisfeld per `WM_GETTEXT`:

```text
[FreeTranslations]
FreeTranslations verwendet translate-pa.googleapis.com READ (https://www.perplexity.ai/search/test-free).
```

Das belegt:

- die URL kommt wieder bis in den Ergebnistext
- die neue EXE startet stabil im Hotkeypfad
- der Output-Patch hat eine technische Grundlage, um den URL-Teil im RichEdit
  zu verstecken und den sichtbaren Anker zu formatieren
