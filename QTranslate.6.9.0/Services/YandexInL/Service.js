var _qtRD=ResponseData;function _qtErrPrefix(a){a=a||"";return /^\s*\[E\]/.test(a)?a:"[E] "+(a||"Keine Daten zurueckgegeben.")}ResponseData=function(a,b,c,d,e){if(!e){var f=a||"";if(!f||(!/^\s*\[E\]/.test(f)&&/^(?:\s*(?:DeepL|YandexInL|Yandex|Google|Microsoft|FreeTranslations|WebTran|TranslateEU|TranslatorEU|Lingvanex|LaraTranslate|Wikipedia|Multi)\s*:\s*)?(?:keine |Keine |Fehler|Error|Skript-Fehler|Zeit|unsupported|failed|timeout|unavailable|no usable|no data|empty)/i.test(f)))a=_qtErrPrefix(f)}_qtRD.call(this,a,b,c,d,e)};
function serviceHeader() {
    return new ServiceHeader(
        111,
        "YandexInL",
        "Yandex Browser inline translation endpoint." + Const.NL2 +
        "https://translate.yandex.com/" + Const.NL2 +
        "Observed via api.browser.yandex.com/instaserp/translate",
        Capability.TRANSLATE | Capability.DETECT_LANGUAGE
    )
}

function serviceHost(a, b, c) {
    return "https://api.browser.yandex.com"
}

function serviceLink(a, b, c) {
    var d = "https://translate.yandex.com/";
    if (a) {
        b = isLanguage(b) ? codeFromLanguage(b) : "auto";
        c = isLanguage(c) ? codeFromLanguage(c) : "auto";
        d += format("?lang={0}-{1}&text={2}", b, c, encodeGetParam(a));
    }
    return d
}

function _generateUUID() {
    var a = (new Date).getTime();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(b) {
        var c = (a + 16 * Math.random()) % 16 | 0;
        a = Math.floor(a / 16);
        return ("x" === b ? c : 3 & c | 8).toString(16)
    }).replace(/-/g, "")
}

function _isSingleWord(a) {
    a = trimString(prepareLinkedSource(a));
    return !!a && !/[\r\n]/.test(a) && 1 === a.split(/\s+/).length
}

function _inlineHeaders() {
    return "Accept: application/json" + Const.NL +
        "Content-Type: application/x-www-form-urlencoded" + Const.NL +
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36"
}

function _inlineTargetLanguage(a) {
    var b = isLanguage(a) ? codeFromLanguage(a) : "";
    return b || SupportedLanguages[ENGLISH_LANGUAGE]
}

function _inlineTitle(a) {
    a = prepareLinkedSource(a);
    a = removeEmptyLines(a).replace(/\r\n/g, " ");
    return limitSource(a, 120)
}

function _inlineCoreBody(a, b) {
    return "text=" + encodePostParam(a) +
        "&brandID=int" +
        "&statLang=" + encodePostParam(b) +
        "&targetLang=auto" +
        "&locale=" + encodePostParam(b) +
        "&clid=2270494" +
        "&disable=serp" +
        "&use_llm_srv=0"
}

function _inlineFullBody(a, b) {
    return _inlineCoreBody(a, b) +
        "&url=" + encodePostParam(serviceLink()) +
        "&title=" + encodePostParam(_inlineTitle(a)) +
        "&before=" +
        "&after="
}

function _inlineResponseObject(a) {
    a = parseJSON(a);
    return a && 0 < a.length ? a[0] : null
}

function _singleWordSource(a) {
    a = limitSource(prepareLinkedSource(a), 256);
    return /\s$/.test(a) ? a : a + " "
}

function _legacyTranslateRequest(a, b, c, d) {
    b = isLanguage(b) ? codeFromLanguage(b) : "";
    return new RequestData(
        HttpMethod.POST,
        format("https://translate.yandex.net/api/v1/tr.json/translate?uuid={0}&srv=android&lang={1}-{2}&reason=auto&format=text&yu=2210680511641235828", _generateUUID(), b, codeFromLanguage(c)),
        "text=" + encodePostParam(limitSource(prepareLinkedSource(a), 1E3)),
        postHeader() + Const.NL + "Referer: " + serviceLink(),
        null,
        d
    )
}

function _legacyDetectRequest(a, b) {
    return new RequestData(
        HttpMethod.GET,
        format("https://translate.yandex.net/api/v1/tr.json/detect?uuid={0}&srv=android&text={1}", _generateUUID(), encodeGetParam(limitSource(prepareLinkedSource(a), 256))),
        null,
        getHeader() + Const.NL + "Referer: " + serviceLink(),
        null,
        b
    )
}

function _inlineRequest(a, b, c, d, e) {
    a = limitSource(prepareLinkedSource(a), c || 5E3);
    b = _inlineTargetLanguage(b);
    return new RequestData(
        HttpMethod.POST,
        "/instaserp/translate",
        d(a, b),
        _inlineHeaders(),
        null,
        e
    )
}

function serviceDetectLanguageRequest(a) {
    return _inlineRequest(a, ENGLISH_LANGUAGE, 256, _inlineCoreBody, "serviceDetectLanguageResponse")
}

function serviceDetectLanguageResponse(a) {
    a = _inlineResponseObject(a);
    return a ? languageFromCode(a.from) : UNKNOWN_LANGUAGE
}

function serviceTranslateRequest(a, b, c) {
    if (_isSingleWord(a)) {
        if (isLanguage(b)) return serviceTranslateSingleWordRequest(a, b, c);
        return _legacyDetectRequest(a, "serviceTranslateSingleWordDetectResponse")
    }
    return _inlineRequest(a, c, 5E3, _inlineCoreBody, "serviceTranslateResponseFast")
}

function serviceTranslateRequestFull(a, b, c) {
    return _inlineRequest(a, c, 5E3, _inlineFullBody, "serviceTranslateResponseFinal")
}

function serviceTranslateSingleWordDetectResponse(a, b, c, d) {
    b = parseJSON(b);
    c = b && 200 == b.code ? languageFromCode(b.lang) : UNKNOWN_LANGUAGE;
    return new ResponseData("", c, d, "", "serviceTranslateSingleWordRequest")
}

function serviceTranslateSingleWordRequest(a, b, c) {
    return _legacyTranslateRequest(_singleWordSource(a), isLanguage(b) ? b : ENGLISH_LANGUAGE, c, "serviceTranslateResponseFinal")
}

function _inlineBuildResponse(a, b, c, d) {
    a = _inlineResponseObject(b);
    b = "";
    if (a) {
        b = a.text || "";
        c = isLanguage(c) ? c : languageFromCode(a.from);
        d = languageFromCode(a.to) || d;
        return new ResponseData(b, c, d)
    }
    return null
}

function serviceTranslateResponseFast(a, b, c, d) {
    a = _inlineBuildResponse(a, b, c, d);
    return a || new ResponseData("", c, d, "", "serviceTranslateRequestFull")
}

function serviceTranslateResponseFinal(a, b, c, d) {
    var e = _inlineBuildResponse(a, b, c, d);
    if (e) return e;
    b = parseJSON(b);
    if (b && 200 == b.code && b.text) {
        c = isLanguage(c) ? c : languageFromCode((b.lang || "").split("-")[0]);
        d = languageFromCode((b.lang || "").split("-")[1]) || d;
        return new ResponseData(b.text.join("\n"), c, d)
    }
    return new ResponseData("", c, d)
}

function serviceTranslateResponse(a, b, c, d) {
    return serviceTranslateResponseFast(a, b, c, d)
}

SupportedLanguages = [-1, -1, "af", "az", "sq", "ar", "hy", "eu", "be", "bg", "ca", "zh", "zh", "hr", "cs", "da", "nl", "en", "et", "fi", -1, "fr", "gl", "de", "el", "ht", "he", "hi", "hu", "is", "id", "it", "ga", "ja", "ka", "ko", "lv", "lt", "mk", "ms", "mt", "no", "fa", "pl", "pt", "ro", "ru", "sr", "sk", "sl", "es", "sw", "sv", "th", "tr", "uk", "ur", "vi", "cy", "yi", "eo", -1, "la", "lo", "kk", "uz", "si", "tg", "te", "km", "mn", "kn", "ta", "mr", "bn", "tt"];
