var _qtRD=ResponseData;function _qtErrPrefix(a){a=a||"";return /^\s*\[E\]/.test(a)?a:"[E] "+(a||"Keine Daten zurueckgegeben.")}ResponseData=function(a,b,c,d,e){if(!e){var f=a||"";if(!f||(!/^\s*\[E\]/.test(f)&&/^(?:\s*(?:DeepL|YandexInL|Yandex|Google|Microsoft|FreeTranslations|WebTran|TranslateEU|TranslatorEU|Lingvanex|LaraTranslate|Wikipedia|Multi)\s*:\s*)?(?:keine |Keine |Fehler|Error|Skript-Fehler|Zeit|unsupported|failed|timeout|unavailable|no usable|no data|empty)/i.test(f)))a=_qtErrPrefix(f)}_qtRD.call(this,a,b,c,d,e)};
function serviceHeader(){return new ServiceHeader(118,"FreeTranslations","FreeTranslations.org web translator route via Google Translate PA translateHtml."+Const.NL2+"https://www.freetranslations.org/",Capability.TRANSLATE|Capability.DETECT_LANGUAGE)}
function serviceHost(a,b,c){return"https://translate-pa.googleapis.com"}
function serviceLink(a,b,c){var d="https://www.freetranslations.org/";return a&&(d+="?text="+encodeGetParam(a)),d}
function _ftCode(a){if(a===AUTO_DETECT_LANGUAGE)return"auto";a=codeFromLanguage(a);return a===UNKNOWN_LANGUAGE_CODE?"auto":a}
function _ftHeaders(){return getHeader()+Const.NL+"Content-Type: application/json+protobuf; charset=utf-8"+Const.NL+"X-goog-api-key: AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520"+Const.NL+"Origin: https://www.freetranslations.org"+Const.NL+"Referer: https://www.freetranslations.org/"}
function _ftAttr(a,b){a=String(a||"");b=(b||"").toLowerCase()+"=";var c=a.toLowerCase(),d=c.indexOf(b);if(d<0)return"";d+=b.length;while(d<a.length&&/\s/.test(a.charAt(d)))d++;if(d>=a.length)return"";if(a.charAt(d)=="\""||a.charAt(d)=="'"){var e=a.charAt(d),f=a.indexOf(e,d+1);return f>=0?a.slice(d+1,f):""}var g=/^[^\s>]+/.exec(a.slice(d));return g?g[0]:""}
function _ftHtml(a){return String(a||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")}
var _ftHasHtmlLinks=!1;
function _ftSource(a){_ftHasHtmlLinks=!1;return prepareSource(a||"").replace(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi,function(a,b,c){var d,e;c=stripHtml(unquoteHtml(c||"")).replace(/\r\n/g,"\n").replace(/^\s+|\s+$/g,"");d=_ftAttr(b,"href");return c&&d?(_ftHasHtmlLinks=!0,'<a href="'+_ftHtml(d)+'">'+_ftHtml(c)+'</a>'):c||d||_ftAttr(b,"title")||_ftAttr(b,"aria-label")||_ftAttr(b,"data-text")||""}).replace(/(^|[\s>])([^\r\n<>]*?)([^\s<>()]+)\s*\(((?:https?:\/\/|www\.)[^()\s]+)\)/g,function(a,b,c,d,e){_ftHasHtmlLinks=!0;return b+c+'<a href="'+_ftHtml(e)+'">'+_ftHtml(d)+'</a>'})}
function _ftNormalizeHtml(a){return String(a||"").replace(/\r\n|\r|\n/g,"<br/>").replace(/<a\b([^>]*)>\s*\[([^\]]+)\]\s*<\/a>/gi,function(a,b,c){return'<a'+b+">"+trimString(c)+"</a>"})}function _ftRestoreLinks(a){return a||""}function _ftBody(a,b,c){return stringifyJSON([[[limitSource(prepareLinkedSource(a),4500)],_ftCode(b),_ftCode(c||ENGLISH_LANGUAGE)],"te"])}
function _ftJSON(a){try{return parseJSON(a)}catch(b){return null}}
function _ftText(a){return stripHtml(unquoteHtml(a||""))}
function _ftParas(a){return _ftSource(a).split(/\n\s*\n/).map(function(a){return a.replace(/^\s+|\s+$/g,"")}).filter(function(a){return!!a})}
function _ftSentCount(a){a=(a.match(/[.!?](?:\s|$)/g)||[]).length;return a||1}
function _ftSentences(a){var b=[],c,d=/[^.!?]+[.!?]+(?:["???])?\s*|[^.!?]+$/g;while(null!==(c=d.exec(a)))c=c[0].replace(/^\s+|\s+$/g,""),c&&b.push(c);return b}
function _ftFormat(a,b){var c=_ftParas(a),d,e,f,g,h;if(2>c.length||/[\r\n]/.test(b))return b;d=[];b=b.replace(/\s+/g," ").replace(/^\s+|\s+$/g,"");if(!/[.!?]$/.test(c[0])&&80>(e=b.indexOf(":"))&&0<e)d.push(b.slice(0,e+1)),b=b.slice(e+1).replace(/^\s+/,""),c=c.slice(1);e=_ftSentences(b);if(!e.length)return b;for(f=0;f<c.length;f++){g=f===c.length-1?e.length:_ftSentCount(c[f]);h=e.splice(0,g).join(" ");h&&d.push(h)}return d.length?d.join(Const.NL2):b}
function serviceDetectLanguageRequest(a){return new RequestData(HttpMethod.POST,"/v1/translateHtml",_ftBody(a,AUTO_DETECT_LANGUAGE,ENGLISH_LANGUAGE),_ftHeaders())}
function serviceDetectLanguageResponse(a){a=_ftJSON(a);return a&&a[1]&&a[1][0]?languageFromCode(a[1][0]):UNKNOWN_LANGUAGE}
function serviceTranslateRequest(a,b,c){return new RequestData(HttpMethod.POST,"/v1/translateHtml",_ftBody(a,b,c),_ftHeaders())}
function serviceTranslateResponse(a,b,c,d){b=_ftJSON(b);if(b&&b[0]&&b[0][0])return new ResponseData(_ftText(b[0][0]),isLanguage(c)?c:languageFromCode(b[1]&&b[1][0]),d);return new ResponseData("FreeTranslations: keine verwertbare Antwort.",c,d)}
SupportedLanguages=[-1,"auto","af","az","sq","ar","hy","eu","be","bg","ca","zh-CN","zh-TW","hr","cs","da","nl","en","et","fi","tl","fr","gl","de","el","ht","iw","hi","hu","is","id","it","ga","ja","ka","ko","lv","lt","mk","ms","mt","no","fa","pl","pt","ro","ru","sr","sk","sl","es","sw","sv","th","tr","uk","ur","vi","cy","yi","eo","hmn","la","lo","kk","uz","si","tg","te","km","mn","kn","ta","mr","bn","tt"];





