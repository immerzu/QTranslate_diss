var _qtRD=ResponseData;function _qtErrPrefix(a){a=a||"";return /^\s*\[E\]/.test(a)?a:"[E] "+(a||"Keine Daten zurueckgegeben.")}ResponseData=function(a,b,c,d,e){if(!e){var f=a||"";if(!f||(!/^\s*\[E\]/.test(f)&&/^(?:\s*(?:DeepL|YandexInL|Yandex|Google|Microsoft|FreeTranslations|WebTran|TranslateEU|TranslatorEU|Lingvanex|LaraTranslate|Wikipedia|Multi)\s*:\s*)?(?:keine |Keine |Fehler|Error|Skript-Fehler|Zeit|unsupported|failed|timeout|unavailable|no usable|no data|empty)/i.test(f)))a=_qtErrPrefix(f)}_qtRD.call(this,a,b,c,d,e)};
function serviceHeader(){return new ServiceHeader(119,"WebTran","WebTran.eu web translator route via Google Translate PA translateHtml."+Const.NL2+"https://www.webtran.eu/",Capability.TRANSLATE|Capability.DETECT_LANGUAGE)}
function serviceHost(a,b,c){return"https://translate-pa.googleapis.com"}
function serviceLink(a,b,c){var d="https://www.webtran.eu/";return a&&(d+="?text="+encodeGetParam(a)),d}
function _wtCode(a){if(a===AUTO_DETECT_LANGUAGE)return"auto";a=codeFromLanguage(a);return a===UNKNOWN_LANGUAGE_CODE?"auto":a}
function _wtHeaders(){return getHeader()+Const.NL+"Content-Type: application/json+protobuf; charset=utf-8"+Const.NL+"X-goog-api-key: AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520"+Const.NL+"Origin: https://www.webtran.eu"+Const.NL+"Referer: https://www.webtran.eu/"}
function _wtBody(a,b,c){return stringifyJSON([[[limitSource(prepareLinkedSource(a),4500)],_wtCode(b),_wtCode(c||ENGLISH_LANGUAGE)],"te"])}
function _wtJSON(a){try{return parseJSON(a)}catch(b){return null}}
function _wtText(a){return stripHtml(unquoteHtml(a||""))}
function serviceDetectLanguageRequest(a){return new RequestData(HttpMethod.POST,"/v1/translateHtml",_wtBody(a,AUTO_DETECT_LANGUAGE,ENGLISH_LANGUAGE),_wtHeaders())}
function serviceDetectLanguageResponse(a){a=_wtJSON(a);return a&&a[1]&&a[1][0]?languageFromCode(a[1][0]):UNKNOWN_LANGUAGE}
function serviceTranslateRequest(a,b,c){return new RequestData(HttpMethod.POST,"/v1/translateHtml",_wtBody(a,b,c),_wtHeaders())}
function serviceTranslateResponse(a,b,c,d){b=_wtJSON(b);if(b&&b[0]&&b[0][0])return new ResponseData(_wtText(b[0][0]),isLanguage(c)?c:languageFromCode(b[1]&&b[1][0]),d);return new ResponseData("WebTran: keine verwertbare Antwort.",c,d)}
SupportedLanguages=[-1,"auto","af","az","sq","ar","hy","eu","be","bg","ca","zh-CN","zh-TW","hr","cs","da","nl","en","et","fi","tl","fr","gl","de","el","ht","iw","hi","hu","is","id","it","ga","ja","ka","ko","lv","lt","mk","ms","mt","no","fa","pl","pt","ro","ru","sr","sk","sl","es","sw","sv","th","tr","uk","ur","vi","cy","yi","eo","hmn","la","lo","kk","uz","si","tg","te","km","mn","kn","ta","mr","bn","tt"];
