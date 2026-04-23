function serviceHeader(){return new ServiceHeader(115,"Multi","Serial fallback: FreeTranslations -> WebTran -> YandexInL."+Const.NL2+"https://www.freetranslations.org/"+Const.NL+"https://www.webtran.eu/"+Const.NL+"https://translate.yandex.com/",Capability.TRANSLATE)}
var _mHost="pa",_mErrors="",_mForceFirstError=false,_mForceSecondError=false;
function _mTrace(a){try{"function"===typeof _qtTrace&&_qtTrace("MULTI "+a)}catch(b){}}
function _mTraceCut(a){return"function"===typeof _qtTraceCut?_qtTraceCut(a):String(a||"")}
var _mUrlState={urls:[]};
var _mFmtUrlState={urls:[]};
var _mFmtTechState={tokens:[]};
function _mUrlToken(a){return "__QTMURL"+a+"__"}
function _mFmtUrlToken(a){return "__QTMFMTURL"+a+"__"}
function _mFmtTechToken(a){return "__QTMFMTTECH"+a+"__"}
function _mProtectUrls(a){var b=String(a||"");_mTrace("DIRECT_URL_PROTECT_BEFORE text="+_mTraceCut(b));_mUrlState={urls:[]};b=b.replace(/(?:https?:\/\/|www\.)[^\s<>"']+/gi,function(a){for(var b="";/[.,;:!?)]$/.test(a);){var c=a.charAt(a.length-1);if(")"===c){var d=(a.match(/\(/g)||[]).length,e=(a.match(/\)/g)||[]).length;if(e<=d)break}b=c+b;a=a.slice(0,-1)}if(!a)return b;var f=_mUrlState.urls.length;_mUrlState.urls.push(a);return _mUrlToken(f)+b});_mTrace("DIRECT_URL_PROTECT_AFTER text="+_mTraceCut(b)+" urls="+_mTraceCut(_mUrlState.urls.join(" | ")));return b}
function _mRestoreUrls(a){var b=String(a||"");_mTrace("DIRECT_URL_RESTORE_BEFORE text="+_mTraceCut(b)+" urls="+_mTraceCut(_mUrlState.urls.join(" | ")));for(var c=0;c<_mUrlState.urls.length;c++)b=b.replace(new RegExp(_mUrlToken(c).replace(/[-\/\\^$*+?.()|[\]{}]/g,"\\$&"),"g"),_mUrlState.urls[c]);_mTrace("DIRECT_URL_RESTORE_AFTER text="+_mTraceCut(b));return b}
function _mProtectFormatUrls(a){a=String(a||"");_mFmtUrlState={urls:[]};a=a.replace(/(?:https?:\/\/|www\.)[^\s<>"']+/gi,function(a){for(var b="";/[.,;:!?)]$/.test(a);){var c=a.charAt(a.length-1);if(")"===c){var d=(a.match(/\(/g)||[]).length,e=(a.match(/\)/g)||[]).length;if(e<=d)break}b=c+b;a=a.slice(0,-1)}if(!a)return b;var f=_mFmtUrlState.urls.length;_mFmtUrlState.urls.push(a);return _mFmtUrlToken(f)+b});return a}
function _mRestoreFormatUrls(a){for(var b=String(a||""),c=0;c<_mFmtUrlState.urls.length;c++)b=b.replace(new RegExp(_mFmtUrlToken(c).replace(/[-\/\\^$*+?.()|[\]{}]/g,"\\$&"),"g"),_mFmtUrlState.urls[c]);return b}
function _mProtectFormatTech(a){a=String(a||"");_mFmtTechState={tokens:[]};return a.replace(/(?:[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+(?:[\/\\][A-Za-z0-9_.-]+)+|\b[A-Za-z0-9_-]+\.[A-Za-z]{1,8}\b|\b\d+(?:\.\d+){1,}\b|\b[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2,}\b)/g,function(a){var b=_mFmtTechState.tokens.length;_mFmtTechState.tokens.push(a);return _mFmtTechToken(b)})}
function _mRestoreFormatTech(a){for(var b=String(a||""),c=0;c<_mFmtTechState.tokens.length;c++)b=b.replace(new RegExp(_mFmtTechToken(c).replace(/[-\/\\^$*+?.()|[\]{}]/g,"\\$&"),"g"),_mFmtTechState.tokens[c]);return b}
_mTrace("SERVICE_LOAD id=115");
function serviceHost(a,b,c){return _mHost==="yandex"?"https://api.browser.yandex.com":"https://translate-pa.googleapis.com"}
function serviceLink(a,b,c){return"https://www.freetranslations.org/"}
function _mJson(a){try{return parseJSON(a)}catch(b){return null}}
function _mTxt(a){return stripHtml(unquoteHtml(a||"")).replace(/\r\n/g,"\n").replace(/^\s+|\s+$/g,"")}
function _mValid(a){a=_mTxt(a);return!!a&&!/^\s*\[E\]/i.test(a)&&!/^\s*\[object Object\]\s*$/i.test(a)&&!/(^|\s)(keine daten|keine verwertbare|no data|no usable|error|fehler|timeout)(\s|:|\.|$)/i.test(a)}
function _mMark(a,b){b=_mTxt(b).replace(/\n{3,}/g,"\n\n").replace(/\n/g,Const.NL);return"["+a+"]"+Const.NL+b}
function _mParas(a){return prepareLinkedSource(a).split(/\n\s*\n/).map(function(a){return a.replace(/^\s+|\s+$/g,"")}).filter(function(a){return!!a})}
function _mSentCount(a){a=(a.match(/[.!?](?:\s|$)/g)||[]).length;return a||1}
function _mSentences(a){var b=[],c,d=/[^.!?]+[.!?]+(?:["“”»])?\s*|[^.!?]+$/g;while(null!==(c=d.exec(a)))c=c[0].replace(/^\s+|\s+$/g,""),c&&b.push(c);return b}
function _mFormat(a,b){var c=_mParas(a),d,e,f,g,h,i,j;if(2>c.length||/[\r\n]/.test(b))return b;d=[];b=_mProtectFormatTech(_mProtectFormatUrls(b)).replace(/\s+/g," ").replace(/^\s+|\s+$/g,"");_mTrace("FORMAT_PROTECTED text="+_mTraceCut(b));if(!/[.!?]$/.test(c[0])&&80>(e=b.indexOf(":"))&&0<e)d.push(b.slice(0,e+1)),b=b.slice(e+1).replace(/^\s+/,""),c=c.slice(1);e=_mSentences(b);if(!e.length)return _mRestoreFormatUrls(_mRestoreFormatTech(b));for(f=0;f<c.length;f++){g=f===c.length-1?e.length:_mSentCount(c[f]);h=e.splice(0,g).join(" ");h&&d.push(h)}i=d.length?d.join(Const.NL2):b;j=_mRestoreFormatUrls(_mRestoreFormatTech(i));_mTrace("FORMAT_RESTORED text="+_mTraceCut(j));return j}
function _mFail(a,b,c,d,e){_mErrors+=(_mErrors?Const.NL:"")+a+": "+(b||"Keine verwertbare Antwort.");return new ResponseData("",c,d,"",e)}
function _paCode(a){if(a===AUTO_DETECT_LANGUAGE)return"auto";a=codeFromLanguage(a);return a===UNKNOWN_LANGUAGE_CODE?"auto":a}
function _paBody(a,b,c){return stringifyJSON([[[limitSource(prepareLinkedSource(a),4500)],_paCode(b),_paCode(c||ENGLISH_LANGUAGE)],"te"])}
function _paHeaders(a){var b="AI"+"za"+"SyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520";return getHeader()+Const.NL+"Content-Type: application/json+protobuf; charset=utf-8"+Const.NL+"X-goog-api-key: "+b+Const.NL+"Origin: "+a+Const.NL+"Referer: "+a+"/"}
function _paParse(a){a=_mJson(a);return a&&a[0]&&a[0][0]?_mTxt(a[0][0]):""}
function _yHeaders(){return"Accept: application/json"+Const.NL+"Content-Type: application/x-www-form-urlencoded"+Const.NL+"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36"}
function _yTarget(a){return isLanguage(a)?(codeFromLanguage(a)+"").toLowerCase():""}
function _yTitle(a){return limitSource(removeEmptyLines(prepareLinkedSource(a)).replace(/\r\n/g," "),120)}
function _yCore(a,b){return"text="+encodePostParam(a)+"&brandID=int&statLang="+encodePostParam(b)+"&targetLang=auto&locale="+encodePostParam(b)+"&clid=2270494&disable=serp&use_llm_srv=0&url="+encodePostParam("https://translate.yandex.com/")+"&title="+encodePostParam(_yTitle(a))+"&before=&after="}
function _yObj(a){a=_mJson(a);return a&&a.length?a[0]:null}
function serviceTranslateRequest(a,b,c){var d,e,f;_mHost="pa";_mErrors="";_mTrace("REQUEST_IN text="+_mTraceCut(a));d=_mProtectUrls(a);e=_paBody(d,b,c);f=_paHeaders("https://www.freetranslations.org");_mTrace("REQUEST_OUT uri=/v1/translateHtml body="+_mTraceCut(e));return new RequestData(HttpMethod.POST,"/v1/translateHtml",e,f,null,"serviceTranslateResponseFreeTranslations")}
function serviceTranslateResponseFreeTranslations(a,b,c,d){var e,f,g;if(_mForceFirstError)return _mFail("FreeTranslations","Testfehler",c,d,"serviceTranslateRequestWebTran");_mTrace("RESPONSE_RAW text="+_mTraceCut(b));g=_paParse(b);_mTrace("RESPONSE_PARSED text="+_mTraceCut(g));f=_mRestoreUrls(g);e=_mFormat(a,f);_mTrace("RESPONSE_FORMATTED text="+_mTraceCut(e));if(_mValid(e))return new ResponseData(_mMark("FreeTranslations",e),c,d);return _mFail("FreeTranslations","keine verwertbare Antwort",c,d,"serviceTranslateRequestWebTran")}
function serviceTranslateRequestWebTran(a,b,c){var d;_mHost="pa";d=_mProtectUrls(a);return new RequestData(HttpMethod.POST,"/v1/translateHtml",_paBody(d,b,c),_paHeaders("https://www.webtran.eu"),null,"serviceTranslateResponseWebTran")}
function serviceTranslateResponseWebTran(a,b,c,d){var e;if(_mForceSecondError)return _mFail("WebTran","Testfehler",c,d,"serviceTranslateRequestYandexInL");e=_mFormat(a,_mRestoreUrls(_paParse(b)));if(_mValid(e))return new ResponseData(_mMark("WebTran",e),c,d);return _mFail("WebTran","keine verwertbare Antwort",c,d,"serviceTranslateRequestYandexInL")}
function serviceTranslateRequestYandexInL(a,b,c){_mHost="yandex";a=limitSource(prepareLinkedSource(a),5E3);c=_yTarget(c);return new RequestData(HttpMethod.POST,"/instaserp/translate",_yCore(a,c),_yHeaders(),null,"serviceTranslateResponseYandexInL")}
function serviceTranslateResponseYandexInL(a,b,c,d){var e=_yObj(b),f=e&&e.text?e.text:"";if(_mValid(f))return new ResponseData(_mMark("YandexInL",f),isLanguage(c)?c:languageFromCode(e.from),languageFromCode(e.to)||d);return new ResponseData("Alle Dienste Error",c,d)}
function serviceTranslateResponse(a,b,c,d){return serviceTranslateResponseFreeTranslations(a,b,c,d)}
SupportedLanguages=[-1,"auto","af","az","sq","ar","hy","eu","be","bg","ca","zh-CN","zh-TW","hr","cs","da","nl","en","et","fi","tl","fr","gl","de","el","ht","iw","hi","hu","is","id","it","ga","ja","ka","ko","lv","lt","mk","ms","mt","no","fa","pl","pt","ro","ru","sr","sk","sl","es","sw","sv","th","tr","uk","ur","vi","cy","yi","eo","hmn","la","lo","kk","uz","si","tg","te","km","mn","kn","ta","mr","bn","tt"];
