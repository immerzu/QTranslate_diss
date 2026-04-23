# HTML-Matrix fuer den Link-Patch

Stand: 2026-04-22

## Ziel

Nach der ersten End-to-End-Bestaetigung wurde der Patch gegen mehrere HTML-Varianten geprueft, um Parser-Grenzen sichtbar zu machen.

Verwendetes Skript:

- `F:\Codex\QTranslate_diss\scripts\run_qtranslate_html_matrix.py`

Dieses Skript nutzt intern:

- `F:\Codex\QTranslate_diss\scripts\probe_qtranslate_capture.py`

und liest den effektiven Text direkt aus den sichtbaren `RICHEDIT50W`-Feldern des Main Window.

## Wichtige Zwischenbefunde

Die erste Matrix zeigte zunaechst einen echten Parserfehler:

- der damalige Patch nahm das erste `href=` irgendwo im HTML
- dadurch konnte ein fremdes `href` aus z. B. `<span href=...>` vor dem eigentlichen Link gewonnen werden

Daraufhin wurde `asm/read_html_or_unicode_clipboard.s` nachgezogen:

- `href` wird jetzt nur noch innerhalb eines echten `<a ...>`-Starttags gesucht
- damit verschwindet der Fehlgriff auf fremde `href`-Attribute

Danach wurde der Merge-Schritt grundlegend umgestellt:

- nicht mehr nur URL-Sammeln am Ende
- stattdessen wird fuer jeden echten Anchor die URL direkt nach dem zugehoerigen sichtbaren Linktext eingefuegt
- Ausgabeform:
  - `text ... linktext (url) ... rest`

## Kontroll-Baseline

### Original `QTranslate.exe`

Fall:

- `AA <a href="https://case1.example/link">ЧИТАТЬ</a> BB`

Effektiver Quelltext:

- `AA ЧИТАТЬ BB`

Effektiver Zieltext:

- `[FreeTranslations]`
- `AA LESEN BB`

Bedeutung:

- das Original ignoriert die URL weiterhin vollstaendig

## Ergebnisse mit `QTranslate.patched.exe`

### Funktioniert

Diese Faelle liefern jetzt korrektes Inline-Mapping:

- doppelt gequotetes `href="..."`
- einfach gequotetes `href='...'`
- ungequotetes `href=https://...`
- `HREF` in Grossschreibung
- verschachteltes Markup innerhalb des `<a>`-Texts
- benannte HTML-Entities wie `&amp;`
- numerische HTML-Entities wie `&#x1F600;`

Beispiele:

- `AA ЧИТАТЬ (https://case1.example/link) BB`
- `AA ЧИТАТЬ (https://case2.example/link) BB`
- `AA ЧИТАТЬ (https://case3.example/link) BB`
- `AA ЧИТАТЬ (https://case4.example/link) BB`
- `AA ЧИТАТЬ (https://case5.example/link) BB`
- `AA A & B (https://entity.example/ab) BB`
- `Fish & Chips Go (https://entity.example/go)`
- `Smile 😀 Go (https://entity.example/emoji-go)`

### Bug behoben

Frueherer Problemfall:

- `<span href="https://wrong.example/meta">Meta</span> <a href="https://good.example/go">Go</a>`

Neues Ergebnis:

- `Meta Go (https://good.example/go)`

Bedeutung:

- der Patch greift jetzt nicht mehr auf ein beliebiges erstes `href=` zu
- sondern auf das erste `href` eines echten Anchor-Tags

### Mehrere Links

Mehrere Links in einer Selektion:

- `<a href="https://first.example/a">Alpha</a> + <a href="https://second.example/b">Beta</a>`

Ergebnis:

- `Alpha (https://first.example/a) + Beta (https://second.example/b)`

Bedeutung:

- mehrere echte Anchor-URLs werden jetzt inline an die jeweils passende Anchor-Position gesetzt

Zusatztest mit drei unterschiedlich formatierten Links:

- doppelt gequotet
- einfach gequotet
- ungequotet
- mit verschachteltem Markup

Ergebnis:

- `One (https://one.example/a) / Two (https://two.example/b) / Three (https://three.example/c)`

### Fallback ohne Link bleibt sauber

Fall:

- HTML ohne Anchor-`href`

Ergebnis:

- Quelltext bleibt nur Plaintext
- keine falsche URL-Anhaengung

## Technische Schlussfolgerung

Der aktuelle Patchstand ist jetzt in vier Schritten abgesichert:

1. End-to-End-Nachweis:
   - Main-Window-Clipboard-Pfad uebernimmt `ЧИТАТЬ (https://...)`
2. Parser-Haertung:
   - nur echte Anchor-`href` werden akzeptiert
3. Inline-Link-Mapping:
   - jeder erkannte Anchor bekommt seine URL direkt an seiner eigenen Textposition
4. Mehrfach-Link-Erweiterung:
   - mehrere Anchors werden unabhaengig voneinander inline erweitert

## Relevante Implementationsbefunde

Beim Umstieg auf echtes Inline-Mapping traten zwei konkrete Shellcode-Bugs auf, die korrigiert wurden:

- der sichtbare Zeichenzähler in `count_visible` verlor seinen laufenden Wert beim Ueberspringen normaler Tags, weil ein Hilfsaufruf den Akkumulator in `EAX` ueberschrieb
- beim Einfuegen einer URL wurde der Restzaehler fuer den noch zu kopierenden Unicode-Plaintext nicht gesichert, wodurch der restliche Text nach dem ersten Anchor verlorenging
- fuer HTML-Entities zaehlte die Sichtbarkeitslogik vorher rohe Zeichenfolgen wie `&amp;` oder `&#x1F600;` statt ihrer tatsaechlichen sichtbaren Breite, wodurch Inline-Positionen bei Entity-Faellen verrutschten

Beide Fehler sind im aktuellen Patchstand behoben.

## Aktuelle Restgrenzen

- es gibt weiterhin keine echte HTML- oder DOM-Rekonstruktion, sondern eine positionsbasierte Zuordnung zwischen HTML-Anchor-Enden und `CF_UNICODETEXT`
- exotischere Sonderfaelle jenseits der jetzt abgedeckten benannten und numerischen Entities wurden noch nicht separat gehaertet
- Accessibility-Pfad ist davon weiterhin unberuehrt

## Relevante Dateien

- `F:\Codex\QTranslate_diss\asm\read_html_or_unicode_clipboard.s`
- `F:\Codex\QTranslate_diss\scripts\probe_qtranslate_capture.py`
- `F:\Codex\QTranslate_diss\scripts\run_qtranslate_html_matrix.py`
- `F:\Codex\QTranslate_diss\QTranslate.6.9.0\QTranslate.patched.exe`
