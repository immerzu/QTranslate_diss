# Link-Erhalt in mehreren Diensten

Der gemeinsame Link-Pfad in `Services/Common.js` erkennt jetzt `Text (URL)`-Paare aus Browser-Selektionstext, fuegt nur den sichtbaren Text als Token in den Request ein und stellt ihn in der Antwort wieder als HTML-Anker her.

## Getestete Dienste

- `WebTran`
- `Lingvanex`
- `LaraTranslate`
- `TranslateEU`
- `TranslatorEU`
- `Yandex`
- `YandexInL`
- `Google Translate`
- `Google New`
- `DeepL`

## Befund

- Die Request-Bodies enthalten jetzt einzelne Link-Tokens wie `__QTLINK1__` direkt nach dem sichtbaren Linktext.
- Bei Linkstellen am Zeilenende wird der Token mit einem Satzpunkt stabilisiert, weil `translate-pa` sonst in laengeren Texten den Linkteil teilweise entfernt.
- Die URL bleibt im Hintergrund und wird in den Rueckgaben wieder als `<a href="...">Text</a>` restauriert.
- Der portable Stand wurde neu gebaut unter `release/QTranslate_portable_clean`.

## Repro vom 2026-04-23

- `FreeTranslations`: langer Beispieltext mit drei Perplexity-Links, `links=3`, kein `ЧИ</a>ТАТЬ` und kein breit gezogener Anchor.
- `WebTran`: gleicher Beispieltext, `links=3`, kein Verlust der Zeilenende-Links nach Token-Stabilisierung.
- `Lingvanex`: gleicher Beispieltext, `links=3`; `LESEN SIE` wird als zusammenhaengender Anker restauriert, statt nur `SIE` zu verlinken.
- `Services.rar` und die einzelnen Service-Archive im Portable-Release werden vom Builder neu aktualisiert.

## Repro mit verschobenen URLs

Der reale QTranslate-Lauf hatte URLs teilweise schon vor dem Service falsch in den Quelltext eingesetzt:

- `ЧИ (url)ТАТЬ`
- `googleapis. (url)com ЧИТАТЬ`
- `lingva (url)nex.com ЧИТАТЬ`

`Common.js` normalisiert diese Fehlformen vor der Tokenisierung wieder zu `ЧИТАТЬ (url)` und setzt getrennte Domainfragmente zusammen. Der direkte Release-Test liefert fuer `FreeTranslations`, `WebTran` und `Lingvanex` jeweils `links=3` und `broken=false`.

## Hinweis

Die Matrix basiert auf dem typischen Browser-Selektionsfall mit einem echten Anchor-Link plus einer nackten URL im selben Textblock.
