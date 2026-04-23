# QTranslate.exe: Plan zum Erhalt von Link-URLs bei Browser-Selektion

## Ziel

Beim Übersetzen von markiertem Browser-Text soll QTranslate aus

`ЧИТАТЬ`

möglichst

`ЧИТАТЬ (https://...)`

machen.

Die Analyse zeigt: Der Link geht in `QTranslate.exe` bereits vor dem Translate-Service verloren.

## Relevante Klassen

- `TaskCopySelection@tasks@windows@@`
  - VTable: `0x54eee8`
  - zentrale Selektionsmethode: `0x4147ed`
- `TaskTranslateClipboard@tasks@windows@@`
  - VTable: `0x54f608`
  - Clipboard-Zugriff: `0x4056ce`
- `TaskReplaceSelection@tasks@windows@@`
  - VTable: `0x54f648`

## Relevante Funktionen

### 1. Accessibility-Selektion

- `0x404901`
- benutzt:
  - `GetCursorPos`
  - `AccessibleObjectFromPoint`
  - `IAccessible`-Methoden über VTable

Dieser Pfad liest sichtbaren Text aus dem Accessibility-Objekt, aber kein `href`.

### 2. Unicode-Clipboard-Leser

- `0x43be7e`
- öffnet Clipboard
- liest ausschließlich Format `13` = `CF_UNICODETEXT`
- übernimmt den Inhalt direkt in den internen String

Das ist der Plaintext-Kollaps.

### 3. Copy-via-Clipboard-Pfad

- `0x43befc`
- relevanter Unterpfad:
  - `0x43bf2e` -> Clipboard-Snapshot
  - simulierte Tastenkombination
  - `0x43bfc7` -> Aufruf von `0x43be7e`
  - `0x43bfd9` -> Restore des alten Clipboards

Dieser Pfad ist besonders wichtig, weil Browser-Selektion hier typischerweise über `Ctrl+C` / `Ctrl+Insert` abgegriffen wird.

### 4. Clipboard-Snapshot / Restore

- Snapshot: `0x43ec71`
- Restore: `0x43ee28`

Diese Helfer können mehrere Clipboard-Formate sichern und wiederherstellen.
Das Problem ist also nicht das Snapshotting, sondern der spätere Import per `CF_UNICODETEXT`.

## Exakte Call-Sites

### In `TaskCopySelection`

Selektionsmethode `0x4147ed`:

- `0x414814` -> ruft `0x404901` auf
- `0x414829` -> ruft `0x43be7e` auf

Bedeutung:

- Modus `2`: Accessibility
- Modus `3`: direkt Unicode-Clipboard

### Im simulierten Copy-Pfad

- `0x43bfc7` -> ruft `0x43be7e` auf

### Weitere Unicode-Clipboard-Nutzer

- `0x405302` -> `0x43be7e`
- `0x4056e6` -> `0x43be7e`
- `0x414829` -> `0x43be7e`
- `0x43bfc7` -> `0x43be7e`

## Freie Codefläche

In `.text` gibt es eine brauchbare Code-Cave:

- Start: `0x53d0a3`
- Länge: `349` Byte Nullpadding

Das reicht für einen kleinen Helfer plus Konstanten.

## Patch-Strategie

### Primärer Eingriff

Nicht zuerst `0x404901` patchen.

Der beste Einstiegspunkt ist ein neuer Helper:

- `read_html_or_unicode_clipboard()`

Dieser Helper soll die Logik von `0x43be7e` erweitern:

1. Clipboard öffnen
2. `RegisterClipboardFormatA("HTML Format")` dynamisch auflösen
3. `GetClipboardData(htmlFormat)` versuchen
4. Falls HTML vorhanden:
   - Buffer locken
   - `href="..."` oder `href='...'` suchen
   - URL extrahieren
   - gleichzeitig Plaintext wie bisher ermitteln
   - Ergebnis bauen:
     - `plainText`
     - `" ("`
     - `url`
     - `")"`
5. Falls HTML fehlt oder Parsing scheitert:
   - unverändert auf die bisherige Unicode-Logik zurückfallen

### Umleitung

Minimal sinnvoll umzuleitende Call-Sites:

- `0x414829`
- `0x43bfc7`

Optional ebenfalls:

- `0x4056e6`
- `0x405302`

### Warum diese Reihenfolge?

- `0x414829` deckt den direkten Clipboard-Pfad in `TaskCopySelection` ab
- `0x43bfc7` deckt den wichtigen Browser-Fall über simuliertes `Ctrl+C` ab
- die Accessibility-Funktion `0x404901` bleibt als Fallback unberührt

## Dynamisch aufzulösende APIs

Nicht direkt importiert:

- `RegisterClipboardFormatA`

Kann aber mit bereits vorhandenen Imports geholt werden:

- `LoadLibraryExA`
- `GetProcAddress`

ASCII-Strings können in die Code-Cave gelegt werden:

- `"user32.dll"`
- `"RegisterClipboardFormatA"`
- `"HTML Format"`

## Parser-Minimum für CF_HTML

Für einen ersten Binär-Patch reicht ein bewusst einfacher Parser:

- nicht volles HTML parsen
- nur erstes `href=`
- URL bis zum schließenden Quote kopieren

Das ist nicht perfekt, aber für den häufigsten Fall "ein markierter Link" ausreichend.

## Pseudocode

```c
bool read_html_or_unicode_clipboard(String* out, unsigned limitChars) {
  if (!openClipboardGuard()) return false;

  char* html = tryGetHtmlClipboard();
  if (html) {
    UrlSpan url = findFirstHref(html);
    if (url.found) {
      WideText plain = readUnicodeClipboardAsWide(limitChars);
      if (plain.ok && plain.len > 0) {
        WideText merged = buildWide(
          plain,
          L" (",
          asciiUrlToWide(url),
          L")"
        );
        out->assign(merged.ptr, merged.len);
        closeClipboardGuard();
        return true;
      }
    }
  }

  bool ok = old_read_unicode_clipboard(out, limitChars);
  closeClipboardGuard();
  return ok;
}
```

## Erwartetes Ergebnis

Der Patch soll nicht den Übersetzer selbst ändern, sondern den Text, der den Services übergeben wird.

Beispiel:

- Browser-Selektion intern bisher: `ЧИТАТЬ`
- Browser-Selektion nach Patch: `ЧИТАТЬ (https://example.com/...)`

## Wichtigste technische Aussage

Der Verlustpunkt liegt derzeit in `TaskCopySelection` und seinen Clipboard-Helfern, nicht in den `Service.js`-Dateien.
