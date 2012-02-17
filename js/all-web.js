
/*
 *	lib/js/lib/jquery.min.js
 *//*!
 * jQuery JavaScript Library v1.6.2
 * http://jquery.com/
 *
 * Copyright 2011, John Resig
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * Includes Sizzle.js
 * http://sizzlejs.com/
 * Copyright 2011, The Dojo Foundation
 * Released under the MIT, BSD, and GPL Licenses.
 *
 * Date: Thu Jun 30 14:16:56 2011 -0400
 */
(function(a,b){function cv(a){return f.isWindow(a)?a:a.nodeType===9?a.defaultView||a.parentWindow:!1}function cs(a){if(!cg[a]){var b=c.body,d=f("<"+a+">").appendTo(b),e=d.css("display");d.remove();if(e==="none"||e===""){ch||(ch=c.createElement("iframe"),ch.frameBorder=ch.width=ch.height=0),b.appendChild(ch);if(!ci||!ch.createElement)ci=(ch.contentWindow||ch.contentDocument).document,ci.write((c.compatMode==="CSS1Compat"?"<!doctype html>":"")+"<html><body>"),ci.close();d=ci.createElement(a),ci.body.appendChild(d),e=f.css(d,"display"),b.removeChild(ch)}cg[a]=e}return cg[a]}function cr(a,b){var c={};f.each(cm.concat.apply([],cm.slice(0,b)),function(){c[this]=a});return c}function cq(){cn=b}function cp(){setTimeout(cq,0);return cn=f.now()}function cf(){try{return new a.ActiveXObject("Microsoft.XMLHTTP")}catch(b){}}function ce(){try{return new a.XMLHttpRequest}catch(b){}}function b$(a,c){a.dataFilter&&(c=a.dataFilter(c,a.dataType));var d=a.dataTypes,e={},g,h,i=d.length,j,k=d[0],l,m,n,o,p;for(g=1;g<i;g++){if(g===1)for(h in a.converters)typeof h=="string"&&(e[h.toLowerCase()]=a.converters[h]);l=k,k=d[g];if(k==="*")k=l;else if(l!=="*"&&l!==k){m=l+" "+k,n=e[m]||e["* "+k];if(!n){p=b;for(o in e){j=o.split(" ");if(j[0]===l||j[0]==="*"){p=e[j[1]+" "+k];if(p){o=e[o],o===!0?n=p:p===!0&&(n=o);break}}}}!n&&!p&&f.error("No conversion from "+m.replace(" "," to ")),n!==!0&&(c=n?n(c):p(o(c)))}}return c}function bZ(a,c,d){var e=a.contents,f=a.dataTypes,g=a.responseFields,h,i,j,k;for(i in g)i in d&&(c[g[i]]=d[i]);while(f[0]==="*")f.shift(),h===b&&(h=a.mimeType||c.getResponseHeader("content-type"));if(h)for(i in e)if(e[i]&&e[i].test(h)){f.unshift(i);break}if(f[0]in d)j=f[0];else{for(i in d){if(!f[0]||a.converters[i+" "+f[0]]){j=i;break}k||(k=i)}j=j||k}if(j){j!==f[0]&&f.unshift(j);return d[j]}}function bY(a,b,c,d){if(f.isArray(b))f.each(b,function(b,e){c||bC.test(a)?d(a,e):bY(a+"["+(typeof e=="object"||f.isArray(e)?b:"")+"]",e,c,d)});else if(!c&&b!=null&&typeof b=="object")for(var e in b)bY(a+"["+e+"]",b[e],c,d);else d(a,b)}function bX(a,c,d,e,f,g){f=f||c.dataTypes[0],g=g||{},g[f]=!0;var h=a[f],i=0,j=h?h.length:0,k=a===bR,l;for(;i<j&&(k||!l);i++)l=h[i](c,d,e),typeof l=="string"&&(!k||g[l]?l=b:(c.dataTypes.unshift(l),l=bX(a,c,d,e,l,g)));(k||!l)&&!g["*"]&&(l=bX(a,c,d,e,"*",g));return l}function bW(a){return function(b,c){typeof b!="string"&&(c=b,b="*");if(f.isFunction(c)){var d=b.toLowerCase().split(bN),e=0,g=d.length,h,i,j;for(;e<g;e++)h=d[e],j=/^\+/.test(h),j&&(h=h.substr(1)||"*"),i=a[h]=a[h]||[],i[j?"unshift":"push"](c)}}}function bA(a,b,c){var d=b==="width"?a.offsetWidth:a.offsetHeight,e=b==="width"?bv:bw;if(d>0){c!=="border"&&f.each(e,function(){c||(d-=parseFloat(f.css(a,"padding"+this))||0),c==="margin"?d+=parseFloat(f.css(a,c+this))||0:d-=parseFloat(f.css(a,"border"+this+"Width"))||0});return d+"px"}d=bx(a,b,b);if(d<0||d==null)d=a.style[b]||0;d=parseFloat(d)||0,c&&f.each(e,function(){d+=parseFloat(f.css(a,"padding"+this))||0,c!=="padding"&&(d+=parseFloat(f.css(a,"border"+this+"Width"))||0),c==="margin"&&(d+=parseFloat(f.css(a,c+this))||0)});return d+"px"}function bm(a,b){b.src?f.ajax({url:b.src,async:!1,dataType:"script"}):f.globalEval((b.text||b.textContent||b.innerHTML||"").replace(be,"/*$0*/")),b.parentNode&&b.parentNode.removeChild(b)}function bl(a){f.nodeName(a,"input")?bk(a):"getElementsByTagName"in a&&f.grep(a.getElementsByTagName("input"),bk)}function bk(a){if(a.type==="checkbox"||a.type==="radio")a.defaultChecked=a.checked}function bj(a){return"getElementsByTagName"in a?a.getElementsByTagName("*"):"querySelectorAll"in a?a.querySelectorAll("*"):[]}function bi(a,b){var c;if(b.nodeType===1){b.clearAttributes&&b.clearAttributes(),b.mergeAttributes&&b.mergeAttributes(a),c=b.nodeName.toLowerCase();if(c==="object")b.outerHTML=a.outerHTML;else if(c!=="input"||a.type!=="checkbox"&&a.type!=="radio"){if(c==="option")b.selected=a.defaultSelected;else if(c==="input"||c==="textarea")b.defaultValue=a.defaultValue}else a.checked&&(b.defaultChecked=b.checked=a.checked),b.value!==a.value&&(b.value=a.value);b.removeAttribute(f.expando)}}function bh(a,b){if(b.nodeType===1&&!!f.hasData(a)){var c=f.expando,d=f.data(a),e=f.data(b,d);if(d=d[c]){var g=d.events;e=e[c]=f.extend({},d);if(g){delete e.handle,e.events={};for(var h in g)for(var i=0,j=g[h].length;i<j;i++)f.event.add(b,h+(g[h][i].namespace?".":"")+g[h][i].namespace,g[h][i],g[h][i].data)}}}}function bg(a,b){return f.nodeName(a,"table")?a.getElementsByTagName("tbody")[0]||a.appendChild(a.ownerDocument.createElement("tbody")):a}function W(a,b,c){b=b||0;if(f.isFunction(b))return f.grep(a,function(a,d){var e=!!b.call(a,d,a);return e===c});if(b.nodeType)return f.grep(a,function(a,d){return a===b===c});if(typeof b=="string"){var d=f.grep(a,function(a){return a.nodeType===1});if(R.test(b))return f.filter(b,d,!c);b=f.filter(b,d)}return f.grep(a,function(a,d){return f.inArray(a,b)>=0===c})}function V(a){return!a||!a.parentNode||a.parentNode.nodeType===11}function N(a,b){return(a&&a!=="*"?a+".":"")+b.replace(z,"`").replace(A,"&")}function M(a){var b,c,d,e,g,h,i,j,k,l,m,n,o,p=[],q=[],r=f._data(this,"events");if(!(a.liveFired===this||!r||!r.live||a.target.disabled||a.button&&a.type==="click")){a.namespace&&(n=new RegExp("(^|\\.)"+a.namespace.split(".").join("\\.(?:.*\\.)?")+"(\\.|$)")),a.liveFired=this;var s=r.live.slice(0);for(i=0;i<s.length;i++)g=s[i],g.origType.replace(x,"")===a.type?q.push(g.selector):s.splice(i--,1);e=f(a.target).closest(q,a.currentTarget);for(j=0,k=e.length;j<k;j++){m=e[j];for(i=0;i<s.length;i++){g=s[i];if(m.selector===g.selector&&(!n||n.test(g.namespace))&&!m.elem.disabled){h=m.elem,d=null;if(g.preType==="mouseenter"||g.preType==="mouseleave")a.type=g.preType,d=f(a.relatedTarget).closest(g.selector)[0],d&&f.contains(h,d)&&(d=h);(!d||d!==h)&&p.push({elem:h,handleObj:g,level:m.level})}}}for(j=0,k=p.length;j<k;j++){e=p[j];if(c&&e.level>c)break;a.currentTarget=e.elem,a.data=e.handleObj.data,a.handleObj=e.handleObj,o=e.handleObj.origHandler.apply(e.elem,arguments);if(o===!1||a.isPropagationStopped()){c=e.level,o===!1&&(b=!1);if(a.isImmediatePropagationStopped())break}}return b}}function K(a,c,d){var e=f.extend({},d[0]);e.type=a,e.originalEvent={},e.liveFired=b,f.event.handle.call(c,e),e.isDefaultPrevented()&&d[0].preventDefault()}function E(){return!0}function D(){return!1}function m(a,c,d){var e=c+"defer",g=c+"queue",h=c+"mark",i=f.data(a,e,b,!0);i&&(d==="queue"||!f.data(a,g,b,!0))&&(d==="mark"||!f.data(a,h,b,!0))&&setTimeout(function(){!f.data(a,g,b,!0)&&!f.data(a,h,b,!0)&&(f.removeData(a,e,!0),i.resolve())},0)}function l(a){for(var b in a)if(b!=="toJSON")return!1;return!0}function k(a,c,d){if(d===b&&a.nodeType===1){var e="data-"+c.replace(j,"$1-$2").toLowerCase();d=a.getAttribute(e);if(typeof d=="string"){try{d=d==="true"?!0:d==="false"?!1:d==="null"?null:f.isNaN(d)?i.test(d)?f.parseJSON(d):d:parseFloat(d)}catch(g){}f.data(a,c,d)}else d=b}return d}var c=a.document,d=a.navigator,e=a.location,f=function(){function J(){if(!e.isReady){try{c.documentElement.doScroll("left")}catch(a){setTimeout(J,1);return}e.ready()}}var e=function(a,b){return new e.fn.init(a,b,h)},f=a.jQuery,g=a.$,h,i=/^(?:[^<]*(<[\w\W]+>)[^>]*$|#([\w\-]*)$)/,j=/\S/,k=/^\s+/,l=/\s+$/,m=/\d/,n=/^<(\w+)\s*\/?>(?:<\/\1>)?$/,o=/^[\],:{}\s]*$/,p=/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g,q=/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g,r=/(?:^|:|,)(?:\s*\[)+/g,s=/(webkit)[ \/]([\w.]+)/,t=/(opera)(?:.*version)?[ \/]([\w.]+)/,u=/(msie) ([\w.]+)/,v=/(mozilla)(?:.*? rv:([\w.]+))?/,w=/-([a-z])/ig,x=function(a,b){return b.toUpperCase()},y=d.userAgent,z,A,B,C=Object.prototype.toString,D=Object.prototype.hasOwnProperty,E=Array.prototype.push,F=Array.prototype.slice,G=String.prototype.trim,H=Array.prototype.indexOf,I={};e.fn=e.prototype={constructor:e,init:function(a,d,f){var g,h,j,k;if(!a)return this;if(a.nodeType){this.context=this[0]=a,this.length=1;return this}if(a==="body"&&!d&&c.body){this.context=c,this[0]=c.body,this.selector=a,this.length=1;return this}if(typeof a=="string"){a.charAt(0)!=="<"||a.charAt(a.length-1)!==">"||a.length<3?g=i.exec(a):g=[null,a,null];if(g&&(g[1]||!d)){if(g[1]){d=d instanceof e?d[0]:d,k=d?d.ownerDocument||d:c,j=n.exec(a),j?e.isPlainObject(d)?(a=[c.createElement(j[1])],e.fn.attr.call(a,d,!0)):a=[k.createElement(j[1])]:(j=e.buildFragment([g[1]],[k]),a=(j.cacheable?e.clone(j.fragment):j.fragment).childNodes);return e.merge(this,a)}h=c.getElementById(g[2]);if(h&&h.parentNode){if(h.id!==g[2])return f.find(a);this.length=1,this[0]=h}this.context=c,this.selector=a;return this}return!d||d.jquery?(d||f).find(a):this.constructor(d).find(a)}if(e.isFunction(a))return f.ready(a);a.selector!==b&&(this.selector=a.selector,this.context=a.context);return e.makeArray(a,this)},selector:"",jquery:"1.6.2",length:0,size:function(){return this.length},toArray:function(){return F.call(this,0)},get:function(a){return a==null?this.toArray():a<0?this[this.length+a]:this[a]},pushStack:function(a,b,c){var d=this.constructor();e.isArray(a)?E.apply(d,a):e.merge(d,a),d.prevObject=this,d.context=this.context,b==="find"?d.selector=this.selector+(this.selector?" ":"")+c:b&&(d.selector=this.selector+"."+b+"("+c+")");return d},each:function(a,b){return e.each(this,a,b)},ready:function(a){e.bindReady(),A.done(a);return this},eq:function(a){return a===-1?this.slice(a):this.slice(a,+a+1)},first:function(){return this.eq(0)},last:function(){return this.eq(-1)},slice:function(){return this.pushStack(F.apply(this,arguments),"slice",F.call(arguments).join(","))},map:function(a){return this.pushStack(e.map(this,function(b,c){return a.call(b,c,b)}))},end:function(){return this.prevObject||this.constructor(null)},push:E,sort:[].sort,splice:[].splice},e.fn.init.prototype=e.fn,e.extend=e.fn.extend=function(){var a,c,d,f,g,h,i=arguments[0]||{},j=1,k=arguments.length,l=!1;typeof i=="boolean"&&(l=i,i=arguments[1]||{},j=2),typeof i!="object"&&!e.isFunction(i)&&(i={}),k===j&&(i=this,--j);for(;j<k;j++)if((a=arguments[j])!=null)for(c in a){d=i[c],f=a[c];if(i===f)continue;l&&f&&(e.isPlainObject(f)||(g=e.isArray(f)))?(g?(g=!1,h=d&&e.isArray(d)?d:[]):h=d&&e.isPlainObject(d)?d:{},i[c]=e.extend(l,h,f)):f!==b&&(i[c]=f)}return i},e.extend({noConflict:function(b){a.$===e&&(a.$=g),b&&a.jQuery===e&&(a.jQuery=f);return e},isReady:!1,readyWait:1,holdReady:function(a){a?e.readyWait++:e.ready(!0)},ready:function(a){if(a===!0&&!--e.readyWait||a!==!0&&!e.isReady){if(!c.body)return setTimeout(e.ready,1);e.isReady=!0;if(a!==!0&&--e.readyWait>0)return;A.resolveWith(c,[e]),e.fn.trigger&&e(c).trigger("ready").unbind("ready")}},bindReady:function(){if(!A){A=e._Deferred();if(c.readyState==="complete")return setTimeout(e.ready,1);if(c.addEventListener)c.addEventListener("DOMContentLoaded",B,!1),a.addEventListener("load",e.ready,!1);else if(c.attachEvent){c.attachEvent("onreadystatechange",B),a.attachEvent("onload",e.ready);var b=!1;try{b=a.frameElement==null}catch(d){}c.documentElement.doScroll&&b&&J()}}},isFunction:function(a){return e.type(a)==="function"},isArray:Array.isArray||function(a){return e.type(a)==="array"},isWindow:function(a){return a&&typeof a=="object"&&"setInterval"in a},isNaN:function(a){return a==null||!m.test(a)||isNaN(a)},type:function(a){return a==null?String(a):I[C.call(a)]||"object"},isPlainObject:function(a){if(!a||e.type(a)!=="object"||a.nodeType||e.isWindow(a))return!1;if(a.constructor&&!D.call(a,"constructor")&&!D.call(a.constructor.prototype,"isPrototypeOf"))return!1;var c;for(c in a);return c===b||D.call(a,c)},isEmptyObject:function(a){for(var b in a)return!1;return!0},error:function(a){throw a},parseJSON:function(b){if(typeof b!="string"||!b)return null;b=e.trim(b);if(a.JSON&&a.JSON.parse)return a.JSON.parse(b);if(o.test(b.replace(p,"@").replace(q,"]").replace(r,"")))return(new Function("return "+b))();e.error("Invalid JSON: "+b)},parseXML:function(b,c,d){a.DOMParser?(d=new DOMParser,c=d.parseFromString(b,"text/xml")):(c=new ActiveXObject("Microsoft.XMLDOM"),c.async="false",c.loadXML(b)),d=c.documentElement,(!d||!d.nodeName||d.nodeName==="parsererror")&&e.error("Invalid XML: "+b);return c},noop:function(){},globalEval:function(b){b&&j.test(b)&&(a.execScript||function(b){a.eval.call(a,b)})(b)},camelCase:function(a){return a.replace(w,x)},nodeName:function(a,b){return a.nodeName&&a.nodeName.toUpperCase()===b.toUpperCase()},each:function(a,c,d){var f,g=0,h=a.length,i=h===b||e.isFunction(a);if(d){if(i){for(f in a)if(c.apply(a[f],d)===!1)break}else for(;g<h;)if(c.apply(a[g++],d)===!1)break}else if(i){for(f in a)if(c.call(a[f],f,a[f])===!1)break}else for(;g<h;)if(c.call(a[g],g,a[g++])===!1)break;return a},trim:G?function(a){return a==null?"":G.call(a)}:function(a){return a==null?"":(a+"").replace(k,"").replace(l,"")},makeArray:function(a,b){var c=b||[];if(a!=null){var d=e.type(a);a.length==null||d==="string"||d==="function"||d==="regexp"||e.isWindow(a)?E.call(c,a):e.merge(c,a)}return c},inArray:function(a,b){if(H)return H.call(b,a);for(var c=0,d=b.length;c<d;c++)if(b[c]===a)return c;return-1},merge:function(a,c){var d=a.length,e=0;if(typeof c.length=="number")for(var f=c.length;e<f;e++)a[d++]=c[e];else while(c[e]!==b)a[d++]=c[e++];a.length=d;return a},grep:function(a,b,c){var d=[],e;c=!!c;for(var f=0,g=a.length;f<g;f++)e=!!b(a[f],f),c!==e&&d.push(a[f]);return d},map:function(a,c,d){var f,g,h=[],i=0,j=a.length,k=a instanceof e||j!==b&&typeof j=="number"&&(j>0&&a[0]&&a[j-1]||j===0||e.isArray(a));if(k)for(;i<j;i++)f=c(a[i],i,d),f!=null&&(h[h.length]=f);else for(g in a)f=c(a[g],g,d),f!=null&&(h[h.length]=f);return h.concat.apply([],h)},guid:1,proxy:function(a,c){if(typeof c=="string"){var d=a[c];c=a,a=d}if(!e.isFunction(a))return b;var f=F.call(arguments,2),g=function(){return a.apply(c,f.concat(F.call(arguments)))};g.guid=a.guid=a.guid||g.guid||e.guid++;return g},access:function(a,c,d,f,g,h){var i=a.length;if(typeof c=="object"){for(var j in c)e.access(a,j,c[j],f,g,d);return a}if(d!==b){f=!h&&f&&e.isFunction(d);for(var k=0;k<i;k++)g(a[k],c,f?d.call(a[k],k,g(a[k],c)):d,h);return a}return i?g(a[0],c):b},now:function(){return(new Date).getTime()},uaMatch:function(a){a=a.toLowerCase();var b=s.exec(a)||t.exec(a)||u.exec(a)||a.indexOf("compatible")<0&&v.exec(a)||[];return{browser:b[1]||"",version:b[2]||"0"}},sub:function(){function a(b,c){return new a.fn.init(b,c)}e.extend(!0,a,this),a.superclass=this,a.fn=a.prototype=this(),a.fn.constructor=a,a.sub=this.sub,a.fn.init=function(d,f){f&&f instanceof e&&!(f instanceof a)&&(f=a(f));return e.fn.init.call(this,d,f,b)},a.fn.init.prototype=a.fn;var b=a(c);return a},browser:{}}),e.each("Boolean Number String Function Array Date RegExp Object".split(" "),function(a,b){I["[object "+b+"]"]=b.toLowerCase()}),z=e.uaMatch(y),z.browser&&(e.browser[z.browser]=!0,e.browser.version=z.version),e.browser.webkit&&(e.browser.safari=!0),j.test(" ")&&(k=/^[\s\xA0]+/,l=/[\s\xA0]+$/),h=e(c),c.addEventListener?B=function(){c.removeEventListener("DOMContentLoaded",B,!1),e.ready()}:c.attachEvent&&(B=function(){c.readyState==="complete"&&(c.detachEvent("onreadystatechange",B),e.ready())});return e}(),g="done fail isResolved isRejected promise then always pipe".split(" "),h=[].slice;f.extend({_Deferred:function(){var a=[],b,c,d,e={done:function(){if(!d){var c=arguments,g,h,i,j,k;b&&(k=b,b=0);for(g=0,h=c.length;g<h;g++)i=c[g],j=f.type(i),j==="array"?e.done.apply(e,i):j==="function"&&a.push(i);k&&e.resolveWith(k[0],k[1])}return this},resolveWith:function(e,f){if(!d&&!b&&!c){f=f||[],c=1;try{while(a[0])a.shift().apply(e,f)}finally{b=[e,f],c=0}}return this},resolve:function(){e.resolveWith(this,arguments);return this},isResolved:function(){return!!c||!!b},cancel:function(){d=1,a=[];return this}};return e},Deferred:function(a){var b=f._Deferred(),c=f._Deferred(),d;f.extend(b,{then:function(a,c){b.done(a).fail(c);return this},always:function(){return b.done.apply(b,arguments).fail.apply(this,arguments)},fail:c.done,rejectWith:c.resolveWith,reject:c.resolve,isRejected:c.isResolved,pipe:function(a,c){return f.Deferred(function(d){f.each({done:[a,"resolve"],fail:[c,"reject"]},function(a,c){var e=c[0],g=c[1],h;f.isFunction(e)?b[a](function(){h=e.apply(this,arguments),h&&f.isFunction(h.promise)?h.promise().then(d.resolve,d.reject):d[g](h)}):b[a](d[g])})}).promise()},promise:function(a){if(a==null){if(d)return d;d=a={}}var c=g.length;while(c--)a[g[c]]=b[g[c]];return a}}),b.done(c.cancel).fail(b.cancel),delete b.cancel,a&&a.call(b,b);return b},when:function(a){function i(a){return function(c){b[a]=arguments.length>1?h.call(arguments,0):c,--e||g.resolveWith(g,h.call(b,0))}}var b=arguments,c=0,d=b.length,e=d,g=d<=1&&a&&f.isFunction(a.promise)?a:f.Deferred();if(d>1){for(;c<d;c++)b[c]&&f.isFunction(b[c].promise)?b[c].promise().then(i(c),g.reject):--e;e||g.resolveWith(g,b)}else g!==a&&g.resolveWith(g,d?[a]:[]);return g.promise()}}),f.support=function(){var a=c.createElement("div"),b=c.documentElement,d,e,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u;a.setAttribute("className","t"),a.innerHTML="   <link/><table></table><a href='/a' style='top:1px;float:left;opacity:.55;'>a</a><input type='checkbox'/>",d=a.getElementsByTagName("*"),e=a.getElementsByTagName("a")[0];if(!d||!d.length||!e)return{};g=c.createElement("select"),h=g.appendChild(c.createElement("option")),i=a.getElementsByTagName("input")[0],k={leadingWhitespace:a.firstChild.nodeType===3,tbody:!a.getElementsByTagName("tbody").length,htmlSerialize:!!a.getElementsByTagName("link").length,style:/top/.test(e.getAttribute("style")),hrefNormalized:e.getAttribute("href")==="/a",opacity:/^0.55$/.test(e.style.opacity),cssFloat:!!e.style.cssFloat,checkOn:i.value==="on",optSelected:h.selected,getSetAttribute:a.className!=="t",submitBubbles:!0,changeBubbles:!0,focusinBubbles:!1,deleteExpando:!0,noCloneEvent:!0,inlineBlockNeedsLayout:!1,shrinkWrapBlocks:!1,reliableMarginRight:!0},i.checked=!0,k.noCloneChecked=i.cloneNode(!0).checked,g.disabled=!0,k.optDisabled=!h.disabled;try{delete a.test}catch(v){k.deleteExpando=!1}!a.addEventListener&&a.attachEvent&&a.fireEvent&&(a.attachEvent("onclick",function(){k.noCloneEvent=!1}),a.cloneNode(!0).fireEvent("onclick")),i=c.createElement("input"),i.value="t",i.setAttribute("type","radio"),k.radioValue=i.value==="t",i.setAttribute("checked","checked"),a.appendChild(i),l=c.createDocumentFragment(),l.appendChild(a.firstChild),k.checkClone=l.cloneNode(!0).cloneNode(!0).lastChild.checked,a.innerHTML="",a.style.width=a.style.paddingLeft="1px",m=c.getElementsByTagName("body")[0],o=c.createElement(m?"div":"body"),p={visibility:"hidden",width:0,height:0,border:0,margin:0},m&&f.extend(p,{position:"absolute",left:-1e3,top:-1e3});for(t in p)o.style[t]=p[t];o.appendChild(a),n=m||b,n.insertBefore(o,n.firstChild),k.appendChecked=i.checked,k.boxModel=a.offsetWidth===2,"zoom"in a.style&&(a.style.display="inline",a.style.zoom=1,k.inlineBlockNeedsLayout=a.offsetWidth===2,a.style.display="",a.innerHTML="<div style='width:4px;'></div>",k.shrinkWrapBlocks=a.offsetWidth!==2),a.innerHTML="<table><tr><td style='padding:0;border:0;display:none'></td><td>t</td></tr></table>",q=a.getElementsByTagName("td"),u=q[0].offsetHeight===0,q[0].style.display="",q[1].style.display="none",k.reliableHiddenOffsets=u&&q[0].offsetHeight===0,a.innerHTML="",c.defaultView&&c.defaultView.getComputedStyle&&(j=c.createElement("div"),j.style.width="0",j.style.marginRight="0",a.appendChild(j),k.reliableMarginRight=(parseInt((c.defaultView.getComputedStyle(j,null)||{marginRight:0}).marginRight,10)||0)===0),o.innerHTML="",n.removeChild(o);if(a.attachEvent)for(t in{submit:1,change:1,focusin:1})s="on"+t,u=s in a,u||(a.setAttribute(s,"return;"),u=typeof a[s]=="function"),k[t+"Bubbles"]=u;o=l=g=h=m=j=a=i=null;return k}(),f.boxModel=f.support.boxModel;var i=/^(?:\{.*\}|\[.*\])$/,j=/([a-z])([A-Z])/g;f.extend({cache:{},uuid:0,expando:"jQuery"+(f.fn.jquery+Math.random()).replace(/\D/g,""),noData:{embed:!0,object:"clsid:D27CDB6E-AE6D-11cf-96B8-444553540000",applet:!0},hasData:function(a){a=a.nodeType?f.cache[a[f.expando]]:a[f.expando];return!!a&&!l(a)},data:function(a,c,d,e){if(!!f.acceptData(a)){var g=f.expando,h=typeof c=="string",i,j=a.nodeType,k=j?f.cache:a,l=j?a[f.expando]:a[f.expando]&&f.expando;if((!l||e&&l&&!k[l][g])&&h&&d===b)return;l||(j?a[f.expando]=l=++f.uuid:l=f.expando),k[l]||(k[l]={},j||(k[l].toJSON=f.noop));if(typeof c=="object"||typeof c=="function")e?k[l][g]=f.extend(k[l][g],c):k[l]=f.extend(k[l],c);i=k[l],e&&(i[g]||(i[g]={}),i=i[g]),d!==b&&(i[f.camelCase(c)]=d);if(c==="events"&&!i[c])return i[g]&&i[g].events;return h?i[f.camelCase(c)]||i[c]:i}},removeData:function(b,c,d){if(!!f.acceptData(b)){var e=f.expando,g=b.nodeType,h=g?f.cache:b,i=g?b[f.expando]:f.expando;if(!h[i])return;if(c){var j=d?h[i][e]:h[i];if(j){delete j[c];if(!l(j))return}}if(d){delete h[i][e];if(!l(h[i]))return}var k=h[i][e];f.support.deleteExpando||h!=a?delete h[i]:h[i]=null,k?(h[i]={},g||(h[i].toJSON=f.noop),h[i][e]=k):g&&(f.support.deleteExpando?delete b[f.expando]:b.removeAttribute?b.removeAttribute(f.expando):b[f.expando]=null)}},_data:function(a,b,c){return f.data(a,b,c,!0)},acceptData:function(a){if(a.nodeName){var b=f.noData[a.nodeName.toLowerCase()];if(b)return b!==!0&&a.getAttribute("classid")===b}return!0}}),f.fn.extend({data:function(a,c){var d=null;if(typeof a=="undefined"){if(this.length){d=f.data(this[0]);if(this[0].nodeType===1){var e=this[0].attributes,g;for(var h=0,i=e.length;h<i;h++)g=e[h].name,g.indexOf("data-")===0&&(g=f.camelCase(g.substring(5)),k(this[0],g,d[g]))}}return d}if(typeof a=="object")return this.each(function(){f.data(this,a)});var j=a.split(".");j[1]=j[1]?"."+j[1]:"";if(c===b){d=this.triggerHandler("getData"+j[1]+"!",[j[0]]),d===b&&this.length&&(d=f.data(this[0],a),d=k(this[0],a,d));return d===b&&j[1]?this.data(j[0]):d}return this.each(function(){var b=f(this),d=[j[0],c];b.triggerHandler("setData"+j[1]+"!",d),f.data(this,a,c),b.triggerHandler("changeData"+j[1]+"!",d)})},removeData:function(a){return this.each(function(){f.removeData(this,a)})}}),f.extend({_mark:function(a,c){a&&(c=(c||"fx")+"mark",f.data(a,c,(f.data(a,c,b,!0)||0)+1,!0))},_unmark:function(a,c,d){a!==!0&&(d=c,c=a,a=!1);if(c){d=d||"fx";var e=d+"mark",g=a?0:(f.data(c,e,b,!0)||1)-1;g?f.data(c,e,g,!0):(f.removeData(c,e,!0),m(c,d,"mark"))}},queue:function(a,c,d){if(a){c=(c||"fx")+"queue";var e=f.data(a,c,b,!0);d&&(!e||f.isArray(d)?e=f.data(a,c,f.makeArray(d),!0):e.push(d));return e||[]}},dequeue:function(a,b){b=b||"fx";var c=f.queue(a,b),d=c.shift(),e;d==="inprogress"&&(d=c.shift()),d&&(b==="fx"&&c.unshift("inprogress"),d.call(a,function(){f.dequeue(a,b)})),c.length||(f.removeData(a,b+"queue",!0),m(a,b,"queue"))}}),f.fn.extend({queue:function(a,c){typeof a!="string"&&(c=a,a="fx");if(c===b)return f.queue(this[0],a);return this.each(function(){var b=f.queue(this,a,c);a==="fx"&&b[0]!=="inprogress"&&f.dequeue(this,a)})},dequeue:function(a){return this.each(function(){f.dequeue(this,a)})},delay:function(a,b){a=f.fx?f.fx.speeds[a]||a:a,b=b||"fx";return this.queue(b,function(){var c=this;setTimeout(function(){f.dequeue(c,b)},a)})},clearQueue:function(a){return this.queue(a||"fx",[])},promise:function(a,c){function m(){--h||d.resolveWith(e,[e])}typeof a!="string"&&(c=a,a=b),a=a||"fx";var d=f.Deferred(),e=this,g=e.length,h=1,i=a+"defer",j=a+"queue",k=a+"mark",l;while(g--)if(l=f.data(e[g],i,b,!0)||(f.data(e[g],j,b,!0)||f.data(e[g],k,b,!0))&&f.data(e[g],i,f._Deferred(),!0))h++,l.done(m);m();return d.promise()}});var n=/[\n\t\r]/g,o=/\s+/,p=/\r/g,q=/^(?:button|input)$/i,r=/^(?:button|input|object|select|textarea)$/i,s=/^a(?:rea)?$/i,t=/^(?:autofocus|autoplay|async|checked|controls|defer|disabled|hidden|loop|multiple|open|readonly|required|scoped|selected)$/i,u=/\:|^on/,v,w;f.fn.extend({attr:function(a,b){return f.access(this,a,b,!0,f.attr)},removeAttr:function(a){return this.each(function(){f.removeAttr(this,a)})},prop:function(a,b){return f.access(this,a,b,!0,f.prop)},removeProp:function(a){a=f.propFix[a]||a;return this.each(function(){try{this[a]=b,delete this[a]}catch(c){}})},addClass:function(a){var b,c,d,e,g,h,i;if(f.isFunction(a))return this.each(function(b){f(this).addClass(a.call(this,b,this.className))});if(a&&typeof a=="string"){b=a.split(o);for(c=0,d=this.length;c<d;c++){e=this[c];if(e.nodeType===1)if(!e.className&&b.length===1)e.className=a;else{g=" "+e.className+" ";for(h=0,i=b.length;h<i;h++)~g.indexOf(" "+b[h]+" ")||(g+=b[h]+" ");e.className=f.trim(g)}}}return this},removeClass:function(a){var c,d,e,g,h,i,j;if(f.isFunction(a))return this.each(function(b){f(this).removeClass(a.call(this,b,this.className))});if(a&&typeof a=="string"||a===b){c=(a||"").split(o);for(d=0,e=this.length;d<e;d++){g=this[d];if(g.nodeType===1&&g.className)if(a){h=(" "+g.className+" ").replace(n," ");for(i=0,j=c.length;i<j;i++)h=h.replace(" "+c[i]+" "," ");g.className=f.trim(h)}else g.className=""}}return this},toggleClass:function(a,b){var c=typeof a,d=typeof b=="boolean";if(f.isFunction(a))return this.each(function(c){f(this).toggleClass(a.call(this,c,this.className,b),b)});return this.each(function(){if(c==="string"){var e,g=0,h=f(this),i=b,j=a.split(o);while(e=j[g++])i=d?i:!h.hasClass(e),h[i?"addClass":"removeClass"](e)}else if(c==="undefined"||c==="boolean")this.className&&f._data(this,"__className__",this.className),this.className=this.className||a===!1?"":f._data(this,"__className__")||""})},hasClass:function(a){var b=" "+a+" ";for(var c=0,d=this.length;c<d;c++)if((" "+this[c].className+" ").replace(n," ").indexOf(b)>-1)return!0;return!1},val:function(a){var c,d,e=this[0];if(!arguments.length){if(e){c=f.valHooks[e.nodeName.toLowerCase()]||f.valHooks[e.type];if(c&&"get"in c&&(d=c.get(e,"value"))!==b)return d;d=e.value;return typeof d=="string"?d.replace(p,""):d==null?"":d}return b}var g=f.isFunction(a);return this.each(function(d){var e=f(this),h;if(this.nodeType===1){g?h=a.call(this,d,e.val()):h=a,h==null?h="":typeof h=="number"?h+="":f.isArray(h)&&(h=f.map(h,function(a){return a==null?"":a+""})),c=f.valHooks[this.nodeName.toLowerCase()]||f.valHooks[this.type];if(!c||!("set"in c)||c.set(this,h,"value")===b)this.value=h}})}}),f.extend({valHooks:{option:{get:function(a){var b=a.attributes.value;return!b||b.specified?a.value:a.text}},select:{get:function(a){var b,c=a.selectedIndex,d=[],e=a.options,g=a.type==="select-one";if(c<0)return null;for(var h=g?c:0,i=g?c+1:e.length;h<i;h++){var j=e[h];if(j.selected&&(f.support.optDisabled?!j.disabled:j.getAttribute("disabled")===null)&&(!j.parentNode.disabled||!f.nodeName(j.parentNode,"optgroup"))){b=f(j).val();if(g)return b;d.push(b)}}if(g&&!d.length&&e.length)return f(e[c]).val();return d},set:function(a,b){var c=f.makeArray(b);f(a).find("option").each(function(){this.selected=f.inArray(f(this).val(),c)>=0}),c.length||(a.selectedIndex=-1);return c}}},attrFn:{val:!0,css:!0,html:!0,text:!0,data:!0,width:!0,height:!0,offset:!0},attrFix:{tabindex:"tabIndex"},attr:function(a,c,d,e){var g=a.nodeType;if(!a||g===3||g===8||g===2)return b;if(e&&c in f.attrFn)return f(a)[c](d);if(!("getAttribute"in a))return f.prop(a,c,d);var h,i,j=g!==1||!f.isXMLDoc(a);j&&(c=f.attrFix[c]||c,i=f.attrHooks[c],i||(t.test(c)?i=w:v&&c!=="className"&&(f.nodeName(a,"form")||u.test(c))&&(i=v)));if(d!==b){if(d===null){f.removeAttr(a,c);return b}if(i&&"set"in i&&j&&(h=i.set(a,d,c))!==b)return h;a.setAttribute(c,""+d);return d}if(i&&"get"in i&&j&&(h=i.get(a,c))!==null)return h;h=a.getAttribute(c);return h===null?b:h},removeAttr:function(a,b){var c;a.nodeType===1&&(b=f.attrFix[b]||b,f.support.getSetAttribute?a.removeAttribute(b):(f.attr(a,b,""),a.removeAttributeNode(a.getAttributeNode(b))),t.test(b)&&(c=f.propFix[b]||b)in a&&(a[c]=!1))},attrHooks:{type:{set:function(a,b){if(q.test(a.nodeName)&&a.parentNode)f.error("type property can't be changed");else if(!f.support.radioValue&&b==="radio"&&f.nodeName(a,"input")){var c=a.value;a.setAttribute("type",b),c&&(a.value=c);return b}}},tabIndex:{get:function(a){var c=a.getAttributeNode("tabIndex");return c&&c.specified?parseInt(c.value,10):r.test(a.nodeName)||s.test(a.nodeName)&&a.href?0:b}},value:{get:function(a,b){if(v&&f.nodeName(a,"button"))return v.get(a,b);return b in a?a.value:null},set:function(a,b,c){if(v&&f.nodeName(a,"button"))return v.set(a,b,c);a.value=b}}},propFix:{tabindex:"tabIndex",readonly:"readOnly","for":"htmlFor","class":"className",maxlength:"maxLength",cellspacing:"cellSpacing",cellpadding:"cellPadding",rowspan:"rowSpan",colspan:"colSpan",usemap:"useMap",frameborder:"frameBorder",contenteditable:"contentEditable"},prop:function(a,c,d){var e=a.nodeType;if(!a||e===3||e===8||e===2)return b;var g,h,i=e!==1||!f.isXMLDoc(a);i&&(c=f.propFix[c]||c,h=f.propHooks[c]);return d!==b?h&&"set"in h&&(g=h.set(a,d,c))!==b?g:a[c]=d:h&&"get"in h&&(g=h.get(a,c))!==b?g:a[c]},propHooks:{}}),w={get:function(a,c){return f.prop(a,c)?c.toLowerCase():b},set:function(a,b,c){var d;b===!1?f.removeAttr(a,c):(d=f.propFix[c]||c,d in a&&(a[d]=!0),a.setAttribute(c,c.toLowerCase()));return c}},f.support.getSetAttribute||(f.attrFix=f.propFix,v=f.attrHooks.name=f.attrHooks.title=f.valHooks.button={get:function(a,c){var d;d=a.getAttributeNode(c);return d&&d.nodeValue!==""?d.nodeValue:b},set:function(a,b,c){var d=a.getAttributeNode(c);if(d){d.nodeValue=b;return b}}},f.each(["width","height"],function(a,b){f.attrHooks[b]=f.extend(f.attrHooks[b],{set:function(a,c){if(c===""){a.setAttribute(b,"auto");return c}}})})),f.support.hrefNormalized||f.each(["href","src","width","height"],function(a,c){f.attrHooks[c]=f.extend(f.attrHooks[c],{get:function(a){var d=a.getAttribute(c,2);return d===null?b:d}})}),f.support.style||(f.attrHooks.style={get:function(a){return a.style.cssText.toLowerCase()||b},set:function(a,b){return a.style.cssText=""+b}}),f.support.optSelected||(f.propHooks.selected=f.extend(f.propHooks.selected,{get:function(a){var b=a.parentNode;b&&(b.selectedIndex,b.parentNode&&b.parentNode.selectedIndex)}})),f.support.checkOn||f.each(["radio","checkbox"],function(){f.valHooks[this]={get:function(a){return a.getAttribute("value")===null?"on":a.value}}}),f.each(["radio","checkbox"],function(){f.valHooks[this]=f.extend(f.valHooks[this],{set:function(a,b){if(f.isArray(b))return a.checked=f.inArray(f(a).val(),b)>=0}})});var x=/\.(.*)$/,y=/^(?:textarea|input|select)$/i,z=/\./g,A=/ /g,B=/[^\w\s.|`]/g,C=function(a){return a.replace(B,"\\$&")};f.event={add:function(a,c,d,e){if(a.nodeType!==3&&a.nodeType!==8){if(d===!1)d=D;else if(!d)return;var g,h;d.handler&&(g=d,d=g.handler),d.guid||(d.guid=f.guid++);var i=f._data(a);if(!i)return;var j=i.events,k=i.handle;j||(i.events=j={}),k||(i.handle=k=function(a){return typeof f!="undefined"&&(!a||f.event.triggered!==a.type)?f.event.handle.apply(k.elem,arguments):b}),k.elem=a,c=c.split(" ");var l,m=0,n;while(l=c[m++]){h=g?f.extend({},g):{handler:d,data:e},l.indexOf(".")>-1?(n=l.split("."),l=n.shift(),h.namespace=n.slice(0).sort().join(".")):(n=[],h.namespace=""),h.type=l,h.guid||(h.guid=d.guid);var o=j[l],p=f.event.special[l]||{};if(!o){o=j[l]=[];if(!p.setup||p.setup.call(a,e,n,k)===!1)a.addEventListener?a.addEventListener(l,k,!1):a.attachEvent&&a.attachEvent("on"+l,k)}p.add&&(p.add.call(a,h),h.handler.guid||(h.handler.guid=d.guid)),o.push(h),f.event.global[l]=!0}a=null}},global:{},remove:function(a,c,d,e){if(a.nodeType!==3&&a.nodeType!==8){d===!1&&(d=D);var g,h,i,j,k=0,l,m,n,o,p,q,r,s=f.hasData(a)&&f._data(a),t=s&&s.events;if(!s||!t)return;c&&c.type&&(d=c.handler,c=c.type);if(!c||typeof c=="string"&&c.charAt(0)==="."){c=c||"";for(h in t)f.event.remove(a,h+c);return}c=c.split(" ");while(h=c[k++]){r=h,q=null,l=h.indexOf(".")<0,m=[],l||(m=h.split("."),h=m.shift(),n=new RegExp("(^|\\.)"+f.map(m.slice(0).sort(),C).join("\\.(?:.*\\.)?")+"(\\.|$)")),p=t[h];if(!p)continue;if(!d){for(j=0;j<p.length;j++){q=p[j];if(l||n.test(q.namespace))f.event.remove(a,r,q.handler,j),p.splice(j--,1)}continue}o=f.event.special[h]||{};for(j=e||0;j<p.length;j++){q=p[j];if(d.guid===q.guid){if(l||n.test(q.namespace))e==null&&p.splice(j--,1),o.remove&&o.remove.call(a,q);if(e!=null)break}}if(p.length===0||e!=null&&p.length===1)(!o.teardown||o.teardown.call(a,m)===!1)&&f.removeEvent(a,h,s.handle),g=null,delete t[h]}if(f.isEmptyObject(t)){var u=s.handle;u&&(u.elem=null),delete s.events,delete s.handle,f.isEmptyObject(s)&&f.removeData(a,b,!0)}}},customEvent:{getData:!0,setData:!0,changeData:!0},trigger:function(c,d,e,g){var h=c.type||c,i=[],j;h.indexOf("!")>=0&&(h=h.slice(0,-1),j=!0),h.indexOf(".")>=0&&(i=h.split("."),h=i.
shift(),i.sort());if(!!e&&!f.event.customEvent[h]||!!f.event.global[h]){c=typeof c=="object"?c[f.expando]?c:new f.Event(h,c):new f.Event(h),c.type=h,c.exclusive=j,c.namespace=i.join("."),c.namespace_re=new RegExp("(^|\\.)"+i.join("\\.(?:.*\\.)?")+"(\\.|$)");if(g||!e)c.preventDefault(),c.stopPropagation();if(!e){f.each(f.cache,function(){var a=f.expando,b=this[a];b&&b.events&&b.events[h]&&f.event.trigger(c,d,b.handle.elem)});return}if(e.nodeType===3||e.nodeType===8)return;c.result=b,c.target=e,d=d!=null?f.makeArray(d):[],d.unshift(c);var k=e,l=h.indexOf(":")<0?"on"+h:"";do{var m=f._data(k,"handle");c.currentTarget=k,m&&m.apply(k,d),l&&f.acceptData(k)&&k[l]&&k[l].apply(k,d)===!1&&(c.result=!1,c.preventDefault()),k=k.parentNode||k.ownerDocument||k===c.target.ownerDocument&&a}while(k&&!c.isPropagationStopped());if(!c.isDefaultPrevented()){var n,o=f.event.special[h]||{};if((!o._default||o._default.call(e.ownerDocument,c)===!1)&&(h!=="click"||!f.nodeName(e,"a"))&&f.acceptData(e)){try{l&&e[h]&&(n=e[l],n&&(e[l]=null),f.event.triggered=h,e[h]())}catch(p){}n&&(e[l]=n),f.event.triggered=b}}return c.result}},handle:function(c){c=f.event.fix(c||a.event);var d=((f._data(this,"events")||{})[c.type]||[]).slice(0),e=!c.exclusive&&!c.namespace,g=Array.prototype.slice.call(arguments,0);g[0]=c,c.currentTarget=this;for(var h=0,i=d.length;h<i;h++){var j=d[h];if(e||c.namespace_re.test(j.namespace)){c.handler=j.handler,c.data=j.data,c.handleObj=j;var k=j.handler.apply(this,g);k!==b&&(c.result=k,k===!1&&(c.preventDefault(),c.stopPropagation()));if(c.isImmediatePropagationStopped())break}}return c.result},props:"altKey attrChange attrName bubbles button cancelable charCode clientX clientY ctrlKey currentTarget data detail eventPhase fromElement handler keyCode layerX layerY metaKey newValue offsetX offsetY pageX pageY prevValue relatedNode relatedTarget screenX screenY shiftKey srcElement target toElement view wheelDelta which".split(" "),fix:function(a){if(a[f.expando])return a;var d=a;a=f.Event(d);for(var e=this.props.length,g;e;)g=this.props[--e],a[g]=d[g];a.target||(a.target=a.srcElement||c),a.target.nodeType===3&&(a.target=a.target.parentNode),!a.relatedTarget&&a.fromElement&&(a.relatedTarget=a.fromElement===a.target?a.toElement:a.fromElement);if(a.pageX==null&&a.clientX!=null){var h=a.target.ownerDocument||c,i=h.documentElement,j=h.body;a.pageX=a.clientX+(i&&i.scrollLeft||j&&j.scrollLeft||0)-(i&&i.clientLeft||j&&j.clientLeft||0),a.pageY=a.clientY+(i&&i.scrollTop||j&&j.scrollTop||0)-(i&&i.clientTop||j&&j.clientTop||0)}a.which==null&&(a.charCode!=null||a.keyCode!=null)&&(a.which=a.charCode!=null?a.charCode:a.keyCode),!a.metaKey&&a.ctrlKey&&(a.metaKey=a.ctrlKey),!a.which&&a.button!==b&&(a.which=a.button&1?1:a.button&2?3:a.button&4?2:0);return a},guid:1e8,proxy:f.proxy,special:{ready:{setup:f.bindReady,teardown:f.noop},live:{add:function(a){f.event.add(this,N(a.origType,a.selector),f.extend({},a,{handler:M,guid:a.handler.guid}))},remove:function(a){f.event.remove(this,N(a.origType,a.selector),a)}},beforeunload:{setup:function(a,b,c){f.isWindow(this)&&(this.onbeforeunload=c)},teardown:function(a,b){this.onbeforeunload===b&&(this.onbeforeunload=null)}}}},f.removeEvent=c.removeEventListener?function(a,b,c){a.removeEventListener&&a.removeEventListener(b,c,!1)}:function(a,b,c){a.detachEvent&&a.detachEvent("on"+b,c)},f.Event=function(a,b){if(!this.preventDefault)return new f.Event(a,b);a&&a.type?(this.originalEvent=a,this.type=a.type,this.isDefaultPrevented=a.defaultPrevented||a.returnValue===!1||a.getPreventDefault&&a.getPreventDefault()?E:D):this.type=a,b&&f.extend(this,b),this.timeStamp=f.now(),this[f.expando]=!0},f.Event.prototype={preventDefault:function(){this.isDefaultPrevented=E;var a=this.originalEvent;!a||(a.preventDefault?a.preventDefault():a.returnValue=!1)},stopPropagation:function(){this.isPropagationStopped=E;var a=this.originalEvent;!a||(a.stopPropagation&&a.stopPropagation(),a.cancelBubble=!0)},stopImmediatePropagation:function(){this.isImmediatePropagationStopped=E,this.stopPropagation()},isDefaultPrevented:D,isPropagationStopped:D,isImmediatePropagationStopped:D};var F=function(a){var b=a.relatedTarget,c=!1,d=a.type;a.type=a.data,b!==this&&(b&&(c=f.contains(this,b)),c||(f.event.handle.apply(this,arguments),a.type=d))},G=function(a){a.type=a.data,f.event.handle.apply(this,arguments)};f.each({mouseenter:"mouseover",mouseleave:"mouseout"},function(a,b){f.event.special[a]={setup:function(c){f.event.add(this,b,c&&c.selector?G:F,a)},teardown:function(a){f.event.remove(this,b,a&&a.selector?G:F)}}}),f.support.submitBubbles||(f.event.special.submit={setup:function(a,b){if(!f.nodeName(this,"form"))f.event.add(this,"click.specialSubmit",function(a){var b=a.target,c=b.type;(c==="submit"||c==="image")&&f(b).closest("form").length&&K("submit",this,arguments)}),f.event.add(this,"keypress.specialSubmit",function(a){var b=a.target,c=b.type;(c==="text"||c==="password")&&f(b).closest("form").length&&a.keyCode===13&&K("submit",this,arguments)});else return!1},teardown:function(a){f.event.remove(this,".specialSubmit")}});if(!f.support.changeBubbles){var H,I=function(a){var b=a.type,c=a.value;b==="radio"||b==="checkbox"?c=a.checked:b==="select-multiple"?c=a.selectedIndex>-1?f.map(a.options,function(a){return a.selected}).join("-"):"":f.nodeName(a,"select")&&(c=a.selectedIndex);return c},J=function(c){var d=c.target,e,g;if(!!y.test(d.nodeName)&&!d.readOnly){e=f._data(d,"_change_data"),g=I(d),(c.type!=="focusout"||d.type!=="radio")&&f._data(d,"_change_data",g);if(e===b||g===e)return;if(e!=null||g)c.type="change",c.liveFired=b,f.event.trigger(c,arguments[1],d)}};f.event.special.change={filters:{focusout:J,beforedeactivate:J,click:function(a){var b=a.target,c=f.nodeName(b,"input")?b.type:"";(c==="radio"||c==="checkbox"||f.nodeName(b,"select"))&&J.call(this,a)},keydown:function(a){var b=a.target,c=f.nodeName(b,"input")?b.type:"";(a.keyCode===13&&!f.nodeName(b,"textarea")||a.keyCode===32&&(c==="checkbox"||c==="radio")||c==="select-multiple")&&J.call(this,a)},beforeactivate:function(a){var b=a.target;f._data(b,"_change_data",I(b))}},setup:function(a,b){if(this.type==="file")return!1;for(var c in H)f.event.add(this,c+".specialChange",H[c]);return y.test(this.nodeName)},teardown:function(a){f.event.remove(this,".specialChange");return y.test(this.nodeName)}},H=f.event.special.change.filters,H.focus=H.beforeactivate}f.support.focusinBubbles||f.each({focus:"focusin",blur:"focusout"},function(a,b){function e(a){var c=f.event.fix(a);c.type=b,c.originalEvent={},f.event.trigger(c,null,c.target),c.isDefaultPrevented()&&a.preventDefault()}var d=0;f.event.special[b]={setup:function(){d++===0&&c.addEventListener(a,e,!0)},teardown:function(){--d===0&&c.removeEventListener(a,e,!0)}}}),f.each(["bind","one"],function(a,c){f.fn[c]=function(a,d,e){var g;if(typeof a=="object"){for(var h in a)this[c](h,d,a[h],e);return this}if(arguments.length===2||d===!1)e=d,d=b;c==="one"?(g=function(a){f(this).unbind(a,g);return e.apply(this,arguments)},g.guid=e.guid||f.guid++):g=e;if(a==="unload"&&c!=="one")this.one(a,d,e);else for(var i=0,j=this.length;i<j;i++)f.event.add(this[i],a,g,d);return this}}),f.fn.extend({unbind:function(a,b){if(typeof a=="object"&&!a.preventDefault)for(var c in a)this.unbind(c,a[c]);else for(var d=0,e=this.length;d<e;d++)f.event.remove(this[d],a,b);return this},delegate:function(a,b,c,d){return this.live(b,c,d,a)},undelegate:function(a,b,c){return arguments.length===0?this.unbind("live"):this.die(b,null,c,a)},trigger:function(a,b){return this.each(function(){f.event.trigger(a,b,this)})},triggerHandler:function(a,b){if(this[0])return f.event.trigger(a,b,this[0],!0)},toggle:function(a){var b=arguments,c=a.guid||f.guid++,d=0,e=function(c){var e=(f.data(this,"lastToggle"+a.guid)||0)%d;f.data(this,"lastToggle"+a.guid,e+1),c.preventDefault();return b[e].apply(this,arguments)||!1};e.guid=c;while(d<b.length)b[d++].guid=c;return this.click(e)},hover:function(a,b){return this.mouseenter(a).mouseleave(b||a)}});var L={focus:"focusin",blur:"focusout",mouseenter:"mouseover",mouseleave:"mouseout"};f.each(["live","die"],function(a,c){f.fn[c]=function(a,d,e,g){var h,i=0,j,k,l,m=g||this.selector,n=g?this:f(this.context);if(typeof a=="object"&&!a.preventDefault){for(var o in a)n[c](o,d,a[o],m);return this}if(c==="die"&&!a&&g&&g.charAt(0)==="."){n.unbind(g);return this}if(d===!1||f.isFunction(d))e=d||D,d=b;a=(a||"").split(" ");while((h=a[i++])!=null){j=x.exec(h),k="",j&&(k=j[0],h=h.replace(x,""));if(h==="hover"){a.push("mouseenter"+k,"mouseleave"+k);continue}l=h,L[h]?(a.push(L[h]+k),h=h+k):h=(L[h]||h)+k;if(c==="live")for(var p=0,q=n.length;p<q;p++)f.event.add(n[p],"live."+N(h,m),{data:d,selector:m,handler:e,origType:h,origHandler:e,preType:l});else n.unbind("live."+N(h,m),e)}return this}}),f.each("blur focus focusin focusout load resize scroll unload click dblclick mousedown mouseup mousemove mouseover mouseout mouseenter mouseleave change select submit keydown keypress keyup error".split(" "),function(a,b){f.fn[b]=function(a,c){c==null&&(c=a,a=null);return arguments.length>0?this.bind(b,a,c):this.trigger(b)},f.attrFn&&(f.attrFn[b]=!0)}),function(){function u(a,b,c,d,e,f){for(var g=0,h=d.length;g<h;g++){var i=d[g];if(i){var j=!1;i=i[a];while(i){if(i.sizcache===c){j=d[i.sizset];break}if(i.nodeType===1){f||(i.sizcache=c,i.sizset=g);if(typeof b!="string"){if(i===b){j=!0;break}}else if(k.filter(b,[i]).length>0){j=i;break}}i=i[a]}d[g]=j}}}function t(a,b,c,d,e,f){for(var g=0,h=d.length;g<h;g++){var i=d[g];if(i){var j=!1;i=i[a];while(i){if(i.sizcache===c){j=d[i.sizset];break}i.nodeType===1&&!f&&(i.sizcache=c,i.sizset=g);if(i.nodeName.toLowerCase()===b){j=i;break}i=i[a]}d[g]=j}}}var a=/((?:\((?:\([^()]+\)|[^()]+)+\)|\[(?:\[[^\[\]]*\]|['"][^'"]*['"]|[^\[\]'"]+)+\]|\\.|[^ >+~,(\[\\]+)+|[>+~])(\s*,\s*)?((?:.|\r|\n)*)/g,d=0,e=Object.prototype.toString,g=!1,h=!0,i=/\\/g,j=/\W/;[0,0].sort(function(){h=!1;return 0});var k=function(b,d,f,g){f=f||[],d=d||c;var h=d;if(d.nodeType!==1&&d.nodeType!==9)return[];if(!b||typeof b!="string")return f;var i,j,n,o,q,r,s,t,u=!0,w=k.isXML(d),x=[],y=b;do{a.exec(""),i=a.exec(y);if(i){y=i[3],x.push(i[1]);if(i[2]){o=i[3];break}}}while(i);if(x.length>1&&m.exec(b))if(x.length===2&&l.relative[x[0]])j=v(x[0]+x[1],d);else{j=l.relative[x[0]]?[d]:k(x.shift(),d);while(x.length)b=x.shift(),l.relative[b]&&(b+=x.shift()),j=v(b,j)}else{!g&&x.length>1&&d.nodeType===9&&!w&&l.match.ID.test(x[0])&&!l.match.ID.test(x[x.length-1])&&(q=k.find(x.shift(),d,w),d=q.expr?k.filter(q.expr,q.set)[0]:q.set[0]);if(d){q=g?{expr:x.pop(),set:p(g)}:k.find(x.pop(),x.length===1&&(x[0]==="~"||x[0]==="+")&&d.parentNode?d.parentNode:d,w),j=q.expr?k.filter(q.expr,q.set):q.set,x.length>0?n=p(j):u=!1;while(x.length)r=x.pop(),s=r,l.relative[r]?s=x.pop():r="",s==null&&(s=d),l.relative[r](n,s,w)}else n=x=[]}n||(n=j),n||k.error(r||b);if(e.call(n)==="[object Array]")if(!u)f.push.apply(f,n);else if(d&&d.nodeType===1)for(t=0;n[t]!=null;t++)n[t]&&(n[t]===!0||n[t].nodeType===1&&k.contains(d,n[t]))&&f.push(j[t]);else for(t=0;n[t]!=null;t++)n[t]&&n[t].nodeType===1&&f.push(j[t]);else p(n,f);o&&(k(o,h,f,g),k.uniqueSort(f));return f};k.uniqueSort=function(a){if(r){g=h,a.sort(r);if(g)for(var b=1;b<a.length;b++)a[b]===a[b-1]&&a.splice(b--,1)}return a},k.matches=function(a,b){return k(a,null,null,b)},k.matchesSelector=function(a,b){return k(b,null,null,[a]).length>0},k.find=function(a,b,c){var d;if(!a)return[];for(var e=0,f=l.order.length;e<f;e++){var g,h=l.order[e];if(g=l.leftMatch[h].exec(a)){var j=g[1];g.splice(1,1);if(j.substr(j.length-1)!=="\\"){g[1]=(g[1]||"").replace(i,""),d=l.find[h](g,b,c);if(d!=null){a=a.replace(l.match[h],"");break}}}}d||(d=typeof b.getElementsByTagName!="undefined"?b.getElementsByTagName("*"):[]);return{set:d,expr:a}},k.filter=function(a,c,d,e){var f,g,h=a,i=[],j=c,m=c&&c[0]&&k.isXML(c[0]);while(a&&c.length){for(var n in l.filter)if((f=l.leftMatch[n].exec(a))!=null&&f[2]){var o,p,q=l.filter[n],r=f[1];g=!1,f.splice(1,1);if(r.substr(r.length-1)==="\\")continue;j===i&&(i=[]);if(l.preFilter[n]){f=l.preFilter[n](f,j,d,i,e,m);if(!f)g=o=!0;else if(f===!0)continue}if(f)for(var s=0;(p=j[s])!=null;s++)if(p){o=q(p,f,s,j);var t=e^!!o;d&&o!=null?t?g=!0:j[s]=!1:t&&(i.push(p),g=!0)}if(o!==b){d||(j=i),a=a.replace(l.match[n],"");if(!g)return[];break}}if(a===h)if(g==null)k.error(a);else break;h=a}return j},k.error=function(a){throw"Syntax error, unrecognized expression: "+a};var l=k.selectors={order:["ID","NAME","TAG"],match:{ID:/#((?:[\w\u00c0-\uFFFF\-]|\\.)+)/,CLASS:/\.((?:[\w\u00c0-\uFFFF\-]|\\.)+)/,NAME:/\[name=['"]*((?:[\w\u00c0-\uFFFF\-]|\\.)+)['"]*\]/,ATTR:/\[\s*((?:[\w\u00c0-\uFFFF\-]|\\.)+)\s*(?:(\S?=)\s*(?:(['"])(.*?)\3|(#?(?:[\w\u00c0-\uFFFF\-]|\\.)*)|)|)\s*\]/,TAG:/^((?:[\w\u00c0-\uFFFF\*\-]|\\.)+)/,CHILD:/:(only|nth|last|first)-child(?:\(\s*(even|odd|(?:[+\-]?\d+|(?:[+\-]?\d*)?n\s*(?:[+\-]\s*\d+)?))\s*\))?/,POS:/:(nth|eq|gt|lt|first|last|even|odd)(?:\((\d*)\))?(?=[^\-]|$)/,PSEUDO:/:((?:[\w\u00c0-\uFFFF\-]|\\.)+)(?:\((['"]?)((?:\([^\)]+\)|[^\(\)]*)+)\2\))?/},leftMatch:{},attrMap:{"class":"className","for":"htmlFor"},attrHandle:{href:function(a){return a.getAttribute("href")},type:function(a){return a.getAttribute("type")}},relative:{"+":function(a,b){var c=typeof b=="string",d=c&&!j.test(b),e=c&&!d;d&&(b=b.toLowerCase());for(var f=0,g=a.length,h;f<g;f++)if(h=a[f]){while((h=h.previousSibling)&&h.nodeType!==1);a[f]=e||h&&h.nodeName.toLowerCase()===b?h||!1:h===b}e&&k.filter(b,a,!0)},">":function(a,b){var c,d=typeof b=="string",e=0,f=a.length;if(d&&!j.test(b)){b=b.toLowerCase();for(;e<f;e++){c=a[e];if(c){var g=c.parentNode;a[e]=g.nodeName.toLowerCase()===b?g:!1}}}else{for(;e<f;e++)c=a[e],c&&(a[e]=d?c.parentNode:c.parentNode===b);d&&k.filter(b,a,!0)}},"":function(a,b,c){var e,f=d++,g=u;typeof b=="string"&&!j.test(b)&&(b=b.toLowerCase(),e=b,g=t),g("parentNode",b,f,a,e,c)},"~":function(a,b,c){var e,f=d++,g=u;typeof b=="string"&&!j.test(b)&&(b=b.toLowerCase(),e=b,g=t),g("previousSibling",b,f,a,e,c)}},find:{ID:function(a,b,c){if(typeof b.getElementById!="undefined"&&!c){var d=b.getElementById(a[1]);return d&&d.parentNode?[d]:[]}},NAME:function(a,b){if(typeof b.getElementsByName!="undefined"){var c=[],d=b.getElementsByName(a[1]);for(var e=0,f=d.length;e<f;e++)d[e].getAttribute("name")===a[1]&&c.push(d[e]);return c.length===0?null:c}},TAG:function(a,b){if(typeof b.getElementsByTagName!="undefined")return b.getElementsByTagName(a[1])}},preFilter:{CLASS:function(a,b,c,d,e,f){a=" "+a[1].replace(i,"")+" ";if(f)return a;for(var g=0,h;(h=b[g])!=null;g++)h&&(e^(h.className&&(" "+h.className+" ").replace(/[\t\n\r]/g," ").indexOf(a)>=0)?c||d.push(h):c&&(b[g]=!1));return!1},ID:function(a){return a[1].replace(i,"")},TAG:function(a,b){return a[1].replace(i,"").toLowerCase()},CHILD:function(a){if(a[1]==="nth"){a[2]||k.error(a[0]),a[2]=a[2].replace(/^\+|\s*/g,"");var b=/(-?)(\d*)(?:n([+\-]?\d*))?/.exec(a[2]==="even"&&"2n"||a[2]==="odd"&&"2n+1"||!/\D/.test(a[2])&&"0n+"+a[2]||a[2]);a[2]=b[1]+(b[2]||1)-0,a[3]=b[3]-0}else a[2]&&k.error(a[0]);a[0]=d++;return a},ATTR:function(a,b,c,d,e,f){var g=a[1]=a[1].replace(i,"");!f&&l.attrMap[g]&&(a[1]=l.attrMap[g]),a[4]=(a[4]||a[5]||"").replace(i,""),a[2]==="~="&&(a[4]=" "+a[4]+" ");return a},PSEUDO:function(b,c,d,e,f){if(b[1]==="not")if((a.exec(b[3])||"").length>1||/^\w/.test(b[3]))b[3]=k(b[3],null,null,c);else{var g=k.filter(b[3],c,d,!0^f);d||e.push.apply(e,g);return!1}else if(l.match.POS.test(b[0])||l.match.CHILD.test(b[0]))return!0;return b},POS:function(a){a.unshift(!0);return a}},filters:{enabled:function(a){return a.disabled===!1&&a.type!=="hidden"},disabled:function(a){return a.disabled===!0},checked:function(a){return a.checked===!0},selected:function(a){a.parentNode&&a.parentNode.selectedIndex;return a.selected===!0},parent:function(a){return!!a.firstChild},empty:function(a){return!a.firstChild},has:function(a,b,c){return!!k(c[3],a).length},header:function(a){return/h\d/i.test(a.nodeName)},text:function(a){var b=a.getAttribute("type"),c=a.type;return a.nodeName.toLowerCase()==="input"&&"text"===c&&(b===c||b===null)},radio:function(a){return a.nodeName.toLowerCase()==="input"&&"radio"===a.type},checkbox:function(a){return a.nodeName.toLowerCase()==="input"&&"checkbox"===a.type},file:function(a){return a.nodeName.toLowerCase()==="input"&&"file"===a.type},password:function(a){return a.nodeName.toLowerCase()==="input"&&"password"===a.type},submit:function(a){var b=a.nodeName.toLowerCase();return(b==="input"||b==="button")&&"submit"===a.type},image:function(a){return a.nodeName.toLowerCase()==="input"&&"image"===a.type},reset:function(a){var b=a.nodeName.toLowerCase();return(b==="input"||b==="button")&&"reset"===a.type},button:function(a){var b=a.nodeName.toLowerCase();return b==="input"&&"button"===a.type||b==="button"},input:function(a){return/input|select|textarea|button/i.test(a.nodeName)},focus:function(a){return a===a.ownerDocument.activeElement}},setFilters:{first:function(a,b){return b===0},last:function(a,b,c,d){return b===d.length-1},even:function(a,b){return b%2===0},odd:function(a,b){return b%2===1},lt:function(a,b,c){return b<c[3]-0},gt:function(a,b,c){return b>c[3]-0},nth:function(a,b,c){return c[3]-0===b},eq:function(a,b,c){return c[3]-0===b}},filter:{PSEUDO:function(a,b,c,d){var e=b[1],f=l.filters[e];if(f)return f(a,c,b,d);if(e==="contains")return(a.textContent||a.innerText||k.getText([a])||"").indexOf(b[3])>=0;if(e==="not"){var g=b[3];for(var h=0,i=g.length;h<i;h++)if(g[h]===a)return!1;return!0}k.error(e)},CHILD:function(a,b){var c=b[1],d=a;switch(c){case"only":case"first":while(d=d.previousSibling)if(d.nodeType===1)return!1;if(c==="first")return!0;d=a;case"last":while(d=d.nextSibling)if(d.nodeType===1)return!1;return!0;case"nth":var e=b[2],f=b[3];if(e===1&&f===0)return!0;var g=b[0],h=a.parentNode;if(h&&(h.sizcache!==g||!a.nodeIndex)){var i=0;for(d=h.firstChild;d;d=d.nextSibling)d.nodeType===1&&(d.nodeIndex=++i);h.sizcache=g}var j=a.nodeIndex-f;return e===0?j===0:j%e===0&&j/e>=0}},ID:function(a,b){return a.nodeType===1&&a.getAttribute("id")===b},TAG:function(a,b){return b==="*"&&a.nodeType===1||a.nodeName.toLowerCase()===b},CLASS:function(a,b){return(" "+(a.className||a.getAttribute("class"))+" ").indexOf(b)>-1},ATTR:function(a,b){var c=b[1],d=l.attrHandle[c]?l.attrHandle[c](a):a[c]!=null?a[c]:a.getAttribute(c),e=d+"",f=b[2],g=b[4];return d==null?f==="!=":f==="="?e===g:f==="*="?e.indexOf(g)>=0:f==="~="?(" "+e+" ").indexOf(g)>=0:g?f==="!="?e!==g:f==="^="?e.indexOf(g)===0:f==="$="?e.substr(e.length-g.length)===g:f==="|="?e===g||e.substr(0,g.length+1)===g+"-":!1:e&&d!==!1},POS:function(a,b,c,d){var e=b[2],f=l.setFilters[e];if(f)return f(a,c,b,d)}}},m=l.match.POS,n=function(a,b){return"\\"+(b-0+1)};for(var o in l.match)l.match[o]=new RegExp(l.match[o].source+/(?![^\[]*\])(?![^\(]*\))/.source),l.leftMatch[o]=new RegExp(/(^(?:.|\r|\n)*?)/.source+l.match[o].source.replace(/\\(\d+)/g,n));var p=function(a,b){a=Array.prototype.slice.call(a,0);if(b){b.push.apply(b,a);return b}return a};try{Array.prototype.slice.call(c.documentElement.childNodes,0)[0].nodeType}catch(q){p=function(a,b){var c=0,d=b||[];if(e.call(a)==="[object Array]")Array.prototype.push.apply(d,a);else if(typeof a.length=="number")for(var f=a.length;c<f;c++)d.push(a[c]);else for(;a[c];c++)d.push(a[c]);return d}}var r,s;c.documentElement.compareDocumentPosition?r=function(a,b){if(a===b){g=!0;return 0}if(!a.compareDocumentPosition||!b.compareDocumentPosition)return a.compareDocumentPosition?-1:1;return a.compareDocumentPosition(b)&4?-1:1}:(r=function(a,b){if(a===b){g=!0;return 0}if(a.sourceIndex&&b.sourceIndex)return a.sourceIndex-b.sourceIndex;var c,d,e=[],f=[],h=a.parentNode,i=b.parentNode,j=h;if(h===i)return s(a,b);if(!h)return-1;if(!i)return 1;while(j)e.unshift(j),j=j.parentNode;j=i;while(j)f.unshift(j),j=j.parentNode;c=e.length,d=f.length;for(var k=0;k<c&&k<d;k++)if(e[k]!==f[k])return s(e[k],f[k]);return k===c?s(a,f[k],-1):s(e[k],b,1)},s=function(a,b,c){if(a===b)return c;var d=a.nextSibling;while(d){if(d===b)return-1;d=d.nextSibling}return 1}),k.getText=function(a){var b="",c;for(var d=0;a[d];d++)c=a[d],c.nodeType===3||c.nodeType===4?b+=c.nodeValue:c.nodeType!==8&&(b+=k.getText(c.childNodes));return b},function(){var a=c.createElement("div"),d="script"+(new Date).getTime(),e=c.documentElement;a.innerHTML="<a name='"+d+"'/>",e.insertBefore(a,e.firstChild),c.getElementById(d)&&(l.find.ID=function(a,c,d){if(typeof c.getElementById!="undefined"&&!d){var e=c.getElementById(a[1]);return e?e.id===a[1]||typeof e.getAttributeNode!="undefined"&&e.getAttributeNode("id").nodeValue===a[1]?[e]:b:[]}},l.filter.ID=function(a,b){var c=typeof a.getAttributeNode!="undefined"&&a.getAttributeNode("id");return a.nodeType===1&&c&&c.nodeValue===b}),e.removeChild(a),e=a=null}(),function(){var a=c.createElement("div");a.appendChild(c.createComment("")),a.getElementsByTagName("*").length>0&&(l.find.TAG=function(a,b){var c=b.getElementsByTagName(a[1]);if(a[1]==="*"){var d=[];for(var e=0;c[e];e++)c[e].nodeType===1&&d.push(c[e]);c=d}return c}),a.innerHTML="<a href='#'></a>",a.firstChild&&typeof a.firstChild.getAttribute!="undefined"&&a.firstChild.getAttribute("href")!=="#"&&(l.attrHandle.href=function(a){return a.getAttribute("href",2)}),a=null}(),c.querySelectorAll&&function(){var a=k,b=c.createElement("div"),d="__sizzle__";b.innerHTML="<p class='TEST'></p>";if(!b.querySelectorAll||b.querySelectorAll(".TEST").length!==0){k=function(b,e,f,g){e=e||c;if(!g&&!k.isXML(e)){var h=/^(\w+$)|^\.([\w\-]+$)|^#([\w\-]+$)/.exec(b);if(h&&(e.nodeType===1||e.nodeType===9)){if(h[1])return p(e.getElementsByTagName(b),f);if(h[2]&&l.find.CLASS&&e.getElementsByClassName)return p(e.getElementsByClassName(h[2]),f)}if(e.nodeType===9){if(b==="body"&&e.body)return p([e.body],f);if(h&&h[3]){var i=e.getElementById(h[3]);if(!i||!i.parentNode)return p([],f);if(i.id===h[3])return p([i],f)}try{return p(e.querySelectorAll(b),f)}catch(j){}}else if(e.nodeType===1&&e.nodeName.toLowerCase()!=="object"){var m=e,n=e.getAttribute("id"),o=n||d,q=e.parentNode,r=/^\s*[+~]/.test(b);n?o=o.replace(/'/g,"\\$&"):e.setAttribute("id",o),r&&q&&(e=e.parentNode);try{if(!r||q)return p(e.querySelectorAll("[id='"+o+"'] "+b),f)}catch(s){}finally{n||m.removeAttribute("id")}}}return a(b,e,f,g)};for(var e in a)k[e]=a[e];b=null}}(),function(){var a=c.documentElement,b=a.matchesSelector||a.mozMatchesSelector||a.webkitMatchesSelector||a.msMatchesSelector;if(b){var d=!b.call(c.createElement("div"),"div"),e=!1;try{b.call(c.documentElement,"[test!='']:sizzle")}catch(f){e=!0}k.matchesSelector=function(a,c){c=c.replace(/\=\s*([^'"\]]*)\s*\]/g,"='$1']");if(!k.isXML(a))try{if(e||!l.match.PSEUDO.test(c)&&!/!=/.test(c)){var f=b.call(a,c);if(f||!d||a.document&&a.document.nodeType!==11)return f}}catch(g){}return k(c,null,null,[a]).length>0}}}(),function(){var a=c.createElement("div");a.innerHTML="<div class='test e'></div><div class='test'></div>";if(!!a.getElementsByClassName&&a.getElementsByClassName("e").length!==0){a.lastChild.className="e";if(a.getElementsByClassName("e").length===1)return;l.order.splice(1,0,"CLASS"),l.find.CLASS=function(a,b,c){if(typeof b.getElementsByClassName!="undefined"&&!c)return b.getElementsByClassName(a[1])},a=null}}(),c.documentElement.contains?k.contains=function(a,b){return a!==b&&(a.contains?a.contains(b):!0)}:c.documentElement.compareDocumentPosition?k.contains=function(a,b){return!!(a.compareDocumentPosition(b)&16)}:k.contains=function(){return!1},k.isXML=function(a){var b=(a?a.ownerDocument||a:0).documentElement;return b?b.nodeName!=="HTML":!1};var v=function(a,b){var c,d=[],e="",f=b.nodeType?[b]:b;while(c=l.match.PSEUDO.exec(a))e+=c[0],a=a.replace(l.match.PSEUDO,"");a=l.relative[a]?a+"*":a;for(var g=0,h=f.length;g<h;g++)k(a,f[g],d);return k.filter(e,d)};f.find=k,f.expr=k.selectors,f.expr[":"]=f.expr.filters,f.unique=k.uniqueSort,f.text=k.getText,f.isXMLDoc=k.isXML,f.contains=k.contains}();var O=/Until$/,P=/^(?:parents|prevUntil|prevAll)/,Q=/,/,R=/^.[^:#\[\.,]*$/,S=Array.prototype.slice,T=f.expr.match.POS,U={children:!0,contents:!0,next:!0,prev:!0};f.fn.extend({find:function(a){var b=this,c,d;if(typeof a!="string")return f(a).filter(function(){for(c=0,d=b.length;c<d;c++)if(f.contains(b[c],this))return!0});var e=this.pushStack("","find",a),g,h,i;for(c=0,d=this.length;c<d;c++){g=e.length,f.find(a,this[c],e);if(c>0)for(h=g;h<e.length;h++)for(i=0;i<g;i++)if(e[i]===e[h]){e.splice(h--,1);break}}return e},has:function(a){var b=f(a);return this.filter(function(){for(var a=0,c=b.length;a<c;a++)if(f.contains(this,b[a]))return!0})},not:function(a){return this.pushStack(W(this,a,!1),"not",a)},filter:function(a){return this.pushStack(W(this,a,!0),"filter",a)},is:function(a){return!!a&&(typeof a=="string"?f.filter(a,this).length>0:this.filter(a).length>0)},closest:function(a,b){var c=[],d,e,g=this[0];if(f.isArray(a)){var h,i,j={},k=1;if(g&&a.length){for(d=0,e=a.length;d<e;d++)i=a[d],j[i]||(j[i]=T.test(i)?f(i,b||this.context):i);while(g&&g.ownerDocument&&g!==b){for(i in j)h=j[i],(h.jquery?h.index(g)>-1:f(g).is(h))&&c.push({selector:i,elem:g,level:k});g=g.parentNode,k++}}return c}var l=T.test(a)||typeof a!="string"?f(a,b||this.context):0;for(d=0,e=this.length;d<e;d++){g=this[d];while(g){if(l?l.index(g)>-1:f.find.matchesSelector(g,a)){c.push(g);break}g=g.parentNode;if(!g||!g.ownerDocument||g===b||g.nodeType===11)break}}c=c.length>1?f.unique(c):c;return this.pushStack(c,"closest",a)},index:function(a){if(!a||typeof a=="string")return f.inArray(this[0],a?f(a):this.parent().children());return f.inArray(a.jquery?a[0]:a,this)},add:function(a,b){var c=typeof a=="string"?f(a,b):f.makeArray(a&&a.nodeType?[a]:a),d=f.merge(this.get(),c);return this.pushStack(V(c[0])||V(d[0])?d:f.unique(d))},andSelf:function(){return this.add(this.prevObject)}}),f.each({parent:function(a){var b=a.parentNode;return b&&b.nodeType!==11?b:null},parents:function(a){return f.dir(a,"parentNode")},parentsUntil:function(a,b,c){return f.dir(a,"parentNode",c)},next:function(a){return f.nth(a,2,"nextSibling")},prev:function(a){return f.nth(a,2,"previousSibling")},nextAll:function(a){return f.dir(a,"nextSibling")},prevAll:function(a){return f.dir(a,"previousSibling")},nextUntil:function(a,b,c){return f.dir(a,"nextSibling",c)},prevUntil:function(a,b,c){return f.dir(a,"previousSibling",c)},siblings:function(a){return f.sibling(a.parentNode.firstChild,a)},children:function(a){return f.sibling(a.firstChild)},contents:function(a){return f.nodeName(a,"iframe")?a.contentDocument||a.contentWindow.document:f.makeArray(a.childNodes)}},function(a,b){f.fn[a]=function(c,d){var e=f.map(this,b,c),g=S.call(arguments);O.test(a)||(d=c),d&&typeof d=="string"&&(e=f.filter(d,e)),e=this.length>1&&!U[a]?f.unique(e):e,(this.length>1||Q.test(d))&&P.test(a)&&(e=e.reverse());return this.pushStack(e,a,g.join(","))}}),f.extend({filter:function(a,b,c){c&&(a=":not("+a+")");return b.length===1?f.find.matchesSelector(b[0],a)?[b[0]]:[]:f.find.matches(a,b)},dir:function(a,c,d){var e=[],g=a[c];while(g&&g.nodeType!==9&&(d===b||g.nodeType!==1||!f(g).is(d)))g.nodeType===1&&e.push(g),g=g[c];return e},nth:function(a,b,c,d){b=b||1;var e=0;for(;a;a=a[c])if(a.nodeType===1&&++e===b)break;return a},sibling:function(a,b){var c=[];for(;a;a=a.nextSibling)a.nodeType===1&&a!==b&&c.push(a);return c}});var X=/ jQuery\d+="(?:\d+|null)"/g,Y=/^\s+/,Z=/<(?!area|br|col|embed|hr|img|input|link|meta|param)(([\w:]+)[^>]*)\/>/ig,$=/<([\w:]+)/,_=/<tbody/i,ba=/<|&#?\w+;/,bb=/<(?:script|object|embed|option|style)/i,bc=/checked\s*(?:[^=]|=\s*.checked.)/i,bd=/\/(java|ecma)script/i,be=/^\s*<!(?:\[CDATA\[|\-\-)/,bf={option:[1,"<select multiple='multiple'>","</select>"],legend:[1,"<fieldset>","</fieldset>"],thead:[1,"<table>","</table>"],tr:[2,"<table><tbody>","</tbody></table>"],td:[3,"<table><tbody><tr>","</tr></tbody></table>"],col:[2,"<table><tbody></tbody><colgroup>","</colgroup></table>"],area:[1,"<map>","</map>"],_default:[0,"",""]};bf.optgroup=bf.option,bf.tbody=bf.tfoot=bf.colgroup=bf.caption=bf.thead,bf.th=bf.td,f.support.htmlSerialize||(bf._default=[1,"div<div>","</div>"]),f.fn.extend({text:function(a){if(f.isFunction(a))return this.each(function(b){var c=f(this);c.text(a.call(this,b,c.text()))});if(typeof a!="object"&&a!==b)return this.empty().append((this[0]&&this[0].ownerDocument||c).createTextNode(a));return f.text(this)},wrapAll:function(a){if(f.isFunction(a))return this.each(function(b){f(this).wrapAll(a.call(this,b))});if(this[0]){var b=f(a,this[0].ownerDocument).eq(0).clone(!0);this[0].parentNode&&b.insertBefore(this[0]),b.map(function(){var a=this;while(a.firstChild&&a.firstChild.nodeType===1)a=a.firstChild;return a}).append(this)}return this},wrapInner:function(a){if(f.isFunction(a))return this.each(function(b){f(this).wrapInner(a.call(this,b))});return this.each(function(){var b=f(this),c=b.contents();c.length?c.wrapAll(a):b.append(a)})},wrap:function(a){return this.each(function(){f(this).wrapAll(a)})},unwrap:function(){return this.parent().each(function(){f.nodeName(this,"body")||f(this).replaceWith(this.childNodes)}).end()},append:function(){return this.domManip(arguments,!0,function(a){this.nodeType===1&&this.appendChild(a)})},prepend:function(){return this.domManip(arguments,!0,function(a){this.nodeType===1&&this.insertBefore(a,this.firstChild)})},before:function(){if(this[0]&&this[0].parentNode)return this.domManip(arguments,!1,function(a){this.parentNode.insertBefore(a,this)});if(arguments.length){var a=f(arguments[0]);a.push.apply(a,this.toArray());return this.pushStack(a,"before",arguments)}},after:function(){if(this[0]&&this[0].parentNode)return this.domManip(arguments,!1,function(a){this.parentNode.insertBefore(a,this.nextSibling)});if(arguments.length){var a=this.pushStack(this,"after",arguments);a.push.apply(a,f(arguments[0]).toArray());return a}},remove:function(a,b){for(var c=0,d;(d=this[c])!=null;c++)if(!a||f.filter(a,[d]).length)!b&&d.nodeType===1&&(f.cleanData(d.getElementsByTagName("*")),f.cleanData([d])),d.parentNode&&d.parentNode.removeChild(d);return this},empty:function(){for(var a=0,b;(b=this[a])!=null;a++){b.nodeType===1&&f.cleanData(b.getElementsByTagName("*"));while(b.firstChild)b.removeChild(b.firstChild)}return this},clone:function(a,b){a=a==null?!1:a,b=b==null?a:b;return this.map(function(){return f.clone(this,a,b)})},html:function(a){if(a===b)return this[0]&&this[0].nodeType===1?this[0].innerHTML.replace(X,""):null;if(typeof a=="string"&&!bb.test(a)&&(f.support.leadingWhitespace||!Y.test(a))&&!bf[($.exec(a)||["",""])[1].toLowerCase()]){a=a.replace(Z,"<$1></$2>");try{for(var c=0,d=this.length;c<d;c++)this[c].nodeType===1&&(f.cleanData(this[c].getElementsByTagName("*")),this[c].innerHTML=a)}catch(e){this.empty().append(a)}}else f.isFunction(a)?this.each(function(b){var c=f(this);c.html(a.call(this,b,c.html()))}):this.empty().append(a);return this},replaceWith:function(a){if(this[0]&&this[0].parentNode){if(f.isFunction(a))return this.each(function(b){var c=f(this),d=c.html();c.replaceWith(a.call(this,b,d))});typeof a!="string"&&(a=f(a).detach());return this.each(function(){var b=this.nextSibling,c=this.parentNode;f(this).remove(),b?f(b).before(a):f(c).append(a)})}return this.length?this.pushStack(f(f.isFunction(a)?a():a),"replaceWith",a):this},detach:function(a){return this.remove(a,!0)},domManip:function(a,c,d){var e,g,h,i,j=a[0],k=[];if(!f.support.checkClone&&arguments.length===3&&typeof j=="string"&&bc.test(j))return this.each(function(){f(this).domManip(a,c,d,!0)});if(f.isFunction(j))return this.each(function(e){var g=f(this);a[0]=j.call(this,e,c?g.html():b),g.domManip(a,c,d)});if(this[0]){i=j&&j.parentNode,f.support.parentNode&&i&&i.nodeType===11&&i.childNodes.length===this.length?e={fragment:i}:e=f.buildFragment(a,this,k),h=e.fragment,h.childNodes.length===1?g=h=h.firstChild:g=h.firstChild;if(g){c=c&&f.nodeName(g,"tr");for(var l=0,m=this.length,n=m-1;l<m;l++)d.call(c?bg(this[l],g):this[l],e.cacheable||m>1&&l<n?f.clone(h,!0,!0):h)}k.length&&f.each(k,bm)}return this}}),f.buildFragment=function(a,b,d){var e,g,h,i;b&&b[0]&&(i=b[0].ownerDocument||b[0]),i.createDocumentFragment||(i=c),a.length===1&&typeof a[0]=="string"&&a[0].length<512&&i===c&&a[0].charAt(0)==="<"&&!bb.test(a[0])&&(f.support.checkClone||!bc.test(a[0]))&&(g=!0,h=f.fragments[a[0]],h&&h!==1&&(e=h)),e||(e=i.createDocumentFragment(),f.clean(a,i,e,d)),g&&(f.fragments[a[0]]=h?e:1);return{fragment:e,cacheable:g}},f.fragments={},f.each({appendTo:"append",prependTo:"prepend",insertBefore:"before",insertAfter:"after",replaceAll:"replaceWith"},function(a,b){f.fn[a]=function(c){var d=[],e=f(c),g=this.length===1&&this[0].parentNode;if(g&&g.nodeType===11&&g.childNodes.length===1&&e.length===1){e[b](this[0]);return this}for(var h=0,i=e.length;h<i;h++){var j=(h>0?this.clone(!0):this).get();f(e[h])[b](j),d=d.concat(j
)}return this.pushStack(d,a,e.selector)}}),f.extend({clone:function(a,b,c){var d=a.cloneNode(!0),e,g,h;if((!f.support.noCloneEvent||!f.support.noCloneChecked)&&(a.nodeType===1||a.nodeType===11)&&!f.isXMLDoc(a)){bi(a,d),e=bj(a),g=bj(d);for(h=0;e[h];++h)bi(e[h],g[h])}if(b){bh(a,d);if(c){e=bj(a),g=bj(d);for(h=0;e[h];++h)bh(e[h],g[h])}}e=g=null;return d},clean:function(a,b,d,e){var g;b=b||c,typeof b.createElement=="undefined"&&(b=b.ownerDocument||b[0]&&b[0].ownerDocument||c);var h=[],i;for(var j=0,k;(k=a[j])!=null;j++){typeof k=="number"&&(k+="");if(!k)continue;if(typeof k=="string")if(!ba.test(k))k=b.createTextNode(k);else{k=k.replace(Z,"<$1></$2>");var l=($.exec(k)||["",""])[1].toLowerCase(),m=bf[l]||bf._default,n=m[0],o=b.createElement("div");o.innerHTML=m[1]+k+m[2];while(n--)o=o.lastChild;if(!f.support.tbody){var p=_.test(k),q=l==="table"&&!p?o.firstChild&&o.firstChild.childNodes:m[1]==="<table>"&&!p?o.childNodes:[];for(i=q.length-1;i>=0;--i)f.nodeName(q[i],"tbody")&&!q[i].childNodes.length&&q[i].parentNode.removeChild(q[i])}!f.support.leadingWhitespace&&Y.test(k)&&o.insertBefore(b.createTextNode(Y.exec(k)[0]),o.firstChild),k=o.childNodes}var r;if(!f.support.appendChecked)if(k[0]&&typeof (r=k.length)=="number")for(i=0;i<r;i++)bl(k[i]);else bl(k);k.nodeType?h.push(k):h=f.merge(h,k)}if(d){g=function(a){return!a.type||bd.test(a.type)};for(j=0;h[j];j++)if(e&&f.nodeName(h[j],"script")&&(!h[j].type||h[j].type.toLowerCase()==="text/javascript"))e.push(h[j].parentNode?h[j].parentNode.removeChild(h[j]):h[j]);else{if(h[j].nodeType===1){var s=f.grep(h[j].getElementsByTagName("script"),g);h.splice.apply(h,[j+1,0].concat(s))}d.appendChild(h[j])}}return h},cleanData:function(a){var b,c,d=f.cache,e=f.expando,g=f.event.special,h=f.support.deleteExpando;for(var i=0,j;(j=a[i])!=null;i++){if(j.nodeName&&f.noData[j.nodeName.toLowerCase()])continue;c=j[f.expando];if(c){b=d[c]&&d[c][e];if(b&&b.events){for(var k in b.events)g[k]?f.event.remove(j,k):f.removeEvent(j,k,b.handle);b.handle&&(b.handle.elem=null)}h?delete j[f.expando]:j.removeAttribute&&j.removeAttribute(f.expando),delete d[c]}}}});var bn=/alpha\([^)]*\)/i,bo=/opacity=([^)]*)/,bp=/([A-Z]|^ms)/g,bq=/^-?\d+(?:px)?$/i,br=/^-?\d/,bs=/^[+\-]=/,bt=/[^+\-\.\de]+/g,bu={position:"absolute",visibility:"hidden",display:"block"},bv=["Left","Right"],bw=["Top","Bottom"],bx,by,bz;f.fn.css=function(a,c){if(arguments.length===2&&c===b)return this;return f.access(this,a,c,!0,function(a,c,d){return d!==b?f.style(a,c,d):f.css(a,c)})},f.extend({cssHooks:{opacity:{get:function(a,b){if(b){var c=bx(a,"opacity","opacity");return c===""?"1":c}return a.style.opacity}}},cssNumber:{fillOpacity:!0,fontWeight:!0,lineHeight:!0,opacity:!0,orphans:!0,widows:!0,zIndex:!0,zoom:!0},cssProps:{"float":f.support.cssFloat?"cssFloat":"styleFloat"},style:function(a,c,d,e){if(!!a&&a.nodeType!==3&&a.nodeType!==8&&!!a.style){var g,h,i=f.camelCase(c),j=a.style,k=f.cssHooks[i];c=f.cssProps[i]||i;if(d===b){if(k&&"get"in k&&(g=k.get(a,!1,e))!==b)return g;return j[c]}h=typeof d;if(h==="number"&&isNaN(d)||d==null)return;h==="string"&&bs.test(d)&&(d=+d.replace(bt,"")+parseFloat(f.css(a,c)),h="number"),h==="number"&&!f.cssNumber[i]&&(d+="px");if(!k||!("set"in k)||(d=k.set(a,d))!==b)try{j[c]=d}catch(l){}}},css:function(a,c,d){var e,g;c=f.camelCase(c),g=f.cssHooks[c],c=f.cssProps[c]||c,c==="cssFloat"&&(c="float");if(g&&"get"in g&&(e=g.get(a,!0,d))!==b)return e;if(bx)return bx(a,c)},swap:function(a,b,c){var d={};for(var e in b)d[e]=a.style[e],a.style[e]=b[e];c.call(a);for(e in b)a.style[e]=d[e]}}),f.curCSS=f.css,f.each(["height","width"],function(a,b){f.cssHooks[b]={get:function(a,c,d){var e;if(c){if(a.offsetWidth!==0)return bA(a,b,d);f.swap(a,bu,function(){e=bA(a,b,d)});return e}},set:function(a,b){if(!bq.test(b))return b;b=parseFloat(b);if(b>=0)return b+"px"}}}),f.support.opacity||(f.cssHooks.opacity={get:function(a,b){return bo.test((b&&a.currentStyle?a.currentStyle.filter:a.style.filter)||"")?parseFloat(RegExp.$1)/100+"":b?"1":""},set:function(a,b){var c=a.style,d=a.currentStyle;c.zoom=1;var e=f.isNaN(b)?"":"alpha(opacity="+b*100+")",g=d&&d.filter||c.filter||"";c.filter=bn.test(g)?g.replace(bn,e):g+" "+e}}),f(function(){f.support.reliableMarginRight||(f.cssHooks.marginRight={get:function(a,b){var c;f.swap(a,{display:"inline-block"},function(){b?c=bx(a,"margin-right","marginRight"):c=a.style.marginRight});return c}})}),c.defaultView&&c.defaultView.getComputedStyle&&(by=function(a,c){var d,e,g;c=c.replace(bp,"-$1").toLowerCase();if(!(e=a.ownerDocument.defaultView))return b;if(g=e.getComputedStyle(a,null))d=g.getPropertyValue(c),d===""&&!f.contains(a.ownerDocument.documentElement,a)&&(d=f.style(a,c));return d}),c.documentElement.currentStyle&&(bz=function(a,b){var c,d=a.currentStyle&&a.currentStyle[b],e=a.runtimeStyle&&a.runtimeStyle[b],f=a.style;!bq.test(d)&&br.test(d)&&(c=f.left,e&&(a.runtimeStyle.left=a.currentStyle.left),f.left=b==="fontSize"?"1em":d||0,d=f.pixelLeft+"px",f.left=c,e&&(a.runtimeStyle.left=e));return d===""?"auto":d}),bx=by||bz,f.expr&&f.expr.filters&&(f.expr.filters.hidden=function(a){var b=a.offsetWidth,c=a.offsetHeight;return b===0&&c===0||!f.support.reliableHiddenOffsets&&(a.style.display||f.css(a,"display"))==="none"},f.expr.filters.visible=function(a){return!f.expr.filters.hidden(a)});var bB=/%20/g,bC=/\[\]$/,bD=/\r?\n/g,bE=/#.*$/,bF=/^(.*?):[ \t]*([^\r\n]*)\r?$/mg,bG=/^(?:color|date|datetime|email|hidden|month|number|password|range|search|tel|text|time|url|week)$/i,bH=/^(?:about|app|app\-storage|.+\-extension|file|widget):$/,bI=/^(?:GET|HEAD)$/,bJ=/^\/\//,bK=/\?/,bL=/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,bM=/^(?:select|textarea)/i,bN=/\s+/,bO=/([?&])_=[^&]*/,bP=/^([\w\+\.\-]+:)(?:\/\/([^\/?#:]*)(?::(\d+))?)?/,bQ=f.fn.load,bR={},bS={},bT,bU;try{bT=e.href}catch(bV){bT=c.createElement("a"),bT.href="",bT=bT.href}bU=bP.exec(bT.toLowerCase())||[],f.fn.extend({load:function(a,c,d){if(typeof a!="string"&&bQ)return bQ.apply(this,arguments);if(!this.length)return this;var e=a.indexOf(" ");if(e>=0){var g=a.slice(e,a.length);a=a.slice(0,e)}var h="GET";c&&(f.isFunction(c)?(d=c,c=b):typeof c=="object"&&(c=f.param(c,f.ajaxSettings.traditional),h="POST"));var i=this;f.ajax({url:a,type:h,dataType:"html",data:c,complete:function(a,b,c){c=a.responseText,a.isResolved()&&(a.done(function(a){c=a}),i.html(g?f("<div>").append(c.replace(bL,"")).find(g):c)),d&&i.each(d,[c,b,a])}});return this},serialize:function(){return f.param(this.serializeArray())},serializeArray:function(){return this.map(function(){return this.elements?f.makeArray(this.elements):this}).filter(function(){return this.name&&!this.disabled&&(this.checked||bM.test(this.nodeName)||bG.test(this.type))}).map(function(a,b){var c=f(this).val();return c==null?null:f.isArray(c)?f.map(c,function(a,c){return{name:b.name,value:a.replace(bD,"\r\n")}}):{name:b.name,value:c.replace(bD,"\r\n")}}).get()}}),f.each("ajaxStart ajaxStop ajaxComplete ajaxError ajaxSuccess ajaxSend".split(" "),function(a,b){f.fn[b]=function(a){return this.bind(b,a)}}),f.each(["get","post"],function(a,c){f[c]=function(a,d,e,g){f.isFunction(d)&&(g=g||e,e=d,d=b);return f.ajax({type:c,url:a,data:d,success:e,dataType:g})}}),f.extend({getScript:function(a,c){return f.get(a,b,c,"script")},getJSON:function(a,b,c){return f.get(a,b,c,"json")},ajaxSetup:function(a,b){b?f.extend(!0,a,f.ajaxSettings,b):(b=a,a=f.extend(!0,f.ajaxSettings,b));for(var c in{context:1,url:1})c in b?a[c]=b[c]:c in f.ajaxSettings&&(a[c]=f.ajaxSettings[c]);return a},ajaxSettings:{url:bT,isLocal:bH.test(bU[1]),global:!0,type:"GET",contentType:"application/x-www-form-urlencoded",processData:!0,async:!0,accepts:{xml:"application/xml, text/xml",html:"text/html",text:"text/plain",json:"application/json, text/javascript","*":"*/*"},contents:{xml:/xml/,html:/html/,json:/json/},responseFields:{xml:"responseXML",text:"responseText"},converters:{"* text":a.String,"text html":!0,"text json":f.parseJSON,"text xml":f.parseXML}},ajaxPrefilter:bW(bR),ajaxTransport:bW(bS),ajax:function(a,c){function w(a,c,l,m){if(s!==2){s=2,q&&clearTimeout(q),p=b,n=m||"",v.readyState=a?4:0;var o,r,u,w=l?bZ(d,v,l):b,x,y;if(a>=200&&a<300||a===304){if(d.ifModified){if(x=v.getResponseHeader("Last-Modified"))f.lastModified[k]=x;if(y=v.getResponseHeader("Etag"))f.etag[k]=y}if(a===304)c="notmodified",o=!0;else try{r=b$(d,w),c="success",o=!0}catch(z){c="parsererror",u=z}}else{u=c;if(!c||a)c="error",a<0&&(a=0)}v.status=a,v.statusText=c,o?h.resolveWith(e,[r,c,v]):h.rejectWith(e,[v,c,u]),v.statusCode(j),j=b,t&&g.trigger("ajax"+(o?"Success":"Error"),[v,d,o?r:u]),i.resolveWith(e,[v,c]),t&&(g.trigger("ajaxComplete",[v,d]),--f.active||f.event.trigger("ajaxStop"))}}typeof a=="object"&&(c=a,a=b),c=c||{};var d=f.ajaxSetup({},c),e=d.context||d,g=e!==d&&(e.nodeType||e instanceof f)?f(e):f.event,h=f.Deferred(),i=f._Deferred(),j=d.statusCode||{},k,l={},m={},n,o,p,q,r,s=0,t,u,v={readyState:0,setRequestHeader:function(a,b){if(!s){var c=a.toLowerCase();a=m[c]=m[c]||a,l[a]=b}return this},getAllResponseHeaders:function(){return s===2?n:null},getResponseHeader:function(a){var c;if(s===2){if(!o){o={};while(c=bF.exec(n))o[c[1].toLowerCase()]=c[2]}c=o[a.toLowerCase()]}return c===b?null:c},overrideMimeType:function(a){s||(d.mimeType=a);return this},abort:function(a){a=a||"abort",p&&p.abort(a),w(0,a);return this}};h.promise(v),v.success=v.done,v.error=v.fail,v.complete=i.done,v.statusCode=function(a){if(a){var b;if(s<2)for(b in a)j[b]=[j[b],a[b]];else b=a[v.status],v.then(b,b)}return this},d.url=((a||d.url)+"").replace(bE,"").replace(bJ,bU[1]+"//"),d.dataTypes=f.trim(d.dataType||"*").toLowerCase().split(bN),d.crossDomain==null&&(r=bP.exec(d.url.toLowerCase()),d.crossDomain=!(!r||r[1]==bU[1]&&r[2]==bU[2]&&(r[3]||(r[1]==="http:"?80:443))==(bU[3]||(bU[1]==="http:"?80:443)))),d.data&&d.processData&&typeof d.data!="string"&&(d.data=f.param(d.data,d.traditional)),bX(bR,d,c,v);if(s===2)return!1;t=d.global,d.type=d.type.toUpperCase(),d.hasContent=!bI.test(d.type),t&&f.active++===0&&f.event.trigger("ajaxStart");if(!d.hasContent){d.data&&(d.url+=(bK.test(d.url)?"&":"?")+d.data),k=d.url;if(d.cache===!1){var x=f.now(),y=d.url.replace(bO,"$1_="+x);d.url=y+(y===d.url?(bK.test(d.url)?"&":"?")+"_="+x:"")}}(d.data&&d.hasContent&&d.contentType!==!1||c.contentType)&&v.setRequestHeader("Content-Type",d.contentType),d.ifModified&&(k=k||d.url,f.lastModified[k]&&v.setRequestHeader("If-Modified-Since",f.lastModified[k]),f.etag[k]&&v.setRequestHeader("If-None-Match",f.etag[k])),v.setRequestHeader("Accept",d.dataTypes[0]&&d.accepts[d.dataTypes[0]]?d.accepts[d.dataTypes[0]]+(d.dataTypes[0]!=="*"?", */*; q=0.01":""):d.accepts["*"]);for(u in d.headers)v.setRequestHeader(u,d.headers[u]);if(d.beforeSend&&(d.beforeSend.call(e,v,d)===!1||s===2)){v.abort();return!1}for(u in{success:1,error:1,complete:1})v[u](d[u]);p=bX(bS,d,c,v);if(!p)w(-1,"No Transport");else{v.readyState=1,t&&g.trigger("ajaxSend",[v,d]),d.async&&d.timeout>0&&(q=setTimeout(function(){v.abort("timeout")},d.timeout));try{s=1,p.send(l,w)}catch(z){status<2?w(-1,z):f.error(z)}}return v},param:function(a,c){var d=[],e=function(a,b){b=f.isFunction(b)?b():b,d[d.length]=encodeURIComponent(a)+"="+encodeURIComponent(b)};c===b&&(c=f.ajaxSettings.traditional);if(f.isArray(a)||a.jquery&&!f.isPlainObject(a))f.each(a,function(){e(this.name,this.value)});else for(var g in a)bY(g,a[g],c,e);return d.join("&").replace(bB,"+")}}),f.extend({active:0,lastModified:{},etag:{}});var b_=f.now(),ca=/(\=)\?(&|$)|\?\?/i;f.ajaxSetup({jsonp:"callback",jsonpCallback:function(){return f.expando+"_"+b_++}}),f.ajaxPrefilter("json jsonp",function(b,c,d){var e=b.contentType==="application/x-www-form-urlencoded"&&typeof b.data=="string";if(b.dataTypes[0]==="jsonp"||b.jsonp!==!1&&(ca.test(b.url)||e&&ca.test(b.data))){var g,h=b.jsonpCallback=f.isFunction(b.jsonpCallback)?b.jsonpCallback():b.jsonpCallback,i=a[h],j=b.url,k=b.data,l="$1"+h+"$2";b.jsonp!==!1&&(j=j.replace(ca,l),b.url===j&&(e&&(k=k.replace(ca,l)),b.data===k&&(j+=(/\?/.test(j)?"&":"?")+b.jsonp+"="+h))),b.url=j,b.data=k,a[h]=function(a){g=[a]},d.always(function(){a[h]=i,g&&f.isFunction(i)&&a[h](g[0])}),b.converters["script json"]=function(){g||f.error(h+" was not called");return g[0]},b.dataTypes[0]="json";return"script"}}),f.ajaxSetup({accepts:{script:"text/javascript, application/javascript, application/ecmascript, application/x-ecmascript"},contents:{script:/javascript|ecmascript/},converters:{"text script":function(a){f.globalEval(a);return a}}}),f.ajaxPrefilter("script",function(a){a.cache===b&&(a.cache=!1),a.crossDomain&&(a.type="GET",a.global=!1)}),f.ajaxTransport("script",function(a){if(a.crossDomain){var d,e=c.head||c.getElementsByTagName("head")[0]||c.documentElement;return{send:function(f,g){d=c.createElement("script"),d.async="async",a.scriptCharset&&(d.charset=a.scriptCharset),d.src=a.url,d.onload=d.onreadystatechange=function(a,c){if(c||!d.readyState||/loaded|complete/.test(d.readyState))d.onload=d.onreadystatechange=null,e&&d.parentNode&&e.removeChild(d),d=b,c||g(200,"success")},e.insertBefore(d,e.firstChild)},abort:function(){d&&d.onload(0,1)}}}});var cb=a.ActiveXObject?function(){for(var a in cd)cd[a](0,1)}:!1,cc=0,cd;f.ajaxSettings.xhr=a.ActiveXObject?function(){return!this.isLocal&&ce()||cf()}:ce,function(a){f.extend(f.support,{ajax:!!a,cors:!!a&&"withCredentials"in a})}(f.ajaxSettings.xhr()),f.support.ajax&&f.ajaxTransport(function(c){if(!c.crossDomain||f.support.cors){var d;return{send:function(e,g){var h=c.xhr(),i,j;c.username?h.open(c.type,c.url,c.async,c.username,c.password):h.open(c.type,c.url,c.async);if(c.xhrFields)for(j in c.xhrFields)h[j]=c.xhrFields[j];c.mimeType&&h.overrideMimeType&&h.overrideMimeType(c.mimeType),!c.crossDomain&&!e["X-Requested-With"]&&(e["X-Requested-With"]="XMLHttpRequest");try{for(j in e)h.setRequestHeader(j,e[j])}catch(k){}h.send(c.hasContent&&c.data||null),d=function(a,e){var j,k,l,m,n;try{if(d&&(e||h.readyState===4)){d=b,i&&(h.onreadystatechange=f.noop,cb&&delete cd[i]);if(e)h.readyState!==4&&h.abort();else{j=h.status,l=h.getAllResponseHeaders(),m={},n=h.responseXML,n&&n.documentElement&&(m.xml=n),m.text=h.responseText;try{k=h.statusText}catch(o){k=""}!j&&c.isLocal&&!c.crossDomain?j=m.text?200:404:j===1223&&(j=204)}}}catch(p){e||g(-1,p)}m&&g(j,k,m,l)},!c.async||h.readyState===4?d():(i=++cc,cb&&(cd||(cd={},f(a).unload(cb)),cd[i]=d),h.onreadystatechange=d)},abort:function(){d&&d(0,1)}}}});var cg={},ch,ci,cj=/^(?:toggle|show|hide)$/,ck=/^([+\-]=)?([\d+.\-]+)([a-z%]*)$/i,cl,cm=[["height","marginTop","marginBottom","paddingTop","paddingBottom"],["width","marginLeft","marginRight","paddingLeft","paddingRight"],["opacity"]],cn,co=a.webkitRequestAnimationFrame||a.mozRequestAnimationFrame||a.oRequestAnimationFrame;f.fn.extend({show:function(a,b,c){var d,e;if(a||a===0)return this.animate(cr("show",3),a,b,c);for(var g=0,h=this.length;g<h;g++)d=this[g],d.style&&(e=d.style.display,!f._data(d,"olddisplay")&&e==="none"&&(e=d.style.display=""),e===""&&f.css(d,"display")==="none"&&f._data(d,"olddisplay",cs(d.nodeName)));for(g=0;g<h;g++){d=this[g];if(d.style){e=d.style.display;if(e===""||e==="none")d.style.display=f._data(d,"olddisplay")||""}}return this},hide:function(a,b,c){if(a||a===0)return this.animate(cr("hide",3),a,b,c);for(var d=0,e=this.length;d<e;d++)if(this[d].style){var g=f.css(this[d],"display");g!=="none"&&!f._data(this[d],"olddisplay")&&f._data(this[d],"olddisplay",g)}for(d=0;d<e;d++)this[d].style&&(this[d].style.display="none");return this},_toggle:f.fn.toggle,toggle:function(a,b,c){var d=typeof a=="boolean";f.isFunction(a)&&f.isFunction(b)?this._toggle.apply(this,arguments):a==null||d?this.each(function(){var b=d?a:f(this).is(":hidden");f(this)[b?"show":"hide"]()}):this.animate(cr("toggle",3),a,b,c);return this},fadeTo:function(a,b,c,d){return this.filter(":hidden").css("opacity",0).show().end().animate({opacity:b},a,c,d)},animate:function(a,b,c,d){var e=f.speed(b,c,d);if(f.isEmptyObject(a))return this.each(e.complete,[!1]);a=f.extend({},a);return this[e.queue===!1?"each":"queue"](function(){e.queue===!1&&f._mark(this);var b=f.extend({},e),c=this.nodeType===1,d=c&&f(this).is(":hidden"),g,h,i,j,k,l,m,n,o;b.animatedProperties={};for(i in a){g=f.camelCase(i),i!==g&&(a[g]=a[i],delete a[i]),h=a[g],f.isArray(h)?(b.animatedProperties[g]=h[1],h=a[g]=h[0]):b.animatedProperties[g]=b.specialEasing&&b.specialEasing[g]||b.easing||"swing";if(h==="hide"&&d||h==="show"&&!d)return b.complete.call(this);c&&(g==="height"||g==="width")&&(b.overflow=[this.style.overflow,this.style.overflowX,this.style.overflowY],f.css(this,"display")==="inline"&&f.css(this,"float")==="none"&&(f.support.inlineBlockNeedsLayout?(j=cs(this.nodeName),j==="inline"?this.style.display="inline-block":(this.style.display="inline",this.style.zoom=1)):this.style.display="inline-block"))}b.overflow!=null&&(this.style.overflow="hidden");for(i in a)k=new f.fx(this,b,i),h=a[i],cj.test(h)?k[h==="toggle"?d?"show":"hide":h]():(l=ck.exec(h),m=k.cur(),l?(n=parseFloat(l[2]),o=l[3]||(f.cssNumber[i]?"":"px"),o!=="px"&&(f.style(this,i,(n||1)+o),m=(n||1)/k.cur()*m,f.style(this,i,m+o)),l[1]&&(n=(l[1]==="-="?-1:1)*n+m),k.custom(m,n,o)):k.custom(m,h,""));return!0})},stop:function(a,b){a&&this.queue([]),this.each(function(){var a=f.timers,c=a.length;b||f._unmark(!0,this);while(c--)a[c].elem===this&&(b&&a[c](!0),a.splice(c,1))}),b||this.dequeue();return this}}),f.each({slideDown:cr("show",1),slideUp:cr("hide",1),slideToggle:cr("toggle",1),fadeIn:{opacity:"show"},fadeOut:{opacity:"hide"},fadeToggle:{opacity:"toggle"}},function(a,b){f.fn[a]=function(a,c,d){return this.animate(b,a,c,d)}}),f.extend({speed:function(a,b,c){var d=a&&typeof a=="object"?f.extend({},a):{complete:c||!c&&b||f.isFunction(a)&&a,duration:a,easing:c&&b||b&&!f.isFunction(b)&&b};d.duration=f.fx.off?0:typeof d.duration=="number"?d.duration:d.duration in f.fx.speeds?f.fx.speeds[d.duration]:f.fx.speeds._default,d.old=d.complete,d.complete=function(a){f.isFunction(d.old)&&d.old.call(this),d.queue!==!1?f.dequeue(this):a!==!1&&f._unmark(this)};return d},easing:{linear:function(a,b,c,d){return c+d*a},swing:function(a,b,c,d){return(-Math.cos(a*Math.PI)/2+.5)*d+c}},timers:[],fx:function(a,b,c){this.options=b,this.elem=a,this.prop=c,b.orig=b.orig||{}}}),f.fx.prototype={update:function(){this.options.step&&this.options.step.call(this.elem,this.now,this),(f.fx.step[this.prop]||f.fx.step._default)(this)},cur:function(){if(this.elem[this.prop]!=null&&(!this.elem.style||this.elem.style[this.prop]==null))return this.elem[this.prop];var a,b=f.css(this.elem,this.prop);return isNaN(a=parseFloat(b))?!b||b==="auto"?0:b:a},custom:function(a,b,c){function h(a){return d.step(a)}var d=this,e=f.fx,g;this.startTime=cn||cp(),this.start=a,this.end=b,this.unit=c||this.unit||(f.cssNumber[this.prop]?"":"px"),this.now=this.start,this.pos=this.state=0,h.elem=this.elem,h()&&f.timers.push(h)&&!cl&&(co?(cl=!0,g=function(){cl&&(co(g),e.tick())},co(g)):cl=setInterval(e.tick,e.interval))},show:function(){this.options.orig[this.prop]=f.style(this.elem,this.prop),this.options.show=!0,this.custom(this.prop==="width"||this.prop==="height"?1:0,this.cur()),f(this.elem).show()},hide:function(){this.options.orig[this.prop]=f.style(this.elem,this.prop),this.options.hide=!0,this.custom(this.cur(),0)},step:function(a){var b=cn||cp(),c=!0,d=this.elem,e=this.options,g,h;if(a||b>=e.duration+this.startTime){this.now=this.end,this.pos=this.state=1,this.update(),e.animatedProperties[this.prop]=!0;for(g in e.animatedProperties)e.animatedProperties[g]!==!0&&(c=!1);if(c){e.overflow!=null&&!f.support.shrinkWrapBlocks&&f.each(["","X","Y"],function(a,b){d.style["overflow"+b]=e.overflow[a]}),e.hide&&f(d).hide();if(e.hide||e.show)for(var i in e.animatedProperties)f.style(d,i,e.orig[i]);e.complete.call(d)}return!1}e.duration==Infinity?this.now=b:(h=b-this.startTime,this.state=h/e.duration,this.pos=f.easing[e.animatedProperties[this.prop]](this.state,h,0,1,e.duration),this.now=this.start+(this.end-this.start)*this.pos),this.update();return!0}},f.extend(f.fx,{tick:function(){for(var a=f.timers,b=0;b<a.length;++b)a[b]()||a.splice(b--,1);a.length||f.fx.stop()},interval:13,stop:function(){clearInterval(cl),cl=null},speeds:{slow:600,fast:200,_default:400},step:{opacity:function(a){f.style(a.elem,"opacity",a.now)},_default:function(a){a.elem.style&&a.elem.style[a.prop]!=null?a.elem.style[a.prop]=(a.prop==="width"||a.prop==="height"?Math.max(0,a.now):a.now)+a.unit:a.elem[a.prop]=a.now}}}),f.expr&&f.expr.filters&&(f.expr.filters.animated=function(a){return f.grep(f.timers,function(b){return a===b.elem}).length});var ct=/^t(?:able|d|h)$/i,cu=/^(?:body|html)$/i;"getBoundingClientRect"in c.documentElement?f.fn.offset=function(a){var b=this[0],c;if(a)return this.each(function(b){f.offset.setOffset(this,a,b)});if(!b||!b.ownerDocument)return null;if(b===b.ownerDocument.body)return f.offset.bodyOffset(b);try{c=b.getBoundingClientRect()}catch(d){}var e=b.ownerDocument,g=e.documentElement;if(!c||!f.contains(g,b))return c?{top:c.top,left:c.left}:{top:0,left:0};var h=e.body,i=cv(e),j=g.clientTop||h.clientTop||0,k=g.clientLeft||h.clientLeft||0,l=i.pageYOffset||f.support.boxModel&&g.scrollTop||h.scrollTop,m=i.pageXOffset||f.support.boxModel&&g.scrollLeft||h.scrollLeft,n=c.top+l-j,o=c.left+m-k;return{top:n,left:o}}:f.fn.offset=function(a){var b=this[0];if(a)return this.each(function(b){f.offset.setOffset(this,a,b)});if(!b||!b.ownerDocument)return null;if(b===b.ownerDocument.body)return f.offset.bodyOffset(b);f.offset.initialize();var c,d=b.offsetParent,e=b,g=b.ownerDocument,h=g.documentElement,i=g.body,j=g.defaultView,k=j?j.getComputedStyle(b,null):b.currentStyle,l=b.offsetTop,m=b.offsetLeft;while((b=b.parentNode)&&b!==i&&b!==h){if(f.offset.supportsFixedPosition&&k.position==="fixed")break;c=j?j.getComputedStyle(b,null):b.currentStyle,l-=b.scrollTop,m-=b.scrollLeft,b===d&&(l+=b.offsetTop,m+=b.offsetLeft,f.offset.doesNotAddBorder&&(!f.offset.doesAddBorderForTableAndCells||!ct.test(b.nodeName))&&(l+=parseFloat(c.borderTopWidth)||0,m+=parseFloat(c.borderLeftWidth)||0),e=d,d=b.offsetParent),f.offset.subtractsBorderForOverflowNotVisible&&c.overflow!=="visible"&&(l+=parseFloat(c.borderTopWidth)||0,m+=parseFloat(c.borderLeftWidth)||0),k=c}if(k.position==="relative"||k.position==="static")l+=i.offsetTop,m+=i.offsetLeft;f.offset.supportsFixedPosition&&k.position==="fixed"&&(l+=Math.max(h.scrollTop,i.scrollTop),m+=Math.max(h.scrollLeft,i.scrollLeft));return{top:l,left:m}},f.offset={initialize:function(){var a=c.body,b=c.createElement("div"),d,e,g,h,i=parseFloat(f.css(a,"marginTop"))||0,j="<div style='position:absolute;top:0;left:0;margin:0;border:5px solid #000;padding:0;width:1px;height:1px;'><div></div></div><table style='position:absolute;top:0;left:0;margin:0;border:5px solid #000;padding:0;width:1px;height:1px;' cellpadding='0' cellspacing='0'><tr><td></td></tr></table>";f.extend(b.style,{position:"absolute",top:0,left:0,margin:0,border:0,width:"1px",height:"1px",visibility:"hidden"}),b.innerHTML=j,a.insertBefore(b,a.firstChild),d=b.firstChild,e=d.firstChild,h=d.nextSibling.firstChild.firstChild,this.doesNotAddBorder=e.offsetTop!==5,this.doesAddBorderForTableAndCells=h.offsetTop===5,e.style.position="fixed",e.style.top="20px",this.supportsFixedPosition=e.offsetTop===20||e.offsetTop===15,e.style.position=e.style.top="",d.style.overflow="hidden",d.style.position="relative",this.subtractsBorderForOverflowNotVisible=e.offsetTop===-5,this.doesNotIncludeMarginInBodyOffset=a.offsetTop!==i,a.removeChild(b),f.offset.initialize=f.noop},bodyOffset:function(a){var b=a.offsetTop,c=a.offsetLeft;f.offset.initialize(),f.offset.doesNotIncludeMarginInBodyOffset&&(b+=parseFloat(f.css(a,"marginTop"))||0,c+=parseFloat(f.css(a,"marginLeft"))||0);return{top:b,left:c}},setOffset:function(a,b,c){var d=f.css(a,"position");d==="static"&&(a.style.position="relative");var e=f(a),g=e.offset(),h=f.css(a,"top"),i=f.css(a,"left"),j=(d==="absolute"||d==="fixed")&&f.inArray("auto",[h,i])>-1,k={},l={},m,n;j?(l=e.position(),m=l.top,n=l.left):(m=parseFloat(h)||0,n=parseFloat(i)||0),f.isFunction(b)&&(b=b.call(a,c,g)),b.top!=null&&(k.top=b.top-g.top+m),b.left!=null&&(k.left=b.left-g.left+n),"using"in b?b.using.call(a,k):e.css(k)}},f.fn.extend({position:function(){if(!this[0])return null;var a=this[0],b=this.offsetParent(),c=this.offset(),d=cu.test(b[0].nodeName)?{top:0,left:0}:b.offset();c.top-=parseFloat(f.css(a,"marginTop"))||0,c.left-=parseFloat(f.css(a,"marginLeft"))||0,d.top+=parseFloat(f.css(b[0],"borderTopWidth"))||0,d.left+=parseFloat(f.css(b[0],"borderLeftWidth"))||0;return{top:c.top-d.top,left:c.left-d.left}},offsetParent:function(){return this.map(function(){var a=this.offsetParent||c.body;while(a&&!cu.test(a.nodeName)&&f.css(a,"position")==="static")a=a.offsetParent;return a})}}),f.each(["Left","Top"],function(a,c){var d="scroll"+c;f.fn[d]=function(c){var e,g;if(c===b){e=this[0];if(!e)return null;g=cv(e);return g?"pageXOffset"in g?g[a?"pageYOffset":"pageXOffset"]:f.support.boxModel&&g.document.documentElement[d]||g.document.body[d]:e[d]}return this.each(function(){g=cv(this),g?g.scrollTo(a?f(g).scrollLeft():c,a?c:f(g).scrollTop()):this[d]=c})}}),f.each(["Height","Width"],function(a,c){var d=c.toLowerCase();f.fn["inner"+c]=function(){var a=this[0];return a&&a.style?parseFloat(f.css(a,d,"padding")):null},f.fn["outer"+c]=function(a){var b=this[0];return b&&b.style?parseFloat(f.css(b,d,a?"margin":"border")):null},f.fn[d]=function(a){var e=this[0];if(!e)return a==null?null:this;if(f.isFunction(a))return this.each(function(b){var c=f(this);c[d](a.call(this,b,c[d]()))});if(f.isWindow(e)){var g=e.document.documentElement["client"+c];return e.document.compatMode==="CSS1Compat"&&g||e.document.body["client"+c]||g}if(e.nodeType===9)return Math.max(e.documentElement["client"+c],e.body["scroll"+c],e.documentElement["scroll"+c],e.body["offset"+c],e.documentElement["offset"+c]);if(a===b){var h=f.css(e,d),i=parseFloat(h);return f.isNaN(i)?h:i}return this.css(d,typeof a=="string"?a:a+"px")}}),a.jQuery=a.$=f})(window);
/*
 *	lib/js/lib/history/history.min.js
 *//*
 * jQuery hashchange event - v1.3 - 7/21/2010
 * http://benalman.com/projects/jquery-hashchange-plugin/
 * 
 * Copyright (c) 2010 "Cowboy" Ben Alman
 * Dual licensed under the MIT and GPL licenses.
 * http://benalman.com/about/license/
 */
(function($,e,b){var c="hashchange",h=document,f,g=$.event.special,i=h.documentMode,d="on"+c in e&&(i===b||i>7);function a(j){j=j||location.href;return"#"+j.replace(/^[^#]*#?(.*)$/,"$1")}$.fn[c]=function(j){return j?this.bind(c,j):this.trigger(c)};$.fn[c].delay=50;g[c]=$.extend(g[c],{setup:function(){if(d){return false}$(f.start)},teardown:function(){if(d){return false}$(f.stop)}});f=(function(){var j={},p,m=a(),k=function(q){return q},l=k,o=k;j.start=function(){p||n()};j.stop=function(){p&&clearTimeout(p);p=b};function n(){var r=a(),q=o(m);if(r!==m){l(m=r,q);$(e).trigger(c)}else{if(q!==m){location.href=location.href.replace(/#.*/,"")+q}}p=setTimeout(n,$.fn[c].delay)}$.browser.msie&&!d&&(function(){var q,r;j.start=function(){if(!q){r=$.fn[c].src;r=r&&r+a();q=$('<iframe tabindex="-1" title="empty"/>').hide().one("load",function(){r||l(a());n()}).attr("src",r||"javascript:0").insertAfter("body")[0].contentWindow;h.onpropertychange=function(){try{if(event.propertyName==="title"){q.document.title=h.title}}catch(s){}}}};j.stop=k;o=function(){return a(q.location.href)};l=function(v,s){var u=q.document,t=$.fn[c].domain;if(v!==s){u.title=h.title;u.open();t&&u.write('<script>document.domain="'+t+'"<\/script>');u.close();q.location.hash=v}}})();return j})()})(jQuery,this);

// manage history
// load pages via ajax
// setup the history adapter
// if settings no_history is set, no history will be bound
// this can be used to make it work with legacy

$(document).bind('ready', function() {
	// standard page openener
	$(window).bind('hashchange', function() {
		if(wn.settings.no_history) 
			return;

		// load the state on the browser	
		wn.page.set(location.hash);
	});	
})

/*
 *	lib/js/core.min.js
 */
/*
 *	lib/js/wn/class.js
 */;(function(){var initializing=false,fnTest=/xyz/.test(function(){xyz;})?/\b_super\b/:/.*/;this.Class=function(){};Class.extend=function(prop){var _super=this.prototype;initializing=true;var prototype=new this();initializing=false;for(var name in prop){prototype[name]=typeof prop[name]=="function"&&typeof _super[name]=="function"&&fnTest.test(prop[name])?(function(name,fn){return function(){var tmp=this._super;this._super=_super[name];var ret=fn.apply(this,arguments);this._super=tmp;return ret;};})(name,prop[name]):prop[name];}
function Class(){if(!initializing&&this.init)
this.init.apply(this,arguments);}
Class.prototype=prototype;Class.prototype.constructor=Class;Class.extend=arguments.callee;return Class;};})();
/*
 *	lib/js/wn/provide.js
 */
if(!window.wn)wn={}
wn.provide=function(namespace){var nsl=namespace.split('.');var l=nsl.length;var parent=window;for(var i=0;i<l;i++){var n=nsl[i];if(!parent[n]){parent[n]={}}
parent=parent[n];}}
wn.provide('wn.settings');wn.provide('wn.ui');
/*
 *	lib/js/wn/xmlhttp.js
 */
wn.xmlhttp={request:function(){if(window.XMLHttpRequest)
return new XMLHttpRequest();else if(window.ActiveXObject)
return new ActiveXObject("MsXml2.XmlHttp");},complete:function(req,callback,url){if(req.status==200||req.status==304){callback(req.responseText);}else{alert(url+' request error: '+req.statusText+' ('+req.status+')');}},get:function(url,callback,args,async){if(async===null)async=true;var req=wn.xmlhttp.request();req.onreadystatechange=function(){if(req.readyState==4){wn.xmlhttp.complete(req,callback,url)}}
var sep=((args&&args.indexOf('?'))==-1)?'?':'&';var u=args?(url+sep+args):url;req.open('GET',u,async);req.send(null);if(!async){wn.xmlhttp.complete(req,callback,url)}}}
/*
 *	lib/js/wn/versions.js
 */
wn.versions={check:function(){if(localStorage){if(window._version_number==-1||parseInt(localStorage._version_number)!=parseInt(window._version_number)){var localversion=localStorage._version_number;localStorage.clear();console.log("Cache cleared - version: "+localversion
+' to '+_version_number)}
localStorage.setItem('_version_number',window._version_number);}}}
/*
 *	lib/js/wn/assets.js
 */
wn.assets={executed_:{},exists:function(src){if('localStorage'in window&&localStorage.getItem(src))
return true},add:function(src,txt){if('localStorage'in window){localStorage.setItem(src,txt);}},get:function(src){return localStorage.getItem(src);},extn:function(src){if(src.indexOf('?')!=-1){src=src.split('?').slice(-1)[0];}
return src.split('.').slice(-1)[0];},load:function(src){var t=src;wn.xmlhttp.get(t,function(txt){wn.assets.add(src,txt);},'q='+Math.floor(Math.random()*1000),false)},execute:function(src){if(!wn.assets.exists(src)){wn.assets.load(src);}
var type=wn.assets.extn(src);if(wn.assets.handler[type]){wn.assets.handler[type](wn.assets.get(src),src);wn.assets.executed_[src]=1;}},handler:{js:function(txt,src){wn.dom.eval(txt);},css:function(txt,src){var se=document.createElement('style');se.type="text/css";if(se.styleSheet){se.styleSheet.cssText=txt;}else{se.appendChild(document.createTextNode(txt));}
document.getElementsByTagName('head')[0].appendChild(se);},cgi:function(txt,src){wn.dom.eval(txt)}}}
/*
 *	lib/js/wn/require.js
 */
wn.require=function(items){if(typeof items==="string"){items=[items];}
var l=items.length;for(var i=0;i<l;i++){var src=items[i];if(!(src in wn.assets.executed_)){wn.assets.execute(src);}}}
/*
 *	lib/js/wn/dom.js
 */
wn.provide('wn.dom');wn.dom.by_id=function(id){return document.getElementById(id);}
wn.dom.eval=function(txt){var el=document.createElement('script');el.appendChild(document.createTextNode(txt));document.getElementsByTagName('head')[0].appendChild(el);}
wn.dom.add=function(parent,newtag,className,cs,innerHTML,onclick){if(parent&&parent.substr)parent=wn.dom.by_id(parent);var c=document.createElement(newtag);if(parent)
parent.appendChild(c);if(className){if(newtag.toLowerCase()=='img')
c.src=className
else
c.className=className;}
if(cs)wn.dom.css(c,cs);if(innerHTML)c.innerHTML=innerHTML;if(onclick)c.onclick=onclick;return c;}
wn.dom.css=function(ele,s){if(ele&&s){for(var i in s)ele.style[i]=s[i];};return ele;}
wn.dom.hide=function(ele){ele.style.display='none';}
wn.dom.show=function(ele,value){if(!value)value='block';ele.style.display=value;}
/*
 *	lib/js/wn/page.js
 */
wn.page={set:function(src){var new_selection=$('.inner div.content[_src="'+src+'"]');if(!new_selection.length){wn.assets.execute(src);new_selection=$('.inner div.content[_src="'+src+'"]');}
$('.inner .current_page').removeClass('current_page');new_selection.addClass('current_page');var title=$('nav ul li a[href*="'+src+'"]').attr('title')||'No Title'
state=window.location.hash;if(state!=src){window.location.hash=state;}
else{document.title=title;}}}
/*
 *	lib/js/lib/json2.js
 */
var JSON;if(!JSON){JSON={};}
(function(){"use strict";function f(n){return n<10?'0'+n:n;}
if(typeof Date.prototype.toJSON!=='function'){Date.prototype.toJSON=function(key){return isFinite(this.valueOf())?this.getUTCFullYear()+'-'+
f(this.getUTCMonth()+1)+'-'+
f(this.getUTCDate())+'T'+
f(this.getUTCHours())+':'+
f(this.getUTCMinutes())+':'+
f(this.getUTCSeconds())+'Z':null;};String.prototype.toJSON=Number.prototype.toJSON=Boolean.prototype.toJSON=function(key){return this.valueOf();};}
var cx=/[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,escapable=/[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,gap,indent,meta={'\b':'\\b','\t':'\\t','\n':'\\n','\f':'\\f','\r':'\\r','"':'\\"','\\':'\\\\'},rep;function quote(string){escapable.lastIndex=0;return escapable.test(string)?'"'+string.replace(escapable,function(a){var c=meta[a];return typeof c==='string'?c:'\\u'+('0000'+a.charCodeAt(0).toString(16)).slice(-4);})+'"':'"'+string+'"';}
function str(key,holder){var i,k,v,length,mind=gap,partial,value=holder[key];if(value&&typeof value==='object'&&typeof value.toJSON==='function'){value=value.toJSON(key);}
if(typeof rep==='function'){value=rep.call(holder,key,value);}
switch(typeof value){case'string':return quote(value);case'number':return isFinite(value)?String(value):'null';case'boolean':case'null':return String(value);case'object':if(!value){return'null';}
gap+=indent;partial=[];if(Object.prototype.toString.apply(value)==='[object Array]'){length=value.length;for(i=0;i<length;i+=1){partial[i]=str(i,value)||'null';}
v=partial.length===0?'[]':gap?'[\n'+gap+partial.join(',\n'+gap)+'\n'+mind+']':'['+partial.join(',')+']';gap=mind;return v;}
if(rep&&typeof rep==='object'){length=rep.length;for(i=0;i<length;i+=1){if(typeof rep[i]==='string'){k=rep[i];v=str(k,value);if(v){partial.push(quote(k)+(gap?': ':':')+v);}}}}else{for(k in value){if(Object.prototype.hasOwnProperty.call(value,k)){v=str(k,value);if(v){partial.push(quote(k)+(gap?': ':':')+v);}}}}
v=partial.length===0?'{}':gap?'{\n'+gap+partial.join(',\n'+gap)+'\n'+mind+'}':'{'+partial.join(',')+'}';gap=mind;return v;}}
if(typeof JSON.stringify!=='function'){JSON.stringify=function(value,replacer,space){var i;gap='';indent='';if(typeof space==='number'){for(i=0;i<space;i+=1){indent+=' ';}}else if(typeof space==='string'){indent=space;}
rep=replacer;if(replacer&&typeof replacer!=='function'&&(typeof replacer!=='object'||typeof replacer.length!=='number')){throw new Error('JSON.stringify');}
return str('',{'':value});};}
if(typeof JSON.parse!=='function'){JSON.parse=function(text,reviver){var j;function walk(holder,key){var k,v,value=holder[key];if(value&&typeof value==='object'){for(k in value){if(Object.prototype.hasOwnProperty.call(value,k)){v=walk(value,k);if(v!==undefined){value[k]=v;}else{delete value[k];}}}}
return reviver.call(holder,key,value);}
text=String(text);cx.lastIndex=0;if(cx.test(text)){text=text.replace(cx,function(a){return'\\u'+
('0000'+a.charCodeAt(0).toString(16)).slice(-4);});}
if(/^[\],:{}\s]*$/.test(text.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g,'@').replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g,']').replace(/(?:^|:|,)(?:\s*\[)+/g,''))){j=eval('('+text+')');return typeof reviver==='function'?walk({'':j},''):j;}
throw new SyntaxError('JSON.parse');};}}());
/*
 *	lib/js/core.js
 */
wn.versions.check();$(document).bind('ready',function(){var base=window.location.href.split('#')[0];$.each($('a[softlink!="false"]'),function(i,v){if(v.href.substr(0,base.length)==base){var path=(v.href.substr(base.length));if(path.substr(0,1)!='#'){v.href=base+'#'+path;}}});if(!wn.settings.no_history&&window.location.hash){wn.page.set(window.location.hash.substr(1));}});
/*
 *	lib/js/legacy/globals.js
 */
wn.provide('wn.widgets.form');wn.provide('wn.widgets.report');wn.provide('wn.utils');wn.provide('wn.model');wn.provide('wn.profile');wn.provide('wn.session');wn.provide('_f');wn.provide('_p');wn.provide('_r');wn.provide('_c');wn.provide('_e');wn.provide('_startup_data')
wn.settings.no_history=1;var NEWLINE='\n';var login_file='';var version='v170';var profile=null;var session={};var is_testing=false;var user=null;var user_defaults=null;var user_roles=null;var user_fullname=null;var user_email=null;var user_img={};var home_page=null;var hide_autosuggest=null;var page_body=null;var pscript={};var selector=null;var top_index=91;var _f={};var _p={};var _e={};var _r={};var FILTER_SEP='\1';var _c={};var widget_files={'_f.FrmContainer':'form.compressed.js','_c.CalendarPopup':'widgets/form/date_picker.js','_r.ReportContainer':'report.compressed.js','_p.PrintQuery':'widgets/print_query.js','Calendar':'widgets/calendar.js','Recommendation':'widgets/recommend.js','RatingWidget':'widgets/rating.js'}
var frms={};var cur_frm=null;var pscript={};var validated=true;var validation_message='';var tinymce_loaded=null;var cur_autosug=null;if(!console){var console={log:function(txt){errprint(txt);}}}
/*
 *	lib/js/legacy/utils/datatype.js
 */
var startup_list=[];wn.utils.full_name=function(fn,ln){return fn+(ln?' ':'')+(ln?ln:'')}
function fmt_money(v){if(v==null||v=='')return'0.00';v=(v+'').replace(/,/g,'');v=parseFloat(v);if(isNaN(v)){return'';}else{var cp=wn.control_panel;var val=2;if(cp.currency_format=='Millions')val=3;v=v.toFixed(2);var delimiter=",";amount=v+'';var a=amount.split('.',2)
var d=a[1];var i=parseInt(a[0]);if(isNaN(i)){return'';}
var minus='';if(v<0){minus='-';}
i=Math.abs(i);var n=new String(i);var a=[];if(n.length>3)
{var nn=n.substr(n.length-3);a.unshift(nn);n=n.substr(0,n.length-3);while(n.length>val)
{var nn=n.substr(n.length-val);a.unshift(nn);n=n.substr(0,n.length-val);}}
if(n.length>0){a.unshift(n);}
n=a.join(delimiter);if(d.length<1){amount=n;}
else{amount=n+'.'+d;}
amount=minus+amount;return amount;}}
function toTitle(str){var word_in=str.split(" ");var word_out=[];for(w in word_in){word_out[w]=word_in[w].charAt(0).toUpperCase()+word_in[w].slice(1);}
return word_out.join(" ");}
function is_null(v){if(v==null){return 1}else if(v==0){if((v+'').length>=1)return 0;else return 1;}else{return 0}}
function $s(ele,v,ftype,fopt){if(v==null)v='';if(ftype=='Text'||ftype=='Small Text'){ele.innerHTML=v?v.replace(/\n/g,'<br>'):'';}else if(ftype=='Date'){v=dateutil.str_to_user(v);if(v==null)v=''
ele.innerHTML=v;}else if(ftype=='Link'&&fopt){ele.innerHTML='';doc_link(ele,fopt,v);}else if(ftype=='Currency'){ele.style.textAlign='right';if(is_null(v))
ele.innerHTML='';else
ele.innerHTML=fmt_money(v);}else if(ftype=='Int'){ele.style.textAlign='right';ele.innerHTML=v;}else if(ftype=='Check'){if(v)ele.innerHTML='<img src="lib/images/ui/tick.gif">';else ele.innerHTML='';}else{ele.innerHTML=v;}}
function clean_smart_quotes(s){if(s){s=s.replace(/\u2018/g,"'");s=s.replace(/\u2019/g,"'");s=s.replace(/\u201c/g,'"');s=s.replace(/\u201d/g,'"');s=s.replace(/\u2013/g,'-');s=s.replace(/\u2014/g,'--');}
return s;}
function copy_dict(d){var n={};for(var k in d)n[k]=d[k];return n;}
function $p(ele,top,left){ele.style.position='absolute';ele.style.top=top+'px';ele.style.left=left+'px';}
function replace_newlines(t){return t?t.replace(/\n/g,'<br>'):'';}
function cstr(s){if(s==null)return'';return s+'';}
function flt(v,decimals){if(v==null||v=='')return 0;v=(v+'').replace(/,/g,'');v=parseFloat(v);if(isNaN(v))
v=0;if(decimals!=null)
return v.toFixed(decimals);return v;}
function esc_quotes(s){if(s==null)s='';return s.replace(/'/,"\'");}
var crop=function(s,len){if(s.length>len)
return s.substr(0,len-3)+'...';else
return s;}
var strip=function(s,chars){var s=lstrip(s,chars)
s=rstrip(s,chars);return s;}
var lstrip=function(s,chars){if(!chars)chars=['\n','\t',' '];var first_char=s.substr(0,1);while(in_list(chars,first_char)){var s=s.substr(1);first_char=s.substr(0,1);}
return s;}
var rstrip=function(s,chars){if(!chars)chars=['\n','\t',' '];var last_char=s.substr(s.length-1);while(in_list(chars,last_char)){var s=s.substr(0,this.length-1);last_char=s.substr(this.length-1);}
return s;}
function repl_all(s,s1,s2){var idx=s.indexOf(s1);while(idx!=-1){s=s.replace(s1,s2);idx=s.indexOf(s1);}
return s;}
function repl(s,dict){if(s==null)return'';for(key in dict)s=repl_all(s,'%('+key+')s',dict[key]);return s;}
function keys(obj){var mykeys=[];for(key in obj)mykeys[mykeys.length]=key;return mykeys;}
function values(obj){var myvalues=[];for(key in obj)myvalues[myvalues.length]=obj[key];return myvalues;}
function in_list(list,item){for(var i=0;i<list.length;i++)
if(list[i]==item)return true;return false;}
function has_common(list1,list2){if(!list1||!list2)return false;for(var i=0;i<list1.length;i++){if(in_list(list2,list1[i]))return true;}
return false;}
var inList=in_list;function add_lists(l1,l2){var l=[];for(var k in l1)l.push(l1[k]);for(var k in l2)l.push(l2[k]);return l;}
function docstring(obj){var l=[];for(key in obj){var v=obj[key];if(v!=null){if(typeof(v)==typeof(1)){l[l.length]="'"+key+"':"+(v+'');}else{v=v+'';l[l.length]="'"+key+"':'"+v.replace(/'/g,"\\'").replace(/\n/g,"\\n")+"'";}}}
return"{"+l.join(',')+'}';}
function DocLink(p,doctype,name,onload){var a=$a(p,'span','link_type');a.innerHTML=a.dn=name;a.dt=doctype;a.onclick=function(){loaddoc(this.dt,this.dn,onload)};return a;}
var doc_link=DocLink;var known_numbers={0:'zero',1:'one',2:'two',3:'three',4:'four',5:'five',6:'six',7:'seven',8:'eight',9:'nine',10:'ten',11:'eleven',12:'twelve',13:'thirteen',14:'fourteen',15:'fifteen',16:'sixteen',17:'seventeen',18:'eighteen',19:'nineteen',20:'twenty',30:'thirty',40:'forty',50:'fifty',60:'sixty',70:'seventy',80:'eighty',90:'ninety'}
function in_words(n){var is_million=wn.control_panel.currency_format=='Millions'?1:0;n=cint(n)
if(known_numbers[n])return known_numbers[n];var bestguess=n+'';var remainder=0
if(n<=20)
alert('Error while converting to words');else if(n<100){return in_words(Math.floor(n/10)*10)+'-'+in_words(n%10);}else if(n<1000){bestguess=in_words(Math.floor(n/100))+' '+'hundred';remainder=n%100;}else if(!is_million){if(n<100000){bestguess=in_words(Math.floor(n/1000))+' '+'thousand';remainder=n%1000;}else if(n<10000000){bestguess=in_words(Math.floor(n/100000))+' '+'lakh';remainder=n%100000;}else{bestguess=in_words(Math.floor(n/10000000))+' '+'crore'
remainder=n%10000000}}else{if(n<1000000){bestguess=in_words(Math.floor(n/1000))+' '+'thousand';remainder=n%1000;}else if(n<1000000000){bestguess=in_words(Math.floor(n/1000000))+' '+'million';remainder=n%1000000;}else{bestguess=in_words(Math.floor(n/1000000000))+' '+'billion'
remainder=n%1000000000}}
if(remainder){if(remainder>=100)comma=','
else comma=''
return bestguess+comma+' '+in_words(remainder);}else{return bestguess;}}
function roundNumber(num,dec){var result=Math.round(num*Math.pow(10,dec))/Math.pow(10,dec);return result;}
/*
 *	lib/js/legacy/utils/browser_detect.js
 */
var appVer=navigator.appVersion.toLowerCase();var is_minor=parseFloat(appVer);var is_major=parseInt(is_minor);var iePos=appVer.indexOf('msie');if(iePos!=-1){is_minor=parseFloat(appVer.substring(iePos+5,appVer.indexOf(';',iePos)))
is_major=parseInt(is_minor);}
var isIE=(iePos!=-1);var isIE6=(isIE&&is_major<=6);var isIE7=(isIE&&is_major>=7);if(/Firefox[\/\s](\d+\.\d+)/.test(navigator.userAgent)){var isFF=1;var ffversion=new Number(RegExp.$1)
if(ffversion>=3)var isFF3=1;else if(ffversion>=2)var isFF2=1;else if(ffversion>=1)var isFF1=1;}
var isSafari=navigator.userAgent.indexOf('Safari')!=-1?1:0;var isChrome=navigator.userAgent.indexOf('Chrome')!=-1?1:0;
/*
 *	lib/js/legacy/utils/datetime.js
 */
function same_day(d1,d2){if(d1.getFullYear()==d2.getFullYear()&&d1.getMonth()==d2.getMonth()&&d1.getDate()==d2.getDate())return true;else return false;}
var month_list=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];var month_last={1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
var month_list_full=['January','February','March','April','May','June','July','August','September','October','November','December'];var week_list=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];var week_list_full=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];function int_to_str(i,len){i=''+i;if(i.length<len)for(c=0;c<(len-i.length);c++)i='0'+i;return i}
wn.datetime={str_to_obj:function(d){if(!d)return new Date();var tm=[null,null];if(d.search(' ')!=-1){var tm=d.split(' ')[1].split(':');var d=d.split(' ')[0];}
if(d.search('-')!=-1){var t=d.split('-');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else if(d.search('/')!=-1){var t=d.split('/');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else{return new Date();}},obj_to_str:function(d){return d.getFullYear()+'-'+int_to_str(d.getMonth()+1,2)+'-'+int_to_str(d.getDate(),2);},obj_to_user:function(d){return dateutil.str_to_user(dateutil.obj_to_str(d));},get_diff:function(d1,d2){return((d1-d2)/86400000);},add_days:function(d,days){d.setTime(d.getTime()+(days*24*60*60*1000));return d},add_months:function(d,months){dt=dateutil.str_to_obj(d)
new_dt=new Date(dt.getFullYear(),dt.getMonth()+months,dt.getDate())
if(new_dt.getDate()!=dt.getDate()){return dateutil.month_end(new Date(dt.getFullYear(),dt.getMonth()+months,1))}
return dateutil.obj_to_str(new_dt);},month_start:function(){var d=new Date();return d.getFullYear()+'-'+int_to_str(d.getMonth()+1,2)+'-01';},month_end:function(d){if(!d)var d=new Date();var m=d.getMonth()+1;var y=d.getFullYear();last_date=month_last[m];if(m==2&&(y%4)==0&&((y%100)!=0||(y%400)==0))
last_date=29;return y+'-'+int_to_str(m,2)+'-'+last_date;},get_user_fmt:function(){var t=wn.control_panel.date_format;if(!t)t='dd-mm-yyyy';return t;},str_to_user:function(val,no_time_str){var user_fmt=dateutil.get_user_fmt();var time_str='';if(val==null||val=='')return null;if(val.search(':')!=-1){var tmp=val.split(' ');if(tmp[1])
time_str=' '+tmp[1];var d=tmp[0];}else{var d=val;}
if(no_time_str)time_str='';d=d.split('-');if(d.length==3){if(user_fmt=='dd-mm-yyyy')
val=d[2]+'-'+d[1]+'-'+d[0]+time_str;else if(user_fmt=='dd/mm/yyyy')
val=d[2]+'/'+d[1]+'/'+d[0]+time_str;else if(user_fmt=='yyyy-mm-dd')
val=d[0]+'-'+d[1]+'-'+d[2]+time_str;else if(user_fmt=='mm/dd/yyyy')
val=d[1]+'/'+d[2]+'/'+d[0]+time_str;else if(user_fmt=='mm-dd-yyyy')
val=d[1]+'-'+d[2]+'-'+d[0]+time_str;}
return val;},full_str:function(){var d=new Date();return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()+' '
+d.getHours()+':'+d.getMinutes()+':'+d.getSeconds();},user_to_str:function(d){var user_fmt=this.get_user_fmt();if(user_fmt=='dd-mm-yyyy'){var d=d.split('-');return d[2]+'-'+d[1]+'-'+d[0];}
else if(user_fmt=='dd/mm/yyyy'){var d=d.split('/');return d[2]+'-'+d[1]+'-'+d[0];}
else if(user_fmt=='yyyy-mm-dd'){return d;}
else if(user_fmt=='mm/dd/yyyy'){var d=d.split('/');return d[2]+'-'+d[0]+'-'+d[1];}
else if(user_fmt=='mm-dd-yyyy'){var d=d.split('-');return d[2]+'-'+d[0]+'-'+d[1];}},global_date_format:function(d){if(d.substr)d=this.str_to_obj(d);return d.getDate()+' '+month_list_full[d.getMonth()]+' '+d.getFullYear();},get_today:function(){var today=new Date();var m=(today.getMonth()+1)+'';if(m.length==1)m='0'+m;var d=today.getDate()+'';if(d.length==1)d='0'+d;return today.getFullYear()+'-'+m+'-'+d;},get_cur_time:function(){var d=new Date();var hh=d.getHours()+''
var mm=cint(d.getMinutes()/5)*5+''
return(hh.length==1?'0'+hh:hh)+':'+(mm.length==1?'0'+mm:mm);}}
wn.datetime.only_date=function(val){if(val==null||val=='')return null;if(val.search(':')!=-1){var tmp=val.split(' ');var d=tmp[0].split('-');}else{var d=val.split('-');}
if(d.length==3)
val=d[2]+'-'+d[1]+'-'+d[0];return val;}
wn.datetime.time_to_ampm=function(v){if(!v){var d=new Date();var t=[d.getHours(),cint(d.getMinutes()/5)*5]}else{var t=v.split(':');}
if(t.length!=2){show_alert('[set_time] Incorect time format');return;}
if(cint(t[0])==0)var ret=['12',t[1],'AM'];else if(cint(t[0])<12)var ret=[cint(t[0])+'',t[1],'AM'];else if(cint(t[0])==12)var ret=['12',t[1],'PM'];else var ret=[(cint(t[0])-12)+'',t[1],'PM'];return ret;}
wn.datetime.time_to_hhmm=function(hh,mm,am){if(am=='AM'&&hh=='12'){hh='00';}else if(am=='PM'&&hh!='12'){hh=cint(hh)+12;}
return hh+':'+mm;}
function prettyDate(time){if(!time)return''
var date=new Date((time||"").replace(/-/g,"/").replace(/[TZ]/g," ").replace(/\.[0-9]*/,"")),diff=(((new Date()).getTime()-date.getTime())/1000),day_diff=Math.floor(diff/86400);if(isNaN(day_diff)||day_diff<0)
return'';return day_diff==0&&(diff<60&&"just now"||diff<120&&"1 minute ago"||diff<3600&&Math.floor(diff/60)+" minutes ago"||diff<7200&&"1 hour ago"||diff<86400&&Math.floor(diff/3600)+" hours ago")||day_diff==1&&"Yesterday"||day_diff<7&&day_diff+" days ago"||day_diff<31&&Math.ceil(day_diff/7)+" weeks ago"||day_diff<365&&Math.ceil(day_diff/30)+" months ago"||"more than "+Math.floor(day_diff/365)+" year(s) ago";}
if(typeof jQuery!="undefined")
jQuery.fn.prettyDate=function(){return this.each(function(){var date=prettyDate(this.title);if(date)
jQuery(this).text(date);});};var comment_when=prettyDate;wn.datetime.comment_when=prettyDate;var date=dateutil=wn.datetime;var get_today=wn.datetime.get_today
var time_to_ampm=wn.datetime.time_to_ampm;var time_to_hhmm=wn.datetime.time_to_hhmm;var only_date=wn.datetime.only_date;
/*
 *	lib/js/legacy/utils/dom.js
 */
wn.dom.set_unique_id=function(ele){var id='unique-'+wn.dom.id_count;ele.setAttribute('id',id);wn.dom.id_count++;return id;}
wn.tinymce={add_simple:function(ele,height){if(ele.myid){tinyMCE.execCommand('mceAddControl',true,ele.myid);return;}
ele.myid=wn.dom.set_unique_id(ele);$(ele).tinymce({script_url:'lib/js/legacy/tiny_mce_33/tiny_mce.js',height:height?height:'200px',theme:"advanced",theme_advanced_buttons1:"bold,italic,underline,separator,strikethrough,justifyleft,justifycenter,justifyright,justifyfull,bullist,numlist,outdent,indent,link,unlink,forecolor,backcolor,code,",theme_advanced_buttons2:"",theme_advanced_buttons3:"",theme_advanced_toolbar_location:"top",theme_advanced_toolbar_align:"left",theme_advanced_path:false,theme_advanced_resizing:false});},remove:function(ele){tinyMCE.execCommand('mceRemoveControl',true,ele.myid);},get_value:function(ele){return tinymce.get(ele.myid).getContent();}}
wn.ele={link:function(args){var span=$a(args.parent,'span','link_type',args.style);span.loading_img=$a(args.parent,'img','',{margin:'0px 4px -2px 4px',display:'none'});span.loading_img.src='lib/images/ui/button-load.gif';span.innerHTML=args.label;span.user_onclick=args.onclick;span.onclick=function(){if(!this.disabled)this.user_onclick(this);}
span.set_working=function(){this.disabled=1;$di(this.loading_img);}
span.done_working=function(){this.disabled=0;$dh(this.loading_img);}
return span;}}
function $ln(parent,label,onclick,style){return wn.ele.link({parent:parent,label:label,onclick:onclick,style:style})}
function $btn(parent,label,onclick,style,css_class,is_ajax){wn.require('lib/js/wn/ui/button.js');if(css_class==='green')css_class='primary';return new wn.ui.Button({parent:parent,label:label,onclick:onclick,style:style,is_ajax:is_ajax,css_class:css_class}).btn;}
$item_normal=function(ele){$y(ele,{padding:'6px 8px',cursor:'pointer',marginRight:'8px',whiteSpace:'nowrap',overflow:'hidden',borderBottom:'1px solid #DDD'});$bg(ele,'#FFF');$fg(ele,'#000');}
$item_active=function(ele){$bg(ele,'#FE8');$fg(ele,'#000');}
$item_selected=function(ele){$bg(ele,'#777');$fg(ele,'#FFF');}
$item_pressed=function(ele){$bg(ele,'#F90');$fg(ele,'#FFF');};(function($){$.fn.set_working=function(){var ele=this.get(0);if(ele.loading_img){$di(ele.loading_img)}else{ele.disabled=1;ele.loading_img=$a(ele.parentNode,'img','',{marginLeft:'4px',marginBottom:'-2px',display:'inline'});ele.loading_img.src='lib/images/ui/button-load.gif';}}
$.fn.done_working=function(){var ele=this.get(0);ele.disabled=0;if(ele.loading_img){$dh(ele.loading_img)};}})(jQuery);function set_opacity(ele,ieop){var op=ieop/100;if(ele.filters){try{ele.filters.item("DXImageTransform.Microsoft.Alpha").opacity=ieop;}catch(e){ele.style.filter='progid:DXImageTransform.Microsoft.Alpha(opacity='+ieop+')';}}else{ele.style.opacity=op;}}
$br=function(ele,r,corners){if(corners){var cl=['top-left','top-right','bottom-right','bottom-left'];for(var i=0;i<4;i++){if(corners[i]){$(ele).css('-moz-border-radius-'+cl[i].replace('-',''),r).css('-webkit-'+cl[i]+'-border-radius',r);}}}else{$(ele).css('-moz-border-radius',r).css('-webkit-border-radius',r).css('border-radius',r);}}
$bs=function(ele,r){$(ele).css('-moz-box-shadow',r).css('-webkit-box-shadow',r).css('box-shadow',r);}
function empty_select(s){if(s.custom_select){s.empty();return;}
if(s.inp)s=s.inp;if(s){var tmplen=s.length;for(var i=0;i<tmplen;i++)s.options[0]=null;}}
function sel_val(s){if(s.custom_select){return s.inp.value?s.inp.value:'';}
if(s.inp)s=s.inp;try{if(s.selectedIndex<s.options.length)return s.options[s.selectedIndex].value;else return'';}catch(err){return'';}}
function add_sel_options(s,list,sel_val,o_style){if(s.custom_select){s.set_options(list)
if(sel_val)s.inp.value=sel_val;return;}
if(s.inp)s=s.inp;for(var i=0,len=list.length;i<len;i++){var o=new Option(list[i],list[i],false,(list[i]==sel_val?true:false));if(o_style)$y(o,o_style);s.options[s.options.length]=o;}}
function cint(v,def){v=v+'';v=lstrip(v,['0']);v=parseInt(v);if(isNaN(v))v=def?def:0;return v;}
function validate_email(id){if(strip(id).search("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")==-1)return 0;else return 1;}
function validate_spl_chars(txt){if(txt.search(/^[a-zA-Z0-9_\- ]*$/)==-1)return 1;else return 0;}
function d2h(d){return cint(d).toString(16);}
function h2d(h){return parseInt(h,16);}
var $n='\n';function set_title(t){document.title=(wn.title_prefix?(wn.title_prefix+' - '):'')+t;}
function $a(parent,newtag,className,cs,innerHTML,onclick){if(parent&&parent.substr)parent=$i(parent);var c=document.createElement(newtag);if(parent)
parent.appendChild(c);if(className){if(newtag.toLowerCase()=='img')
c.src=className
else
c.className=className;}
if(cs)$y(c,cs);if(innerHTML)c.innerHTML=innerHTML;if(onclick)c.onclick=onclick;return c;}
function $a_input(p,in_type,attributes,cs){if(!attributes)attributes={};var $input=$(p).append('<input type="'+in_type+'">').find('input:last');for(key in attributes)
$input.attr(key,attributes[key]);var input=$input.get(0);if(cs)
$y(input,cs);return input;}
function $dh(d){if(d&&d.substr)d=$i(d);if(d&&d.style.display.toLowerCase()!='none')d.style.display='none';}
function $ds(d){if(d&&d.substr)d=$i(d);var t='block';if(d&&in_list(['span','img','button'],d.tagName.toLowerCase()))
t='inline'
if(d&&d.style.display.toLowerCase()!=t)
d.style.display=t;}
function $di(d){if(d&&d.substr)d=$i(d);if(d)d.style.display='inline';}
function $i(id){if(!id)return null;if(id&&id.appendChild)return id;return document.getElementById(id);}
function $t(parent,txt){if(parent.substr)parent=$i(parent);return parent.appendChild(document.createTextNode(txt));}
function $w(e,w){if(e&&e.style&&w)e.style.width=w;}
function $h(e,h){if(e&&e.style&&h)e.style.height=h;}
function $bg(e,w){if(e&&e.style&&w)e.style.backgroundColor=w;}
function $fg(e,w){if(e&&e.style&&w)e.style.color=w;}
function $op(e,w){if(e&&e.style&&w){set_opacity(e,w);}}
function $y(ele,s){if(ele&&s){for(var i in s)ele.style[i]=s[i];};return ele;}
function $yt(tab,r,c,s){var rmin=r;var rmax=r;if(r=='*'){rmin=0;rmax=tab.rows.length-1;}
if(r.search&&r.search('-')!=-1){r=r.split('-');rmin=cint(r[0]);rmax=cint(r[1]);}
var cmin=c;var cmax=c;if(c=='*'){cmin=0;cmax=tab.rows[0].cells.length-1;}
if(c.search&&c.search('-')!=-1){c=c.split('-');rmin=cint(c[0]);rmax=cint(c[1]);}
for(var ri=rmin;ri<=rmax;ri++){for(var ci=cmin;ci<=cmax;ci++)
$y($td(tab,ri,ci),s);}}
function set_style(txt){var se=document.createElement('style');se.type="text/css";if(se.styleSheet){se.styleSheet.cssText=txt;}else{se.appendChild(document.createTextNode(txt));}
document.getElementsByTagName('head')[0].appendChild(se);}
function make_table(parent,nr,nc,table_width,widths,cell_style,table_style){var t=$a(parent,'table');t.style.borderCollapse='collapse';if(table_width)t.style.width=table_width;if(cell_style)t.cell_style=cell_style;for(var ri=0;ri<nr;ri++){var r=t.insertRow(ri);for(var ci=0;ci<nc;ci++){var c=r.insertCell(ci);if(ri==0&&widths&&widths[ci]){c.style.width=widths[ci];}
if(cell_style){for(var s in cell_style)c.style[s]=cell_style[s];}}}
t.append_row=function(){return append_row(this);}
if(table_style)$y(t,table_style);return t;}
function append_row(t,at,style){var r=t.insertRow(at?at:t.rows.length);if(t.rows.length>1){for(var i=0;i<t.rows[0].cells.length;i++){var c=r.insertCell(i);if(style)$y(c,style);}}
return r}
function $td(t,r,c){if(r<0)r=t.rows.length+r;if(c<0)c=t.rows[0].cells.length+c;return t.rows[r].cells[c];}
function $sum(t,cidx){var s=0;if(cidx<1)cidx=t.rows[0].cells.length+cidx;for(var ri=0;ri<t.rows.length;ri++){var c=t.rows[ri].cells[cidx];if(c.div)s+=flt(c.div.innerHTML);else if(c.value)s+=flt(c.value);else s+=flt(c.innerHTML);}
return s;}
function objpos(obj){if(obj.substr)obj=$i(obj);var p=$(obj).offset();return{x:cint(p.left),y:cint(p.top)}}
function get_screen_dims(){var d={};d.w=0;d.h=0;if(typeof(window.innerWidth)=='number'){d.w=window.innerWidth;d.h=window.innerHeight;}else if(document.documentElement&&(document.documentElement.clientWidth||document.documentElement.clientHeight)){d.w=document.documentElement.clientWidth;d.h=document.documentElement.clientHeight;}else if(document.body&&(document.body.clientWidth||document.body.clientHeight)){d.w=document.body.clientWidth;d.h=document.body.clientHeight;}
return d}
function get_page_size(){return[$(document).height(),$(document).width()];}
function get_scroll_top(){var st=0;if(document.documentElement&&document.documentElement.scrollTop)
st=document.documentElement.scrollTop;else if(document.body&&document.body.scrollTop)
st=document.body.scrollTop;return st;}
function get_cookie(c){var t=""+document.cookie;var ind=t.indexOf(c);if(ind==-1||c=="")return"";var ind1=t.indexOf(';',ind);if(ind1==-1)ind1=t.length;return unescape(t.substring(ind+c.length+1,ind1));}
wn.urllib={get_arg:function(name){name=name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");var regexS="[\\?&]"+name+"=([^&#]*)";var regex=new RegExp(regexS);var results=regex.exec(window.location.href);if(results==null)
return"";else
return decodeURIComponent(results[1]);},get_dict:function(){var d={}
var t=window.location.href.split('?')[1];if(!t)return d;if(t.indexOf('#')!=-1)t=t.split('#')[0];if(!t)return d;t=t.split('&');for(var i=0;i<t.length;i++){var a=t[i].split('=');d[decodeURIComponent(a[0])]=decodeURIComponent(a[1]);}
return d;},get_base_url:function(){var url=window.location.href.split('#')[0].split('?')[0].split('index.html')[0];if(url.substr(url.length-1,1)=='/')url=url.substr(0,url.length-1)
return url},get_file_url:function(file_id){return repl('files/%(fn)s',{fn:file_id})}}
get_url_arg=wn.urllib.get_arg;get_url_dict=wn.urllib.get_dict;var user_img={}
var user_img_queue={};var user_img_loading=[];set_user_img=function(img,username,get_latest,img_id){function set_it(i){if(user_img[username]=='no_img_m')
i.src='lib/images/ui/no_img_m.gif';else if(user_img[username]=='no_img_f')
i.src='lib/images/ui/no_img_f.gif';else{ac_id=wn.control_panel.account_id;i.src=repl('cgi-bin/getfile.cgi?ac=%(ac)s&name=%(fn)s',{fn:user_img[username],ac:ac_id});}}
if(img_id){user_img[username]=img_id;set_it(img);return;}
if(user_img[username]&&!get_latest){set_it(img);}else{if(in_list(user_img_loading,username)){if(!user_img_queue[username])
user_img_queue[username]=[];user_img_queue[username].push(img);return;}
$c('webnotes.profile.get_user_img',{username:username},function(r,rt){delete user_img_loading[user_img_loading.indexOf(username)];user_img[username]=r.message;if(user_img_queue[username]){var q=user_img_queue[username];for(var i in q){set_it(q[i]);}}
set_it(img);},null,1);user_img_loading.push(username);}}
/*
 *	lib/js/legacy/utils/handler.js
 */
var outUrl="index.cgi";var NULL_CHAR='^\5*';function checkResponse(r,on_timeout,no_spinner,freeze_msg){try{if(r.readyState==4&&r.status==200)return true;else return false;}catch(e){msgprint("error:Request timed out, try again");if(on_timeout)
on_timeout();hide_loading();if(freeze_msg)
unfreeze();return false;}}
var pending_req=0;function newHttpReq(){if(!isIE)
var r=new XMLHttpRequest();else if(window.ActiveXObject)
var r=new ActiveXObject("Microsoft.XMLHTTP");return r;}
function $c(command,args,fn,on_timeout,no_spinner,freeze_msg,btn){var req=newHttpReq();ret_fn=function(){if(checkResponse(req,on_timeout,no_spinner,freeze_msg)){if(btn)$(btn).done_working();if(!no_spinner)
hide_loading();var rtxt=req.responseText;try{var r=JSON.parse(rtxt);}catch(e){msgprint('Handler Exception:'+rtxt);return;}
if(freeze_msg)unfreeze();if(!validate_session(r,rtxt))return;if(r.exc){errprint(r.exc);console.log(r.exc);};if(r.server_messages){msgprint(r.server_messages);};if(r.docs){LocalDB.sync(r.docs);}
saveAllowed=true;if(fn)fn(r,rtxt);}}
if(btn)$(btn).set_working();req.onreadystatechange=ret_fn;req.open("POST",outUrl,true);req.setRequestHeader("ENCTYPE","multipart/form-data");req.setRequestHeader("Content-Type","application/x-www-form-urlencoded; charset=UTF-8");args['cmd']=command;req.send(makeArgString(args));if(!no_spinner)set_loading();if(freeze_msg)freeze(freeze_msg,1);}
function validate_session(r,rt){if(r.message=='Logged In'){start_sid=get_cookie('sid');return true;}
if(start_sid&&start_sid!=get_cookie('sid')&&user&&user!='Guest'){page_body.set_session_changed();return;}
if(r.exc&&r.session_status=='Session Expired'){resume_session();return;}
if(r.exc&&r.session_status=='Logged Out'){msgprint('You have been logged out');setTimeout('redirect_to_login()',3000);return;}
if(r.exc&&r.exc_type&&r.exc_type=='PermissionError'){loadpage('_home');}
return true;}
function $c_obj(doclist,method,arg,call_back,no_spinner,freeze_msg,btn){var args={'method':method,'arg':(typeof arg=='string'?arg:JSON.stringify(arg))}
if(typeof doclist=='string')args.doctype=doclist;else args.docs=compress_doclist(doclist)
$c('runserverobj',args,call_back,null,no_spinner,freeze_msg,btn);}
function $c_page(module,page,method,arg,call_back,no_spinner,freeze_msg,btn){if(arg&&!arg.substr)arg=JSON.stringify(arg);$c(module+'.page.'+page+'.'+page+'.'+method,{'arg':arg},call_back,null,no_spinner,freeze_msg,btn);}
wn.call=function(args){if(args.module&&args.page){$c_page(args.module,args.page,args.method,args.args,args.callback,args.no_spinner,false,args.btn);}else if(args.docs){$c_obj(args.doc,args.method,args.args,args.callback,args.no_spinner,false,args.btn);}else{$c(args.method,args.args,args.callback,false,args.no_spinner,false,args.btn);}}
function $c_obj_csv(doclist,method,arg){var args={}
args.cmd='runserverobj';args.as_csv=1;args.method=method;args.arg=arg;if(doclist.substr)
args.doctype=doclist;else
args.docs=compress_doclist(doclist);open_url_post(outUrl,args);}
function my_eval(co){var w=window;if(!w.execScript){if(/Gecko/.test(navigator.userAgent)){eval(co,w);}else{eval.call(w,co);}}else{w.execScript(co);}}
function makeArgString(dict){var varList=[];for(key in dict){varList[varList.length]=key+'='+encodeURIComponent(dict[key]);}
return varList.join('&');}
function open_url_post(URL,PARAMS,new_window){var temp=document.createElement("form");temp.action=URL;temp.method="POST";temp.style.display="none";if(new_window){temp.target='_blank';}
for(var x in PARAMS){var opt=document.createElement("textarea");opt.name=x;opt.value=PARAMS[x];temp.appendChild(opt);}
document.body.appendChild(temp);temp.submit();return temp;}
/*
 *	lib/js/legacy/utils/msgprint.js
 */
var msg_dialog;function msgprint(msg,issmall,callback){if(!msg)return;if(typeof(msg)!='string')
msg=JSON.stringify(msg);if(issmall){show_alert(msg);return;}
if(msg.substr(0,8)=='__small:'){show_alert(msg.substr(8));return;}
if(!msg_dialog){msg_dialog=new Dialog(500,200,"Message");msg_dialog.make_body([['HTML','Msg']])
msg_dialog.onhide=function(){msg_dialog.msg_area.innerHTML='';$dh(msg_dialog.msg_icon);if(msg_dialog.custom_onhide)msg_dialog.custom_onhide();}
$y(msg_dialog.rows['Msg'],{fontSize:'14px',lineHeight:'1.5em',padding:'16px'})
var t=make_table(msg_dialog.rows['Msg'],1,2,'100%',['20px','250px'],{padding:'2px',verticalAlign:'Top'});msg_dialog.msg_area=$td(t,0,1);msg_dialog.msg_icon=$a($td(t,0,0),'img');}
if(!msg_dialog.display)msg_dialog.show();var has_msg=msg_dialog.msg_area.innerHTML?1:0;var m=$a(msg_dialog.msg_area,'div','');if(has_msg)$y(m,{marginTop:'4px'});$dh(msg_dialog.msg_icon);if(msg.substr(0,6).toLowerCase()=='error:'){msg_dialog.msg_icon.src='lib/images/icons/error.gif';$di(msg_dialog.msg_icon);msg=msg.substr(6);}else if(msg.substr(0,8).toLowerCase()=='message:'){msg_dialog.msg_icon.src='lib/images/icons/application.gif';$di(msg_dialog.msg_icon);msg=msg.substr(8);}else if(msg.substr(0,3).toLowerCase()=='ok:'){msg_dialog.msg_icon.src='lib/images/icons/accept.gif';$di(msg_dialog.msg_icon);msg=msg.substr(3);}
m.innerHTML=replace_newlines(msg);if(m.offsetHeight>200){$y(m,{height:'200px',width:'400px',overflow:'auto'})}
msg_dialog.custom_onhide=callback;}
var growl_area;function show_alert(txt){if(!growl_area){growl_area=$a(popup_cont,'div','',{position:'fixed',bottom:'8px',right:'8px',width:'320px',zIndex:10});}
var wrapper=$a(growl_area,'div','',{position:'relative'});var body=$a(wrapper,'div','notice');var c=$a(body,'div','wn-icon ic-round_delete',{cssFloat:'right'});$(c).click(function(){$dh(this.wrapper)});c.wrapper=wrapper;var t=$a(body,'div','',{color:'#FFF'});$(t).html(txt);$(wrapper).hide().fadeIn(1000);}
/*
 *	lib/js/legacy/utils/shortcut.js
 */
(function(jQuery){jQuery.hotkeys={version:"0.8",specialKeys:{8:"backspace",9:"tab",13:"return",16:"shift",17:"ctrl",18:"alt",19:"pause",20:"capslock",27:"esc",32:"space",33:"pageup",34:"pagedown",35:"end",36:"home",37:"left",38:"up",39:"right",40:"down",45:"insert",46:"del",96:"0",97:"1",98:"2",99:"3",100:"4",101:"5",102:"6",103:"7",104:"8",105:"9",106:"*",107:"+",109:"-",110:".",111:"/",112:"f1",113:"f2",114:"f3",115:"f4",116:"f5",117:"f6",118:"f7",119:"f8",120:"f9",121:"f10",122:"f11",123:"f12",144:"numlock",145:"scroll",191:"/",224:"meta"},shiftNums:{"`":"~","1":"!","2":"@","3":"#","4":"$","5":"%","6":"^","7":"&","8":"*","9":"(","0":")","-":"_","=":"+",";":": ","'":"\"",",":"<",".":">","/":"?","\\":"|"}};function keyHandler(handleObj){if(typeof handleObj.data!=="string"){return;}
var origHandler=handleObj.handler,keys=handleObj.data.toLowerCase().split(" ");handleObj.handler=function(event){if(this!==event.target&&(/textarea|select/i.test(event.target.nodeName)||event.target.type==="text")){return;}
var special=event.type!=="keypress"&&jQuery.hotkeys.specialKeys[event.which],character=String.fromCharCode(event.which).toLowerCase(),key,modif="",possible={};if(event.altKey&&special!=="alt"){modif+="alt+";}
if(event.ctrlKey&&special!=="ctrl"){modif+="ctrl+";}
if(event.metaKey&&!event.ctrlKey&&special!=="meta"){modif+="meta+";}
if(event.shiftKey&&special!=="shift"){modif+="shift+";}
if(special){possible[modif+special]=true;}else{possible[modif+character]=true;possible[modif+jQuery.hotkeys.shiftNums[character]]=true;if(modif==="shift+"){possible[jQuery.hotkeys.shiftNums[character]]=true;}}
for(var i=0,l=keys.length;i<l;i++){if(possible[keys[i]]){return origHandler.apply(this,arguments);}}};}
jQuery.each(["keydown","keyup","keypress"],function(){jQuery.event.special[this]={add:keyHandler};});})(jQuery);
/*
 *	lib/js/legacy/widgets/form/fields.js
 */
var no_value_fields=['Section Break','Column Break','HTML','Table','FlexTable','Button','Image'];var codeid=0;var code_editors={};function Field(){this.with_label=1;}
Field.prototype.make_body=function(){var ischk=(this.df.fieldtype=='Check'?1:0);if(this.parent)
this.wrapper=$a(this.parent,'div');else
this.wrapper=document.createElement('div');this.label_area=$a(this.wrapper,'div','',{margin:'8px 0px 2px 0px'});if(ischk&&!this.in_grid){this.input_area=$a(this.label_area,'span','',{marginRight:'4px'});this.disp_area=$a(this.label_area,'span','',{marginRight:'4px'});}
if(this.with_label){this.label_span=$a(this.label_area,'span','field_label')
this.label_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 4px'});$dh(this.label_icon);this.label_icon.src='lib/images/icons/error.gif';this.label_icon.title='Mandatory value needs to be entered';this.suggest_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 0px'});$dh(this.suggest_icon);this.suggest_icon.src='lib/images/icons/bullet_arrow_down.png';this.suggest_icon.title='With suggestions';}else{this.label_span=$a(this.label_area,'span','',{marginRight:'4px'})
$dh(this.label_area);}
if(!this.input_area){this.input_area=$a(this.wrapper,'div');this.disp_area=$a(this.wrapper,'div');}
if(this.in_grid){if(this.label_area)$dh(this.label_area);}else{this.input_area.className='input_area';$y(this.wrapper,{marginBottom:'4px'});this.set_description();}
if(this.onmake)this.onmake();}
Field.prototype.set_max_width=function(){var no_max=['Code','Text Editor','Text','Table','HTML']
if(this.wrapper&&this.layout_cell&&this.layout_cell.parentNode.cells&&this.layout_cell.parentNode.cells.length==1&&!in_list(no_max,this.df.fieldtype)){$y(this.wrapper,{paddingRight:'50%'});}}
Field.prototype.set_label=function(){if(this.with_label&&this.label_area&&this.label!=this.df.label){this.label_span.innerHTML=this.df.label;this.label=this.df.label;}}
Field.prototype.set_description=function(){if(this.df.description){var p=in_list(['Text Editor','Code','Check'],this.df.fieldtype)?this.label_area:this.wrapper;this.desc_area=$a(p,'div','field_description','',this.df.description)
if(in_list(['Text Editor','Code'],this.df.fieldtype))
$(this.desc_area).addClass('field_description_top');}}
Field.prototype.get_status=function(){if(this.in_filter)this.not_in_form=this.in_filter;if(this.not_in_form){return'Write';}
var fn=this.df.fieldname?this.df.fieldname:this.df.label;this.df=get_field(this.doctype,fn,this.docname);if(!this.df.permlevel)this.df.permlevel=0;var p=this.perm[this.df.permlevel];var ret;if(cur_frm.editable&&p&&p[WRITE])ret='Write';else if(p&&p[READ])ret='Read';else ret='None';if(this.df.fieldtype=='Binary')
ret='None';if(cint(this.df.hidden))
ret='None';if(ret=='Write'&&cint(cur_frm.doc.docstatus)>0)ret='Read';var a_o_s=cint(this.df.allow_on_submit);if(a_o_s&&(this.in_grid||(this.frm&&this.frm.not_in_container))){a_o_s=null;if(this.in_grid)a_o_s=this.grid.field.df.allow_on_submit;if(this.frm&&this.frm.not_in_container){a_o_s=cur_grid.field.df.allow_on_submit;}}
if(cur_frm.editable&&a_o_s&&cint(cur_frm.doc.docstatus)>0&&!this.df.hidden){tmp_perm=get_perm(cur_frm.doctype,cur_frm.docname,1);if(tmp_perm[this.df.permlevel]&&tmp_perm[this.df.permlevel][WRITE])ret='Write';}
return ret;}
Field.prototype.set_style_mandatory=function(add){if(add){$(this.txt?this.txt:this.input).addClass('input-mandatory');if(this.disp_area)$(this.disp_area).addClass('input-mandatory');}else{$(this.txt?this.txt:this.input).removeClass('input-mandatory');if(this.disp_area)$(this.disp_area).removeClass('input-mandatory');}}
Field.prototype.refresh_mandatory=function(){if(this.in_filter)return;if(this.df.reqd){if(this.label_area)this.label_area.style.color="#d22";this.set_style_mandatory(1);}else{if(this.label_area)this.label_area.style.color="#222";this.set_style_mandatory(0);}
this.refresh_label_icon()
this.set_reqd=this.df.reqd;}
Field.prototype.refresh_display=function(){if(!this.set_status||this.set_status!=this.disp_status){if(this.disp_status=='Write'){if(this.make_input&&(!this.input)){this.make_input();if(this.onmake_input)this.onmake_input();}
if(this.show)this.show()
else{$ds(this.wrapper);}
if(this.input){$ds(this.input_area);$dh(this.disp_area);if(this.input.refresh)this.input.refresh();}else{$dh(this.input_area);$ds(this.disp_area);}}else if(this.disp_status=='Read'){if(this.show)this.show()
else{$ds(this.wrapper);}
$dh(this.input_area);$ds(this.disp_area);}else{if(this.hide)this.hide();else $dh(this.wrapper);}
this.set_status=this.disp_status;}}
Field.prototype.refresh=function(){this.disp_status=this.get_status();if(this.in_grid&&this.table_refresh&&this.disp_status=='Write')
{this.table_refresh();return;}
this.set_label();this.refresh_display();if(this.onrefresh)
this.onrefresh();if(this.input){if(this.input.refresh)this.input.refresh(this.df);}
if(this.wrapper){this.wrapper.fieldobj=this;$(this.wrapper).trigger('refresh');}
if(!this.not_in_form)
this.set_input(_f.get_value(this.doctype,this.docname,this.df.fieldname));this.refresh_mandatory();this.set_max_width();}
Field.prototype.refresh_label_icon=function(){if(this.df.reqd){if(this.get_value&&is_null(this.get_value())){if(this.label_icon)$ds(this.label_icon);$(this.txt?this.txt:this.input).addClass('field-to-update')}else{if(this.label_icon)$dh(this.label_icon);$(this.txt?this.txt:this.input).removeClass('field-to-update')}}}
Field.prototype.set=function(val){if(this.not_in_form)
return;if((!this.docname)&&this.grid){this.docname=this.grid.add_newrow();}
if(in_list(['Data','Text','Small Text','Code'],this.df.fieldtype))
val=clean_smart_quotes(val);var set_val=val;if(this.validate)set_val=this.validate(val);_f.set_value(this.doctype,this.docname,this.df.fieldname,set_val);this.value=val;}
Field.prototype.set_input=function(val){this.value=val;if(this.input&&this.input.set_input){if(val==null)this.input.set_input('');else this.input.set_input(val);}
var disp_val=val;if(val==null)disp_val='';this.set_disp(disp_val);}
Field.prototype.run_trigger=function(){this.refresh_label_icon();if(this.df.reqd&&this.get_value&&!is_null(this.get_value())&&this.set_as_error)
this.set_as_error(0);if(this.not_in_form){return;}
if(cur_frm.cscript[this.df.fieldname])
cur_frm.runclientscript(this.df.fieldname,this.doctype,this.docname);cur_frm.refresh_dependency();}
Field.prototype.set_disp_html=function(t){if(this.disp_area){$(this.disp_area).addClass('disp_area');this.disp_area.innerHTML=(t==null?'':t);if(!t)$(this.disp_area).addClass('disp_area_no_val');}}
Field.prototype.set_disp=function(val){this.set_disp_html(val);}
Field.prototype.set_as_error=function(set){if(this.in_grid||this.in_filter)return;var w=this.txt?this.txt:this.input;if(set){$y(w,{border:'2px solid RED'});}else{$y(w,{border:'1px solid #888'});}}
Field.prototype.activate=function(docname){this.docname=docname;this.refresh();if(this.input){var v=_f.get_value(this.doctype,this.docname,this.df.fieldname);this.last_value=v;if(this.input.onchange&&this.input.get_value&&this.input.get_value()!=v){if(this.validate)
this.input.set_value(this.validate(v));else
this.input.set_value((v==null)?'':v);if(this.format_input)
this.format_input();}
if(this.input.focus){try{this.input.focus();}catch(e){}}}
if(this.txt){try{this.txt.focus();}catch(e){}
this.txt.field_object=this;}}
function DataField(){}DataField.prototype=new Field();DataField.prototype.make_input=function(){var me=this;this.input=$a_input(this.input_area,this.df.fieldtype=='Password'?'password':'text');this.get_value=function(){var v=this.input.value;if(this.validate)v=this.validate(v);return v;}
this.input.name=this.df.fieldname;this.input.onchange=function(){if(!me.last_value)me.last_value='';if(me.validate)
me.input.value=me.validate(me.input.value);me.set(me.input.value);if(me.format_input)
me.format_input();if(in_list(['Currency','Float','Int'],me.df.fieldtype)){if(flt(me.last_value)==flt(me.input.value)){me.last_value=me.input.value;return;}}
me.last_value=me.input.value;me.run_trigger();}
this.input.set_input=function(val){if(val==null)val='';me.input.value=val;if(me.format_input)me.format_input();}
if(this.df.options=='Suggest'){wn.require('lib/js/legacy/widgets/autosuggest.js');if(this.suggest_icon)$di(this.suggest_icon);this.set_get_query=function(){}
this.get_query=function(doc,dt,dn){return repl('SELECT DISTINCT `%(fieldname)s` FROM `tab%(dt)s` WHERE `%(fieldname)s` LIKE "%s" LIMIT 50',{fieldname:me.df.fieldname,dt:me.df.parent})}
var opts={script:'',json:true,maxresults:10,link_field:this};this.as=new AutoSuggest(this.input,opts);}}
DataField.prototype.validate=function(v){if(this.df.options=='Phone'){if(v+''=='')return'';v1=''
v=v.replace(/ /g,'').replace(/-/g,'').replace(/\(/g,'').replace(/\)/g,'');if(v&&v.substr(0,1)=='+'){v1='+';v=v.substr(1);}
if(v&&v.substr(0,2)=='00'){v1+='00';v=v.substr(2);}
if(v&&v.substr(0,1)=='0'){v1+='0';v=v.substr(1);}
v1+=cint(v)+'';return v1;}else if(this.df.options=='Email'){if(v+''=='')return'';if(!validate_email(v)){msgprint(this.df.label+': '+v+' is not a valid email id');return'';}else
return v;}else{return v;}}
DataField.prototype.onrefresh=function(){if(this.input&&this.df.colour){var col='#'+this.df.colour.split(':')[1];$bg(this.input,col);}}
function ReadOnlyField(){}
ReadOnlyField.prototype=new Field();function HTMLField(){}
HTMLField.prototype=new Field();HTMLField.prototype.with_label=0;HTMLField.prototype.set_disp=function(val){this.disp_area.innerHTML=val;}
HTMLField.prototype.set_input=function(val){if(val)this.set_disp(val);}
HTMLField.prototype.onrefresh=function(){this.set_disp(this.df.options?this.df.options:'');}
var datepicker_active=0;function DateField(){}DateField.prototype=new Field();DateField.prototype.make_input=function(){var me=this;this.user_fmt=wn.control_panel.date_format;if(!this.user_fmt)this.user_fmt='dd-mm-yy';this.input=$a(this.input_area,'input');wn.require('lib/css/legacy/jquery-ui.css');$(this.input).datepicker({dateFormat:me.user_fmt.replace('yyyy','yy'),altFormat:'yy-mm-dd',changeYear:true,beforeShow:function(input,inst){datepicker_active=1},onClose:function(dateText,inst){datepicker_active=0;if(_f.cur_grid_cell)
_f.cur_grid_cell.grid.cell_deselect();}});var me=this;me.input.onchange=function(){if(this.value==null)this.value='';if(!this.not_in_form)
me.set(dateutil.user_to_str(me.input.value));me.run_trigger();}
me.input.set_input=function(val){if(val==null)val='';else val=dateutil.str_to_user(val);me.input.value=val;}
me.get_value=function(){if(me.input.value)
return dateutil.user_to_str(me.input.value);}}
DateField.prototype.set_disp=function(val){var v=dateutil.str_to_user(val);if(v==null)v='';this.set_disp_html(v);}
DateField.prototype.validate=function(v){if(!v)return;var me=this;this.clear=function(){msgprint("Date must be in format "+this.user_fmt);me.input.set_input('');return'';}
var t=v.split('-');if(t.length!=3){return this.clear();}
else if(cint(t[1])>12||cint(t[1])<1){return this.clear();}
else if(cint(t[2])>31||cint(t[2])<1){return this.clear();}
return v;};var _link_onchange_flag=null;function LinkField(){}LinkField.prototype=new Field();LinkField.prototype.make_input=function(){var me=this;if(me.df.no_buttons){this.txt=$a(this.input_area,'input');this.input=this.txt;}else{makeinput_popup(this,'ic-zoom','ic-sq_next','ic-sq_plus');me.setup_buttons();me.onrefresh=function(){if(me.can_create&&cur_frm.doc.docstatus==0)$ds(me.btn2);else $dh(me.btn2);}}
me.txt.field_object=this;me.set_onchange();me.input.set_input=function(val){if(val==undefined)val='';me.txt.value=val;}
me.get_value=function(){return me.txt.value;}
wn.require('lib/js/legacy/widgets/autosuggest.js');var opts={script:'',json:true,maxresults:10,link_field:me};this.as=new AutoSuggest(me.txt,opts);}
LinkField.prototype.setup_buttons=function(){var me=this;me.btn.onclick=function(){selector.set(me,me.df.options,me.df.label);selector.show(me.txt);}
if(me.btn1)me.btn1.onclick=function(){if(me.txt.value&&me.df.options){loaddoc(me.df.options,me.txt.value);}}
me.can_create=0;if((!me.not_in_form)&&in_list(profile.can_create,me.df.options)){me.can_create=1;me.btn2.onclick=function(){var on_save_callback=function(new_rec){if(new_rec){var d=_f.calling_doc_stack.pop();locals[d[0]][d[1]][me.df.fieldname]=new_rec;me.refresh();if(me.grid)me.grid.refresh();me.run_trigger();}}
_f.calling_doc_stack.push([me.doctype,me.docname]);new_doc(me.df.options,me.on_new,1,on_save_callback,me.doctype,me.docname,me.frm.not_in_container);}}else{$dh(me.btn2);$y($td(me.tab,0,2),{width:'0px'});}}
LinkField.prototype.set_onchange=function(){var me=this;me.txt.onchange=function(e){if(cur_autosug)return;if(_link_onchange_flag){return;}
_link_onchange_flag=1;me.refresh_label_icon();if(me.not_in_form){_link_onchange_flag=0;return;}
if(cur_frm){if(me.txt.value==locals[me.doctype][me.docname][me.df.fieldname]){me.set(me.txt.value);me.run_trigger();setTimeout('_link_onchange_flag = 0',500);return;}}
me.set(me.txt.value);if(_f.cur_grid_cell)
_f.cur_grid_cell.grid.cell_deselect();if(!me.txt.value){me.run_trigger();setTimeout('_link_onchange_flag = 0',500);return;}
var fetch='';if(cur_frm.fetch_dict[me.df.fieldname])
fetch=cur_frm.fetch_dict[me.df.fieldname].columns.join(', ');$c('webnotes.widgets.form.utils.validate_link',{'value':me.txt.value,'options':me.df.options,'fetch':fetch},function(r,rt){setTimeout('_link_onchange_flag = 0',500);if(selector&&selector.display)return;if(r.message=='Ok'){if(r.fetch_values)me.set_fetch_values(r.fetch_values);me.run_trigger();}else{var astr='';if(in_list(profile.can_create,me.df.options))astr=repl('<br><br><span class="link_type" onclick="newdoc(\'%(dt)s\')">Click here</span> to create a new %(dtl)s',{dt:me.df.options,dtl:get_doctype_label(me.df.options)})
msgprint(repl('error:<b>%(val)s</b> is not a valid %(dt)s.<br><br>You must first create a new %(dt)s <b>%(val)s</b> and then select its value. To find an existing %(dt)s, click on the magnifying glass next to the field.%(add)s',{val:me.txt.value,dt:get_doctype_label(me.df.options),add:astr}));me.txt.value='';me.set('');}});}}
LinkField.prototype.set_fetch_values=function(fetch_values){var fl=cur_frm.fetch_dict[this.df.fieldname].fields;var changed_fields=[];for(var i=0;i<fl.length;i++){if(locals[this.doctype][this.docname][fl[i]]!=fetch_values[i]){locals[this.doctype][this.docname][fl[i]]=fetch_values[i];if(!this.grid){refresh_field(fl[i]);changed_fields.push(fl[i]);}}}
for(i=0;i<changed_fields.length;i++){if(cur_frm.fields_dict[changed_fields[i]])
cur_frm.fields_dict[changed_fields[i]].run_trigger();}
if(this.grid)this.grid.refresh();}
LinkField.prototype.set_get_query=function(){if(this.get_query)return;if(this.grid){var f=this.grid.get_field(this.df.fieldname);if(f.get_query)this.get_query=f.get_query;}}
LinkField.prototype.set_disp=function(val){var t=null;if(val)t="<a href=\'javascript:loaddoc(\""+this.df.options+"\", \""+val+"\")\'>"+val+"</a>";this.set_disp_html(t);}
function IntField(){}IntField.prototype=new DataField();IntField.prototype.validate=function(v){if(isNaN(parseInt(v)))return null;return cint(v);};IntField.prototype.format_input=function(){if(this.input.value==null)this.input.value='';}
function FloatField(){}FloatField.prototype=new DataField();FloatField.prototype.validate=function(v){var v=parseFloat(v);if(isNaN(v))return null;return v;};FloatField.prototype.format_input=function(){if(this.input.value==null)this.input.value='';}
function CurrencyField(){}CurrencyField.prototype=new DataField();CurrencyField.prototype.format_input=function(){var v=fmt_money(this.input.value);if(this.not_in_form){if(!flt(this.input.value))v='';}
this.input.value=v;}
CurrencyField.prototype.validate=function(v){if(v==null||v=='')
return 0;return flt(v,2);}
CurrencyField.prototype.set_disp=function(val){var v=fmt_money(val);this.set_disp_html(v);}
CurrencyField.prototype.onmake_input=function(){if(!this.input)return;this.input.onfocus=function(){if(flt(this.value)==0)this.select();}}
function CheckField(){}CheckField.prototype=new Field();CheckField.prototype.validate=function(v){var v=parseInt(v);if(isNaN(v))return 0;return v;};CheckField.prototype.onmake=function(){this.checkimg=$a(this.disp_area,'div');var img=$a(this.checkimg,'img');img.src='lib/images/ui/tick.gif';$dh(this.checkimg);}
CheckField.prototype.make_input=function(){var me=this;this.input=$a_input(this.input_area,'checkbox');$y(this.input,{width:"16px",border:'0px',margin:'2px'});$(this.input).click(function(){me.set(this.checked?1:0);me.run_trigger();})
this.input.set_input=function(v){v=parseInt(v);if(isNaN(v))v=0;if(v)me.input.checked=true;else me.input.checked=false;}
this.get_value=function(){return this.input.checked?1:0;}}
CheckField.prototype.set_disp=function(val){if(val){$ds(this.checkimg);}
else{$dh(this.checkimg);}}
function TextField(){}TextField.prototype=new Field();TextField.prototype.set_disp=function(val){this.disp_area.innerHTML=replace_newlines(val);}
TextField.prototype.make_input=function(){var me=this;if(this.in_grid)
return;this.input=$a(this.input_area,'textarea');if(this.df.fieldtype=='Small Text')
this.input.style.height="80px";this.input.set_input=function(v){me.input.value=v;}
this.input.onchange=function(){me.set(me.input.value);me.run_trigger();}
this.get_value=function(){return this.input.value;}}
var text_dialog;function make_text_dialog(){var d=new Dialog(520,410,'Edit Text');d.make_body([['Text','Enter Text'],['HTML','Description'],['Button','Update']]);d.widgets['Update'].onclick=function(){var t=this.dialog;t.field.set(t.widgets['Enter Text'].value);t.hide();}
d.onshow=function(){this.widgets['Enter Text'].style.height='300px';var v=_f.get_value(this.field.doctype,this.field.docname,this.field.df.fieldname);this.widgets['Enter Text'].value=v==null?'':v;this.widgets['Enter Text'].focus();this.widgets['Description'].innerHTML=''
if(this.field.df.description)
$a(this.widgets['Description'],'div','field_description','',this.field.df.description);}
d.onhide=function(){if(_f.cur_grid_cell)
_f.cur_grid_cell.grid.cell_deselect();}
text_dialog=d;}
TextField.prototype.table_refresh=function(){if(!this.text_dialog)
make_text_dialog();text_dialog.set_title('Enter text for "'+this.df.label+'"');text_dialog.field=this;text_dialog.show();}
function SelectField(){}SelectField.prototype=new Field();SelectField.prototype.make_input=function(){var me=this;var opt=[];if(this.in_filter&&(!this.df.single_select)){this.input=$a(this.input_area,'select');this.input.multiple=true;this.input.style.height='4em';this.input.lab=$a(this.input_area,'div',{fontSize:'9px',color:'#999'});this.input.lab.innerHTML='(Use Ctrl+Click to select multiple or de-select)'}else{this.input=$a(this.input_area,'select');this.input.onchange=function(){if(me.validate)
me.validate();me.set(sel_val(this));me.run_trigger();}
if(this.df.options=='attach_files:'){this.file_attach=true;}}
this.set_as_single=function(){var i=this.input;i.multiple=false;i.style.height=null;if(i.lab)$dh(i.lab)}
this.refresh_options=function(options){if(options)
me.df.options=options;if(this.file_attach)
this.set_attach_options();me.options_list=me.df.options?me.df.options.split('\n'):[];empty_select(this.input);if(me.in_filter&&me.options_list[0]!=''){me.options_list=add_lists([''],me.options_list);}
add_sel_options(this.input,me.options_list);}
this.onrefresh=function(){this.refresh_options();if(this.not_in_form){this.input.value='';return;}
if(_f.get_value)
var v=_f.get_value(this.doctype,this.docname,this.df.fieldname);else{if(this.options_list&&this.options_list.length)
var v=this.options_list[0];else
var v=null;}
this.input.set_input(v);}
this.input.set_input=function(v){if(!v){if(!me.input.multiple){if(me.docname){if(me.options_list&&me.options_list.length){me.set(me.options_list[0]);me.input.value=me.options_list[0];}else{me.input.value='';}}}}else{if(me.options_list){if(me.input.multiple){for(var i=0;i<me.input.options.length;i++){me.input.options[i].selected=0;if(me.input.options[i].value&&inList(v.split(","),me.input.options[i].value))
me.input.options[i].selected=1;}}else if(in_list(me.options_list,v)){me.input.value=v;}}}}
this.get_value=function(){if(me.input.multiple){var l=[];for(var i=0;i<me.input.options.length;i++){if(me.input.options[i].selected)l[l.length]=me.input.options[i].value;}
return l;}else{if(me.input.options){var val=sel_val(me.input);if(!val&&!me.input.selectedIndex)
val=me.input.options[0].value;return val;}
return me.input.value;}}
this.set_attach_options=function(){if(!cur_frm)return;var fl=cur_frm.doc.file_list;if(fl){this.df.options='';var fl=fl.split('\n');for(var i in fl){this.df.options+='\n'+fl[i].split(',')[1];}}else{this.df.options=''}}
this.refresh();}
function TimeField(){}TimeField.prototype=new Field();TimeField.prototype.get_time=function(){return time_to_hhmm(sel_val(this.input_hr),sel_val(this.input_mn),sel_val(this.input_am));}
TimeField.prototype.set_time=function(v){ret=time_to_ampm(v);this.input_hr.inp.value=ret[0];this.input_mn.inp.value=ret[1];this.input_am.inp.value=ret[2];}
TimeField.prototype.set_style_mandatory=function(){}
TimeField.prototype.set_as_error=function(){}
TimeField.prototype.make_input=function(){var me=this;this.input=$a(this.input_area,'div','time_field');var t=make_table(this.input,1,3,'200px');var opt_hr=['1','2','3','4','5','6','7','8','9','10','11','12'];var opt_mn=['00','05','10','15','20','25','30','35','40','45','50','55'];var opt_am=['AM','PM'];this.input_hr=new SelectWidget($td(t,0,0),opt_hr,'50px');this.input_mn=new SelectWidget($td(t,0,1),opt_mn,'50px');this.input_am=new SelectWidget($td(t,0,2),opt_am,'50px');var onchange_fn=function(){me.set(me.get_time());me.run_trigger();}
this.input_hr.inp.onchange=onchange_fn;this.input_mn.inp.onchange=onchange_fn;this.input_am.inp.onchange=onchange_fn;this.onrefresh=function(){var v=_f.get_value?_f.get_value(me.doctype,me.docname,me.df.fieldname):null;me.set_time(v);if(!v)
me.set(me.get_time());}
this.input.set_input=function(v){if(v==null)v='';me.set_time(v);}
this.get_value=function(){return this.get_time();}
this.refresh();}
TimeField.prototype.set_disp=function(v){var t=time_to_ampm(v);var t=t[0]+':'+t[1]+' '+t[2];this.set_disp_html(t);}
function makeinput_popup(me,iconsrc,iconsrc1,iconsrc2){me.input=$a(me.input_area,'div');if(!me.not_in_form)
$y(me.input,{width:'80%'});me.input.set_width=function(w){$y(me.input,{width:(w-2)+'px'});}
var tab=$a(me.input,'table');me.tab=tab;$y(tab,{width:'100%',borderCollapse:'collapse',tableLayout:'fixed'});var c0=tab.insertRow(0).insertCell(0);var c1=tab.rows[0].insertCell(1);$y(c1,{width:'20px'});me.txt=$a($a($a(c0,'div','',{paddingRight:'8px'}),'div'),'input','',{width:'100%'});me.btn=$a(c1,'div','wn-icon '+iconsrc,{width:'16px'});if(iconsrc1)
me.btn.setAttribute('title','Search');else
me.btn.setAttribute('title','Select Date');if(iconsrc1){var c2=tab.rows[0].insertCell(2);$y(c2,{width:'20px'});me.btn1=$a(c2,'div','wn-icon '+iconsrc1,{width:'16px'});me.btn1.setAttribute('title','Open Link');}
if(iconsrc2){var c3=tab.rows[0].insertCell(3);$y(c3,{width:'20px'});me.btn2=$a(c3,'div','wn-icon '+iconsrc2,{width:'16px'});me.btn2.setAttribute('title','Create New');$dh(me.btn2);}
if(me.df.colour)
me.txt.style.background='#'+me.df.colour.split(':')[1];me.txt.name=me.df.fieldname;me.setdisabled=function(tf){me.txt.disabled=tf;}}
var tmpid=0;_f.ButtonField=function(){};_f.ButtonField.prototype=new Field();_f.ButtonField.prototype.with_label=0;_f.ButtonField.prototype.init=function(){this.prev_button=null;if(!this.frm)return;if(cur_frm&&cur_frm.fields[cur_frm.fields.length-1]&&cur_frm.fields[cur_frm.fields.length-1].df.fieldtype=='Button'){this.make_body=function(){this.prev_button=cur_frm.fields[cur_frm.fields.length-1];if(!this.prev_button.prev_button){this.prev_button.button_area=$a(this.prev_button.input_area,'span');}
this.wrapper=this.prev_button.wrapper;this.input_area=this.prev_button.input_area;this.disp_area=this.prev_button.disp_area;this.button_area=$a(this.prev_button.input_area,'span');}}}
_f.ButtonField.prototype.make_input=function(){var me=this;if(!this.prev_button){$y(this.input_area,{marginTop:'4px',marginBottom:'4px'});}
if(!this.button_area)
this.button_area=$a(this.input_area,'span','',{marginRight:'4px'});this.input=$btn(this.button_area,me.df.label.substr(0,20)+((me.df.label.length>20)?'..':''),null,{maxWidth:'170px',fontWeight:'bold'},null,1)
this.input.onclick=function(){if(me.not_in_form)return;this.disabled='disabled';if(cur_frm.cscript[me.df.label]&&(!me.in_filter)){cur_frm.runclientscript(me.df.label,me.doctype,me.docname);this.disabled=false;}else{cur_frm.runscript(me.df.options,me);this.disabled=false;}}}
_f.ButtonField.prototype.hide=function(){$dh(this.button_area);};_f.ButtonField.prototype.show=function(){$ds(this.button_area);};_f.ButtonField.prototype.set=function(v){};_f.ButtonField.prototype.set_disp=function(val){}
function make_field(docfield,doctype,parent,frm,in_grid,hide_label){switch(docfield.fieldtype.toLowerCase()){case'data':var f=new DataField();break;case'password':var f=new DataField();break;case'int':var f=new IntField();break;case'float':var f=new FloatField();break;case'currency':var f=new CurrencyField();break;case'read only':var f=new ReadOnlyField();break;case'link':var f=new LinkField();break;case'date':var f=new DateField();break;case'time':var f=new TimeField();break;case'html':var f=new HTMLField();break;case'check':var f=new CheckField();break;case'text':var f=new TextField();break;case'small text':var f=new TextField();break;case'select':var f=new SelectField();break;case'button':var f=new _f.ButtonField();break;case'code':var f=new _f.CodeField();break;case'text editor':var f=new _f.CodeField();break;case'table':var f=new _f.TableField();break;case'section break':var f=new _f.SectionBreak();break;case'column break':var f=new _f.ColumnBreak();break;case'image':var f=new _f.ImageField();break;}
f.parent=parent;f.doctype=doctype;f.df=docfield;f.perm=frm?frm.perm:[[1,1,1]];if(_f)
f.col_break_width=_f.cur_col_break_width;if(in_grid){f.in_grid=true;f.with_label=0;}
if(hide_label){f.with_label=0;}
if(frm){f.frm=frm;if(parent)
f.layout_cell=parent.parentNode;}
if(f.init)f.init();f.make_body();return f;}
/*
 *	lib/js/wn/ui/dialog.js
 */
wn.widgets.FieldGroup=function(){this.first_button=false;this.make_fields=function(body,fl){$y(this.body,{padding:'11px'});this.fields_dict={};for(var i=0;i<fl.length;i++){var df=fl[i];var div=$a(body,'div','',{margin:'6px 0px'})
f=make_field(df,null,div,null);f.not_in_form=1;this.fields_dict[df.fieldname]=f
f.refresh();if(df.fieldtype=='Button'&&!this.first_button){$(f.input).addClass('primary');this.first_button=true;}}}
this.get_values=function(){var ret={};var errors=[];for(var key in this.fields_dict){var f=this.fields_dict[key];var v=f.get_value?f.get_value():null;if(f.df.reqd&&!v)
errors.push(f.df.label+' is mandatory');if(v)ret[f.df.fieldname]=v;}
if(errors.length){msgprint('<b>Please check the following Errors</b>\n'+errors.join('\n'));return null;}
return ret;}
this.set_value=function(key,val){var f=this.fields_dict[key];if(f){f.set_input(val);f.refresh_mandatory();}}
this.set_values=function(dict){for(var key in dict){if(this.fields_dict[key]){this.set_value(key,dict[key]);}}}
this.clear=function(){for(key in this.fields_dict){var f=this.fields_dict[key];if(f){f.set_input(f.df['default']||'');}}}}
wn.widgets.Dialog=function(opts){this.opts=opts;this.display=false;this.make=function(opts){if(opts)
this.opts=opts;if(!this.opts.width)this.opts.width=480;this.wrapper=$a(popup_cont,'div','dialog_wrapper');if(this.opts.width)
this.wrapper.style.width=this.opts.width+'px';this.make_head();this.body=$a(this.wrapper,'div','dialog_body');if(this.opts.fields)
this.make_fields(this.body,this.opts.fields);}
this.make_head=function(){var me=this;this.head=$a(this.wrapper,'div','dialog_head');var t=make_table(this.head,1,2,'100%',['100%','16px'],{padding:'2px'});$y($td(t,0,0),{paddingLeft:'16px',fontWeight:'bold',fontSize:'14px',textAlign:'center'});$y($td(t,0,1),{textAlign:'right'});var img=$a($td(t,0,01),'img','',{cursor:'pointer'});img.src='lib/images/icons/close.gif';this.title_text=$td(t,0,0);this.set_title(this.opts.title);img.onclick=function(){if(me.oncancel)me.oncancel();me.hide();}
this.cancel_img=img;}
this.set_title=function(t){this.title_text.innerHTML=t?t:'';}
this.set_postion=function(){var d=get_screen_dims();this.wrapper.style.left=((d.w-cint(this.wrapper.style.width))/2)+'px';this.wrapper.style.top=(get_scroll_top()+60)+'px';top_index++;$y(this.wrapper,{zIndex:top_index});}
this.show=function(){if(this.display)return;this.set_postion()
$ds(this.wrapper);freeze();this.display=true;cur_dialog=this;if(this.onshow)this.onshow();}
this.hide=function(){if(this.onhide)this.onhide();unfreeze();$dh(this.wrapper);if(cur_autosug)cur_autosug.clearSuggestions();this.display=false;cur_dialog=null;}
this.no_cancel=function(){$dh(this.cancel_img);}
if(opts)this.make();}
wn.widgets.Dialog.prototype=new wn.widgets.FieldGroup();$(document).bind('keydown',function(e){if(cur_dialog&&!cur_dialog.no_cancel_flag&&e.which==27){cur_dialog.hide();}});
/*
 *	lib/js/legacy/widgets/dialog.js
 */
var cur_dialog;var top_index=91;function Dialog(w,h,title,content){this.make({width:w,title:title});if(content)this.make_body(content);this.onshow='';this.oncancel='';this.no_cancel_flag=0;this.display=false;this.first_button=false;}
Dialog.prototype=new wn.widgets.Dialog()
Dialog.prototype.make_body=function(content){this.rows={};this.widgets={};for(var i in content)this.make_row(content[i]);}
Dialog.prototype.clear_inputs=function(d){for(var wid in this.widgets){var w=this.widgets[wid];var tn=w.tagName?w.tagName.toLowerCase():'';if(tn=='input'||tn=='textarea'){w.value='';}else if(tn=='select'){sel_val(w.options[0].value);}else if(w.txt){w.txt.value='';}else if(w.input){w.input.value='';}}}
Dialog.prototype.make_row=function(d){var me=this;this.rows[d[1]]=$a(this.body,'div','dialog_row');var row=this.rows[d[1]];if(d[0]!='HTML'){var t=make_table(row,1,2,'100%',['30%','70%']);row.tab=t;var c1=$td(t,0,0);var c2=$td(t,0,1);if(d[0]!='Check'&&d[0]!='Button')
$t(c1,d[1]);}
if(d[0]=='HTML'){if(d[2])row.innerHTML=d[2];this.widgets[d[1]]=row;}
else if(d[0]=='Check'){var i=$a_input(c2,'checkbox','',{width:'20px'});c1.innerHTML=d[1];this.widgets[d[1]]=i;}
else if(d[0]=='Data'){c1.innerHTML=d[1];c2.style.overflow='auto';this.widgets[d[1]]=$a_input(c2,'text');if(d[2])$a(c2,'div','field_description').innerHTML=d[2];}
else if(d[0]=='Link'){c1.innerHTML=d[1];var f=make_field({fieldtype:'Link','label':d[1],'options':d[2]},'',c2,this,0,1);f.not_in_form=1;f.dialog=this;f.refresh();this.widgets[d[1]]=f.input;}
else if(d[0]=='Date'){c1.innerHTML=d[1];var f=make_field({fieldtype:'Date','label':d[1],'options':d[2]},'',c2,this,0,1);f.not_in_form=1;f.refresh();f.dialog=this;this.widgets[d[1]]=f.input;}
else if(d[0]=='Password'){c1.innerHTML=d[1];c2.style.overflow='auto';this.widgets[d[1]]=$a_input(c2,'password');if(d[3])$a(c2,'div','field_description').innerHTML=d[3];}
else if(d[0]=='Select'){c1.innerHTML=d[1];this.widgets[d[1]]=$a(c2,'select','',{width:'160px'})
if(d[2])$a(c2,'div','field_description').innerHTML=d[2];if(d[3])add_sel_options(this.widgets[d[1]],d[3],d[3][0]);}
else if(d[0]=='Text'){c1.innerHTML=d[1];c2.style.overflow='auto';this.widgets[d[1]]=$a(c2,'textarea');if(d[2])$a(c2,'div','field_description').innerHTML=d[2];}
else if(d[0]=='Button'){c2.style.height='32px';var b=$btn(c2,d[1],function(btn){if(btn._onclick)btn._onclick(me)},null,null,1);b.dialog=me;if(!this.first_button){$(b).addClass('primary');this.first_button=true;}
if(d[2]){b._onclick=d[2];}
this.widgets[d[1]]=b;}}
/*
 *	lib/js/wn/ui/listing.js
 */
wn.widgets.Listing=function(opts){this.opts=opts;this.page_length=20;this.btns={};this.start=0;var me=this;this.make=function(opts){this.wrapper=$a(this.opts.parent,'div');this.filters_area=$a(this.wrapper,'div','listing-filters');this.toolbar_area=$a(this.wrapper,'div','listing-toolbar');this.results_area=$a(this.wrapper,'div','listing-results');this.more_button_area=$a(this.wrapper,'div','listing-more');this.no_results_area=$a(this.wrapper,'div','help_box',{display:'none'},(this.opts.no_result_message?this.opts.no_result_message:'No results'));if(opts)this.opts=opts;this.page_length=this.opts.page_length?this.opts.page_length:this.page_length;this.make_toolbar();this.make_filters();this.make_more_button();}
this.make_filters=function(){if(this.opts.filters){$ds(this.filters_area);this.filters=new wn.widgets.FieldGroup(this.filters_area,this.opts.fields);}}
this.make_toolbar=function(){if(!this.opts.hide_refresh){this.ref_img=$a(this.toolbar_area,'span','link_type',{color:'#888'},'[refresh]');this.ref_img.onclick=function(){me.run();}
this.loading_img=$a(this.toolbar_area,'img','lib/images/ui/button-load.gif',{display:'none',marginLeft:'3px',marginBottom:'-2px'});}
if(this.opts.new_doctype){this.new_btn=$btn(this.toolbar_area,'New '+get_doctype_label(this.opts.new_doctype),function(){newdoc(me.opts.new_doctype,me.opts.new_doc_onload,me.opts.new_doc_indialog,me.opts.new_doc_onsave);},{marginLeft:'7px'});}}
this.make_more_button=function(){this.more_btn=$btn(this.more_button_area,'More...',function(){me.more_btn.set_working();me.run(function(){me.more_btn.done_working();},1);},'',0,1);$y(this.more_btn.loading_img,{marginBottom:'0px'});}
this.clear=function(){this.results_area.innerHTML='';this.table=null;$ds(this.results_area);$dh(this.no_results_area);}
this.make_results=function(r,rt){if(this.start==0)this.clear();$dh(this.more_button_area);if(this.loading_img)$dh(this.loading_img)
if(r.values&&r.values.length){this.values=r.values;var m=Math.min(r.values.length,this.page_length);for(var i=0;i<m;i++){var row=this.add_row();this.opts.render_row(row,r.values[i],this,i);}
this.start+=m;if(r.values.length>this.page_length)$ds(this.more_button_area);}else{if(this.start==0){$dh(this.results_area);$ds(this.no_results_area);}}
if(this.onrun)this.onrun();if(this.opts.onrun)this.opts.onrun();}
this.add_row=function(){return $a(this.results_area,'div','',(opts.cell_style?opts.cell_style:{padding:'3px 0px'}));}
this.run=function(callback,append){if(callback)
this.onrun=callback;if(!append)
this.start=0;this.query=this.opts.get_query?this.opts.get_query():this.opts.query;this.add_limits();args={query_max:this.query_max||this.opts.query_max||''}
args.simple_query=this.query;args.as_dict=1;if(this.loading_img)$di(this.loading_img);wn.call({method:'webnotes.widgets.query_builder.runquery',args:args,callback:function(r,rt){me.make_results(r,rt)},no_spinner:this.opts.no_loading,btn:this.opts.run_btn});}
this.refresh=this.run;this.add_limits=function(){this.query+=' LIMIT '+this.start+','+(this.page_length+1);}
if(opts)this.make();}
/*
 *	lib/js/legacy/widgets/layout.js
 */
function Layout(parent,width){if(parent&&parent.substr){parent=$i(parent);}
this.wrapper=$a(parent,'div','',{display:'none'});if(width){this.width=this.wrapper.style.width;}
this.myrows=[];}
Layout.prototype.addrow=function(){this.cur_row=new LayoutRow(this,this.wrapper);this.myrows[this.myrows.length]=this.cur_row;return this.cur_row}
Layout.prototype.addsubrow=function(){this.cur_row=new LayoutRow(this,this.cur_row.main_body);this.myrows[this.myrows.length]=this.cur_row;return this.cur_row}
Layout.prototype.addcell=function(width){return this.cur_row.addCell(width);}
Layout.prototype.setcolour=function(col){$bg(cc,col);}
Layout.prototype.show=function(){$ds(this.wrapper);}
Layout.prototype.hide=function(){$dh(this.wrapper);}
Layout.prototype.close_borders=function(){if(this.with_border){this.myrows[this.myrows.length-1].wrapper.style.borderBottom='1px solid #000';}}
function LayoutRow(layout,parent){this.layout=layout;this.wrapper=$a(parent,'div');this.main_head=$a(this.wrapper,'div');this.main_body=$a(this.wrapper,'div');if(layout.with_border){this.wrapper.style.border='1px solid #000';this.wrapper.style.borderBottom='0px';}
this.header=$a(this.main_body,'div','',{padding:(layout.with_border?'0px 8px':'0px')});this.body=$a(this.main_body,'div');this.table=$a(this.body,'table','',{width:'100%',borderCollapse:'collapse'});this.row=this.table.insertRow(0);this.mycells=[];}
LayoutRow.prototype.hide=function(){$dh(this.wrapper);}
LayoutRow.prototype.show=function(){$ds(this.wrapper);}
LayoutRow.prototype.addCell=function(wid){var lc=new LayoutCell(this.layout,this,wid);this.mycells[this.mycells.length]=lc;return lc;}
function LayoutCell(layout,layoutRow,width){if(width){var w=width+'';if(w.substr(w.length-2,2)!='px'){if(w.substr(w.length-1,1)!="%"){width=width+'%'};}}
this.width=width;this.layout=layout;var cidx=layoutRow.row.cells.length;this.cell=layoutRow.row.insertCell(cidx);this.cell.style.verticalAlign='top';this.set_width(layoutRow.row,width);var h=$a(this.cell,'div','',{padding:(layout.with_border?'0px 8px':'0px')});this.wrapper=$a(this.cell,'div','',{padding:(layout.with_border?'8px':'8px 0px')});layout.cur_cell=this.wrapper;layout.cur_cell.header=h;}
LayoutCell.prototype.set_width=function(row,width){var w=100;var n_cells=row.cells.length;var cells_with_no_width=n_cells;if(width){$y(row.cells[n_cells-1],{width:cint(width)+'%'})}else{row.cells[n_cells-1].estimated_width=1;}
for(var i=0;i<n_cells;i++){if(!row.cells[i].estimated_width){w=w-cint(row.cells[i].style.width);cells_with_no_width--;}}
for(var i=0;i<n_cells;i++){if(row.cells[i].estimated_width)
$y(row.cells[i],{width:cint(w/cells_with_no_width)+'%'})}}
LayoutCell.prototype.show=function(){$ds(this.wrapper);}
LayoutCell.prototype.hide=function(){$dh(this.wrapper);}
/*
 *	lib/js/legacy/webpage/page_header.js
 */
var def_ph_style={wrapper:{marginBottom:'16px',backgroundColor:'#EEE'},main_heading:{},sub_heading:{marginBottom:'8px',color:'#555',display:'none'},separator:{borderTop:'3px solid #444'},toolbar_area:{padding:'3px 0px',display:'none',borderBottom:'1px solid #AAA'}}
function PageHeader(parent,main_text,sub_text){this.wrapper=$a(parent,'div','page_header');this.t1=make_table($a(this.wrapper,'div','',def_ph_style.wrapper.backgroundColor),1,2,'100%',[null,'100px'],{padding:'2px'});$y(this.t1,{borderCollapse:'collapse'})
this.lhs=$td(this.t1,0,0);this.main_head=$a(this.lhs,'h1','',def_ph_style.main_heading);this.sub_head=$a(this.lhs,'h4','',def_ph_style.sub_heading);this.separator=$a(this.wrapper,'div','',def_ph_style.separator);this.toolbar_area=$a(this.wrapper,'div','',def_ph_style.toolbar_area);this.padding_area=$a(this.wrapper,'div','',{padding:'3px'});$y($td(this.t1,0,1),{textAlign:'right',padding:'3px'});this.close_btn=$a($td(this.t1,0,1),'span','close',{},'&#215;');this.close_btn.onclick=function(){nav_obj.show_last_open();};if(main_text)this.main_head.innerHTML=main_text;if(sub_text)this.sub_head.innerHTML=sub_text;this.buttons={};this.buttons2={};}
PageHeader.prototype.add_button=function(label,fn,bold,icon,green){var tb=this.toolbar_area;if(this.buttons[label])return;var btn=$btn(tb,label,fn,{marginRight:'4px'},(green?'primary':''));if(bold)$y(btn,{fontWeight:'bold'});this.buttons[label]=btn;$ds(this.toolbar_area);return btn;}
PageHeader.prototype.clear_toolbar=function(){this.toolbar_area.innerHTML='';this.buttons={};}
PageHeader.prototype.make_buttonset=function(){$(this.toolbar_area).buttonset();}
/*
 *	lib/js/legacy/widgets/select.js
 */
function SelectWidget(parent,options,width,editable,bg_color){var me=this;this.inp=$a(parent,'select');if(options)add_sel_options(this.inp,options);if(width)$y(this.inp,{width:width});this.set_width=function(w){$y(this.inp,{width:w})};this.set_options=function(o){add_sel_options(this.inp,o);}
this.inp.onchange=function(){if(me.onchange)me.onchange(this);}
return;}
/*
 *	lib/js/legacy/webpage/history.js
 */
var nav_obj={}
nav_obj.observers=[];nav_obj.add_observer=function(o){nav_obj.observers.push(o);}
nav_obj.ol=[];nav_obj.open_notify=function(t,dt,dn,no_history){if(nav_obj.ol.length){var tmp=nav_obj.ol[nav_obj.ol.length-1];if(tmp&&tmp[0]==t&&tmp[1]==dt&&tmp[2]==dn)return;}
if(!no_history){var tmp=[];for(var i in nav_obj.ol)
if(!(nav_obj.ol[i][0]==t&&nav_obj.ol[i][1]==dt&&nav_obj.ol[i][2]==dn))tmp.push(nav_obj.ol[i]);nav_obj.ol=tmp;nav_obj.ol.push([t,dt,dn])
en_t=encodeURIComponent(t);en_dt=encodeURIComponent(dt);en_dn=dn?encodeURIComponent(dn):'';if(en_t=='Page'){var id=en_dt+(dn?('/'+en_dn):'')}else{var id=en_t+'/'+en_dt+(dn?('/'+en_dn):'')}
if(nav_obj.on_open)
nav_obj.on_open(id);if(window.location.hash!='!'+id){window.location.hash='!'+id;}}
nav_obj.notify_observers(t,dt,dn);if(wn.boot.analytics_code){try{eval(wn.boot.analytics_code);}catch(e){console.log(e);}}}
nav_obj.notify_observers=function(t,dt,dn){for(var i=0;i<nav_obj.observers.length;i++){var o=nav_obj.observers[i];if(o&&o.notify)o.notify(t,dt,dn);}}
nav_obj.rename_notify=function(dt,oldn,newn){for(var i=0;i<nav_obj.ol.length;i++){var o=nav_obj.ol[i];if(o[1]==dt&&o[2]==oldn)o[2]=newn;}}
nav_obj.show_last_open=function(){var l=nav_obj.ol[nav_obj.ol.length-2];delete nav_obj.ol[nav_obj.ol.length-1];if(!l)loadpage('_home');else if(l[0]=='Page'){loadpage(l[1]);}else if(l[0]=='Report'){loadreport(l[1],l[2]);}else if(l[0]=='Form'){loaddoc(l[1],l[2]);}else if(l[0]=='DocBrowser'||l[0]=='List'){loaddocbrowser(l[1]);}}
var _history_current;function history_get_name(t){var parts=[];if(t.length>=3){for(var i=2;i<t.length;i++){parts.push(t[i]);}}
return parts.join('/')}
nav_obj.get_page=function(loc){if(!loc)loc=window.location.hash;if(loc.substr(0,1)=='#'){loc=loc.substr(1);}
if(loc.substr(0,1)=='!'){loc=loc.substr(1);}
if(!in_list(['Page/','Form/','Repor','DocBr','List/'],loc.substr(0,5))){loc='Page/'+loc;}
return loc.split('/');}
function historyChange(newLocation){var t=nav_obj.get_page(newLocation)
for(var i=0;i<t.length;i++)
t[i]=decodeURIComponent(t[i]);if(nav_obj.ol.length){var c=nav_obj.ol[nav_obj.ol.length-1];if(t.length==2){if(c[0]==t[0]&&c[1]==t[1])return;}else{if(c[0]==t[0]&&c[1]==t[1]&&c[2]==t[2])return;}}
if(t[2])
var docname=history_get_name(t);if(t[0]=='Form'){_history_current=newLocation;if(docname.substr(0,3)=='New'&&!(locals[t[1]]&&locals[t[1]][docname])){newdoc(t[1]);}else{loaddoc(t[1],docname);}}else if(t[0]=='Report'){_history_current=newLocation;loadreport(t[1],docname);}else if(t[0]=='Page'){_history_current=newLocation;loadpage(t[1]);}else if(t[0]=='Application'){_history_current=newLocation;loadapp(t[1]);}else if(t[0]=='DocBrowser'||t[0]=='List'){_history_current=newLocation;loaddocbrowser(t[1]);}};$(window).bind('hashchange',function(){historyChange(location.hash);});
/*
 *	lib/js/legacy/webpage/search.js
 */
search_fields={};function setlinkvalue(name){selector.input.set_input(name);selector.hide();}
function makeselector(){var d=new Dialog(540,440,'Search');d.make_body([['Data','Beginning With','Tip: You can use wildcard "%"'],['Select','Search By'],['Button','Search'],['HTML','Help'],['HTML','Result']]);var inp=d.widgets['Beginning With'];var field_sel=d.widgets['Search By'];var btn=d.widgets['Search'];d.sel_type='';d.values_len=0;d.set=function(input,type,label){d.sel_type=type;d.input=input;if(d.style!='Link'){d.rows['Result'].innerHTML='';d.values_len=0;}
d.style='Link';d.set_query_description()
if(!d.sel_type)d.sel_type='Value';d.set_title('Select a "'+d.sel_type+'" for field "'+label+'"');}
d.set_search=function(dt){if(d.style!='Search'){d.rows['Result'].innerHTML='';d.values_len=0;}
d.style='Search';if(d.input){d.input=null;sel_type=null;}
d.sel_type=get_label_doctype(dt);d.set_title('Quick Search for '+dt);}
$(inp).keydown(function(e){if(e.which==13){if(!btn.disabled)btn.onclick();}})
d.set_query_description=function(){if(d.input&&d.input.query_description){d.rows['Help'].innerHTML='<div class="help_box">'+d.input.query_description+'</div>';}else{d.rows['Help'].innerHTML=''}}
d.onshow=function(){if(d.set_doctype!=d.sel_type){d.rows['Result'].innerHTML='';d.values_len=0;}
inp.value='';if(d.input&&d.input.txt.value){inp.value=d.input.txt.value;}
try{inp.focus();}catch(e){}
if(d.input)d.input.set_get_query();var get_sf_list=function(dt){var l=[];var lf=search_fields[dt];for(var i=0;i<lf.length;i++)l.push(lf[i][1]);return l;}
$ds(d.rows['Search By']);if(search_fields[d.sel_type]){empty_select(field_sel);add_sel_options(field_sel,get_sf_list(d.sel_type),'ID');}else{empty_select(field_sel);add_sel_options(field_sel,['ID'],'ID');$c('webnotes.widgets.search.getsearchfields',{'doctype':d.sel_type},function(r,rt){search_fields[d.sel_type]=r.searchfields;empty_select(field_sel);add_sel_options(field_sel,get_sf_list(d.sel_type));field_sel.selectedIndex=0;});}}
d.onhide=function(){if(d.input&&d.input.txt)
d.input.txt.onchange()}
btn.onclick=function(){if(this.disabled)return;this.args.is_ajax=true;this.set_working();d.set_doctype=d.sel_type;var q='';args={};if(d.input&&d.input.get_query){var doc={};args.is_simple=1;if(cur_frm)doc=locals[cur_frm.doctype][cur_frm.docname];var q=d.input.get_query(doc,d.input.doctype,d.input.docname);if(!q){return'';}}
var get_sf_fieldname=function(v){var lf=search_fields[d.sel_type];if(!lf)
return'name'
for(var i=0;i<lf.length;i++)if(lf[i][1]==v)return lf[i][0];}
$.extend(args,{'txt':strip(inp.value),'doctype':d.sel_type,'query':q,'searchfield':get_sf_fieldname(sel_val(field_sel))});$c('webnotes.widgets.search.search_widget',args,function(r,rtxt){btn.done_working();if(r.coltypes)r.coltypes[0]='Link';d.values_len=r.values.length;d.set_result(r);},function(){btn.done_working();});}
d.set_result=function(r){d.rows['Result'].innerHTML='';var c=$a(d.rows['Result'],'div','comment',{paddingBottom:'4px',marginBottom:'4px',borderBottom:'1px solid #CCC',marginLeft:'4px'});if(r.values.length==50)
c.innerHTML='Showing max 50 results. Use filters to narrow down your search';else
c.innerHTML='Showing '+r.values.length+' resuts.';var w=$a(d.rows['Result'],'div','',{height:'240px',overflow:'auto',margin:'4px'});for(var i=0;i<r.values.length;i++){var div=$a(w,'div','',{marginBottom:'4px',paddingBottom:'4px',borderBottom:'1px dashed #CCC'});var l=$a($a(div,'div'),'span','link_type');l.innerHTML=r.values[i][0];l.link_name=r.values[i][0];l.dt=r.coloptions[0];if(d.input)
l.onclick=function(){setlinkvalue(this.link_name);}
else
l.onclick=function(){loaddoc(this.dt,this.link_name);d.hide();}
var cl=[]
for(var j=1;j<r.values[i].length;j++)cl.push(r.values[i][j]);var c=$a(div,'div','comment',{marginTop:'2px'});c.innerHTML=cl.join(', ');}}
selector=d;}
/*
 *	lib/js/legacy/webpage/spinner.js
 */
function set_loading(){pending_req++;$('#spinner').css('visibility','visible');$('body').css('cursor','progress');}
function hide_loading(){pending_req--;if(!pending_req){$('body').css('cursor','default');$('#spinner').css('visibility','hidden');}}
/*
 *	lib/js/legacy/webpage/freeze_page.js
 */
var fcount=0;var frozen=0;var dialog_message;var dialog_back;function freeze(msg,do_freeze){if(!dialog_back){dialog_back=$a($i('body_div'),'div','dialog_back');if(isIE)dialog_back.style['filter']='alpha(opacity=60)';}
$ds(dialog_back);fcount++;frozen=1;}
function unfreeze(){if(dialog_message)
$dh(dialog_message);if(!fcount)return;fcount--;if(!fcount){$dh(dialog_back);frozen=0;}}
/*
 *	lib/js/legacy/webpage/error_console.js
 */
var err_console;var err_list=[];function errprint(t){err_list[err_list.length]=('<pre style="font-family: Courier, Fixed; font-size: 11px; border-bottom: 1px solid #AAA; overflow: auto; width: 90%;">'+t+'</pre>');}
function setup_err_console(){err_console=new Dialog(640,480,'Error Console')
err_console.make_body([['HTML','Error List'],['Button','Clear'],['HTML','Error Report']]);var span=$a(err_console.widgets['Error Report'],'span','link_type');span.innerHTML='Send Error Report';span.onclick=function(){msg=prompt('How / where did you get the error [optional]')
var call_back=function(r,rt){err_console.hide();msgprint("Error Report Sent")}
$c('webnotes.utils.send_error_report',{'err_msg':err_console.rows['Error List'].innerHTML,'msg':msg},call_back);}
err_console.widgets['Clear'].onclick=function(){err_list=[];err_console.rows['Error List'].innerHTML='';err_console.hide();}
err_console.onshow=function(){err_console.rows['Error List'].innerHTML='<div style="padding: 16px; height: 360px; width: 90%; overflow: auto;">'
+err_list.join('<div style="height: 10px; margin-bottom: 10px; border-bottom: 1px solid #AAA"></div>')+'</div>';}}
startup_list.push(setup_err_console);
/*
 *	lib/js/legacy/webpage/loaders.js
 */
function loadreport(dt,rep_name,onload,menuitem,reset_report){wn.require('lib/js/legacy/report.compressed.js');dt=get_label_doctype(dt);var show_report_builder=function(){if(!_r.rb_con){_r.rb_con=new _r.ReportContainer();}
_r.rb_con.set_dt(dt,function(rb){if(rep_name){var t=rb.current_loaded;rb.load_criteria(rep_name);if(onload)
onload(rb);if((rb.dt)&&(!rb.dt.has_data()||rb.current_loaded!=t))
rb.dt.run();}else{if(reset_report){rb.reset_report();}}
if(!rb.forbidden){page_body.change_to('Report Builder');nav_obj.open_notify('Report',dt,rep_name);}});}
show_report_builder();}
var load_doc=loaddoc;function loaddoc(doctype,name,onload,menuitem,from_archive){doctype=get_label_doctype(doctype);if(frms['DocType']&&frms['DocType'].opendocs[doctype]){msgprint("Cannot open an instance of \""+doctype+"\" when the DocType is open.");return;}
if(doctype=='DocType'&&frms[name]){msgprint("Cannot open DocType \""+name+"\" when its instance is open.");return;}
var show_form=function(f){if(!_f.frm_con){_f.frm_con=new _f.FrmContainer();}
if(!frms[doctype]){_f.add_frm(doctype,show_doc,name,from_archive);}else if(LocalDB.is_doc_loaded(doctype,name)){show_doc();}else{$c('webnotes.widgets.form.load.getdoc',{'name':name,'doctype':doctype,'user':user,'from_archive':(from_archive?1:0)},show_doc,null,null);}}
var show_doc=function(r,rt){if(locals[doctype]&&locals[doctype][name]){page_body.set_status('Done');var frm=frms[doctype];frm.refresh(name);if(!frm.in_dialog)
nav_obj.open_notify('Form',doctype,name);if(onload)onload();}else{if(r.exc){msgprint('There were errors while loading '+doctype+' '+name);}
loadpage('_home');}}
show_form();}
function new_doc(doctype,onload,in_dialog,on_save_callback,cdt,cdn,cnic){doctype=get_label_doctype(doctype);if(!doctype){if(cur_frm)doctype=cur_frm.doctype;else return;}
var show_doc=function(){frm=frms[doctype];if(frm.perm[0][CREATE]==1){if(frm.meta.issingle){var dn=doctype;LocalDB.set_default_values(locals[doctype][doctype]);}else
var dn=LocalDB.create(doctype);if(onload)onload(dn);if(frm.in_dialog){var fd=_f.frm_dialog;fd.cdt=cdt;fd.cdn=cdn;fd.cnic=cnic;fd.on_save_callback=on_save_callback;}else{nav_obj.open_notify('Form',doctype,dn);}
frm.refresh(dn);}else{msgprint('error:Not Allowed To Create '+doctype+'\nContact your Admin for help');}}
var show_form=function(){if(!_f.frm_con){_f.frm_con=new _f.FrmContainer();}
if(!frms[doctype])
_f.add_frm(doctype,show_doc);else
show_doc(frms[doctype]);}
show_form();}
var newdoc=new_doc;var pscript={};var cur_page;function loadpage(page_name,call_back,no_history){if(!page_name)return;if(page_name=='_home')
page_name=home_page;var fn=function(r,rt){page_body.set_status('Done');if(page_body.pages[page_name]){var p=page_body.pages[page_name]
page_body.change_to(page_name);}else{var p=render_page(page_name);if(!p)return;}
cur_page=page_name;if(call_back)call_back();scroll(0,0);pscript.update_page_history(page_name,no_history)
try{if(pscript['refresh_'+page_name])pscript['refresh_'+page_name]();}catch(e){console.log(e);}}
if(get_local('Page',page_name)||page_body.pages[page_name])
fn();else{args=get_url_dict();args.name=page_name;$c('webnotes.widgets.page.getpage',args,fn);}}
pscript.update_page_history=function(page_name,no_history){var arg=null;var t=null;if(window.location.hash){var t=nav_obj.get_page(window.location.hash)}else if(get_url_arg('page')){var t=nav_obj.get_page(get_url_arg('page'))}
if(t&&t[1]==page_name)arg=t[2];nav_obj.open_notify('Page',page_name,arg,no_history);}
function loadscript(src,call_back){set_loading();var script=$a('head','script');script.type='text/javascript';script.src=src;script.onload=function(){if(call_back)call_back();hide_loading();}
script.onreadystatechange=function(){if(this.readyState=='complete'||this.readyState=='loaded'){hide_loading();call_back();}}}
var doc_browser_page;function loaddocbrowser(dt,label,fields){wn.require('lib/js/legacy/webpage/docbrowser.js');dt=get_label_doctype(dt);if(!doc_browser_page)
doc_browser_page=new ItemBrowserPage();doc_browser_page.show(dt,label,fields);nav_obj.open_notify('List',dt,'');}
/*
 *	lib/js/legacy/webpage/uploader.js
 */
var uploaders={};var upload_frame_count=0;Uploader=function(parent,args,callback){var id='frame'+upload_frame_count;upload_frame_count++;this.callback=callback;var div=$a(parent,'div');div.innerHTML='<iframe id="'+id+'" name="'+id+'" src="blank.html" \
  style="width:0px; height:0px; border:0px"></iframe>';var div=$a(parent,'div');div.innerHTML='<form method="POST" enctype="multipart/form-data" action="'+outUrl+'" target="'+id+'"></form>';var ul_form=div.childNodes[0];var f_list=[];var inp_fdata=$a_input($a(ul_form,'span'),'file',{name:'filedata'},{marginLeft:'7px'});if(!('cmd'in args)){var inp=$a_input($a(ul_form,'span'),'hidden',{name:'cmd'});inp.value='uploadfile';}
var inp=$a_input($a(ul_form,'span'),'hidden',{name:'uploader_id'});inp.value=id;var inp=$a_input($a(ul_form,'span'),'submit',null,{marginLeft:'7px'});inp.value='Upload';$y(inp,{width:'80px'});for(var key in args){var inp=$a_input($a(ul_form,'span'),'hidden',{name:key});inp.value=args[key];}
uploaders[id]=this;}
function upload_callback(id,fid){uploaders[id].callback(fid);}
/*
 *	lib/js/legacy/webpage/page.js
 */
var pages=[];var stylesheets=[];function Page(page_name,content){var me=this;this.name=page_name;this.trigger=function(event){try{if(pscript[event+'_'+this.name])
pscript[event+'_'+this.name](this.wrapper);}catch(e){console.log(e);}}
this.onshow=function(){set_title(me.doc.title?me.doc.title:me.name);if(!me.onload_complete){me.trigger('onload');me.onload_complete=true;}
me.trigger('onshow');cur_frm=null;}
this.wrapper=page_body.add_page(page_name,this.onshow);this.cont=this.wrapper
if(content)
this.wrapper.innerHTML=content;if(page_name==home_page)
pages['_home']=this;return this;}
function render_page(page_name,menuitem){if(!page_name)return;if((!locals['Page'])||(!locals['Page'][page_name])){loadpage('_home');return;}
var pdoc=locals['Page'][page_name];if(pdoc.style)set_style(pdoc.style)
if(pdoc.stylesheet){set_style(locals.Stylesheet[pdoc.stylesheet].stylesheet);stylesheets.push(pdoc.stylesheet);}
var p=new Page(page_name,pdoc._Page__content?pdoc._Page__content:pdoc.content);var script=pdoc.__script?pdoc.__script:pdoc.script;p.doc=pdoc;if(script){eval(script);}
page_body.change_to(page_name);return p;}
function refresh_page(page_name){var fn=function(r,rt){render_page(page_name)}
$c('webnotes.widgets.page.getpage',{'name':page_name,stylesheets:JSON.stringify(stylesheets)},fn);}
/*
 *	lib/js/legacy/wn/page_layout.js
 */
wn.PageLayout=function(args){$.extend(this,args)
this.wrapper=$a(this.parent,'div');this.wtab=make_table(this.wrapper,1,2,'100%',[this.main_width,this.sidebar_width]);this.main=$a($td(this.wtab,0,0),'div','layout_wrapper');this.sidebar_area=$a($td(this.wtab,0,1),'div');this.head=$a(this.main,'div');this.toolbar_area=$a(this.main,'div');this.body=$a(this.main,'div');this.footer=$a(this.main,'div');if(this.heading){this.page_head=new PageHeader(this.head,this.heading);}}
/*
 *	lib/js/legacy/wn/widgets/footer.js
 */
wn.widgets.Footer=function(args){$.extend(this,args);this.make=function(){this.wrapper=$a(this.parent,'div','std-footer');this.table=make_table(this.wrapper,1,this.columns,[],{width:100/this.columns+'%'});this.render_items();}
this.render_items=function(){for(var i=0;i<this.items.length;i++){var item=this.items[i];var div=$a($td(this.table,0,item.column),'div','std-footer-item');div.label=$a($a(div,'div'),'span','link_type','',item.label);div.label.onclick=item.onclick;if(item.description){div.description=$a(div,'div','field_description','',item.description);}}}
if(this.items)
this.make();}
/*
 *	lib/js/legacy/model/local_data.js
 */
var locals={'DocType':{}};var fields={};var fields_list={};var LocalDB={};var READ=0;var WRITE=1;var CREATE=2;var SUBMIT=3;var CANCEL=4;var AMEND=5;LocalDB.getchildren=function(child_dt,parent,parentfield,parenttype){var l=[];for(var key in locals[child_dt]){var d=locals[child_dt][key];if((d.parent==parent)&&(d.parentfield==parentfield)){if(parenttype){if(d.parenttype==parenttype)l.push(d);}else{l.push(d);}}}
l.sort(function(a,b){return(cint(a.idx)-cint(b.idx))});return l;}
LocalDB.add=function(dt,dn){if(!locals[dt])locals[dt]={};if(locals[dt][dn])delete locals[dt][dn];locals[dt][dn]={'name':dn,'doctype':dt,'docstatus':0};return locals[dt][dn];}
LocalDB.delete_doc=function(dt,dn){var doc=get_local(dt,dn);for(var ndt in locals){if(locals[ndt]){for(var ndn in locals[ndt]){var doc=locals[ndt][ndn];if(doc&&doc.parenttype==dt&&(doc.parent==dn||doc.__oldparent==dn)){delete locals[ndt][ndn];}}}}
delete locals[dt][dn];}
function get_local(dt,dn){return locals[dt]?locals[dt][dn]:null;}
LocalDB.sync=function(list){if(list._kl)list=expand_doclist(list);for(var i=0;i<list.length;i++){var d=list[i];if(!d.name)
d.name=LocalDB.get_localname(d.doctype);LocalDB.add(d.doctype,d.name);locals[d.doctype][d.name]=d;if(d.doctype=='DocType'){fields_list[d.name]=[];}else if(d.doctype=='DocField'){if(!d.parent){alert('Error: No parent specified for field "'+d.label+'"');}
if(!fields_list[d.parent])fields_list[d.parent]=[];fields_list[d.parent][fields_list[d.parent].length]=d;if(!fields[d.parent])
fields[d.parent]={};if(d.fieldname){fields[d.parent][d.fieldname]=d;}else if(d.label){fields[d.parent][d.label]=d;}}else if(d.doctype=='Event'){if((!d.localname)&&_c.calendar&&(!_c.calendar.has_event[d.name]))
_c.calendar.set_event(d);}
if(d.localname)
notify_rename_observers(d.doctype,d.localname,d.name);}}
local_name_idx={};LocalDB.get_localname=function(doctype){if(!local_name_idx[doctype])local_name_idx[doctype]=1;var n='New '+get_doctype_label(doctype)+' '+local_name_idx[doctype];local_name_idx[doctype]++;return n;}
LocalDB.set_default_values=function(doc){var doctype=doc.doctype;var docfields=fields_list[doctype];if(!docfields){return;}
var fields_to_refresh=[];for(var fid=0;fid<docfields.length;fid++){var f=docfields[fid];if(!in_list(no_value_fields,f.fieldtype)&&doc[f.fieldname]==null){var v=LocalDB.get_default_value(f.fieldname,f.fieldtype,f['default']);if(v){doc[f.fieldname]=v;fields_to_refresh.push(f.fieldname);}}}
return fields_to_refresh;}
LocalDB.is_doc_loaded=function(dt,dn){var exists=false;if(locals[dt]&&locals[dt][dn])exists=true;if(exists&&dt=='DocType'&&!locals[dt][dn].__islocal&&!frms[dt])
exists=false;return exists;}
function check_perm_match(p,dt,dn){if(!dn)return true;var out=false;if(p.match){if(user_defaults[p.match]){for(var i=0;i<user_defaults[p.match].length;i++){if(user_defaults[p.match][i]==locals[dt][dn][p.match]){return true;}}
return false;}else if(!locals[dt][dn][p.match]){return true;}else{return false;}}else{return true;}}
function get_perm(doctype,dn,ignore_submit){var perm=[[0,0],];if(in_list(user_roles,'Administrator'))perm[0][READ]=1;var plist=getchildren('DocPerm',doctype,'permissions','DocType');for(var pidx in plist){var p=plist[pidx];var pl=cint(p.permlevel?p.permlevel:0);if(in_list(user_roles,p.role)){if(check_perm_match(p,doctype,dn)){if(!perm[pl])perm[pl]=[];if(!perm[pl][READ]){if(cint(p.read))perm[pl][READ]=1;else perm[pl][READ]=0;}
if(!perm[pl][WRITE]){if(cint(p.write)){perm[pl][WRITE]=1;perm[pl][READ]=1;}else perm[pl][WRITE]=0;}
if(!perm[pl][CREATE]){if(cint(p.create))perm[pl][CREATE]=1;else perm[pl][CREATE]=0;}
if(!perm[pl][SUBMIT]){if(cint(p.submit))perm[pl][SUBMIT]=1;else perm[pl][SUBMIT]=0;}
if(!perm[pl][CANCEL]){if(cint(p.cancel))perm[pl][CANCEL]=1;else perm[pl][CANCEL]=0;}
if(!perm[pl][AMEND]){if(cint(p.amend))perm[pl][AMEND]=1;else perm[pl][AMEND]=0;}}}}
if((!ignore_submit)&&dn&&locals[doctype][dn].docstatus>0){for(pl in perm)
perm[pl][WRITE]=0;}
return perm;}
LocalDB.create=function(doctype,n){if(!n)n=LocalDB.get_localname(doctype);var doc=LocalDB.add(doctype,n)
doc.__islocal=1;doc.owner=user;LocalDB.set_default_values(doc);return n;}
LocalDB.delete_record=function(dt,dn){var d=locals[dt][dn];if(!d.__islocal)
d.__oldparent=d.parent;d.parent='old_parent:'+d.parent;d.docstatus=2;d.__deleted=1;}
LocalDB.get_default_value=function(fn,ft,df){if(df=='_Login'||df=='__user')
return user;else if(df=='_Full Name')
return user_fullname;else if(ft=='Date'&&(df=='Today'||df=='__today')){return get_today();}
else if(df)
return df;else if(user_defaults[fn])
return user_defaults[fn][0];else if(sys_defaults[fn])
return sys_defaults[fn];}
LocalDB.add_child=function(doc,childtype,parentfield){var n=LocalDB.create(childtype);var d=locals[childtype][n];d.parent=doc.name;d.parentfield=parentfield;d.parenttype=doc.doctype;return d;}
LocalDB.no_copy_list=['amended_from','amendment_date','cancel_reason'];LocalDB.copy=function(dt,dn,from_amend){var newdoc=LocalDB.create(dt);for(var key in locals[dt][dn]){if(key!=='name'&&key.substr(0,2)!='__'){locals[dt][newdoc][key]=locals[dt][dn][key];}
var df=get_field(dt,key);if(df&&((!from_amend&&cint(df.no_copy)==1)||in_list(LocalDB.no_copy_list,df.fieldname))){locals[dt][newdoc][key]='';}}
return locals[dt][newdoc];}
function make_doclist(dt,dn,deleted){var dl=[];dl[0]=locals[dt][dn];for(var ndt in locals){if(locals[ndt]){for(var ndn in locals[ndt]){var doc=locals[ndt][ndn];if(doc&&doc.parenttype==dt&&(doc.parent==dn||(deleted&&doc.__oldparent==dn))){dl[dl.length]=doc;}}}}
return dl;}
var rename_observers=[];function notify_rename_observers(dt,old_name,new_name){try{var old=locals[dt][old_name];old.parent=null;old.__deleted=1;}catch(e){alert("[rename_from_local] No Document for: "+old_name);}
for(var i=0;i<rename_observers.length;i++){if(rename_observers[i])
rename_observers[i].rename_notify(dt,old_name,new_name);}}
var Meta={};var local_dt={};Meta.make_local_dt=function(dt,dn){var dl=make_doclist('DocType',dt);if(!local_dt[dt])local_dt[dt]={};if(!local_dt[dt][dn])local_dt[dt][dn]={};for(var i=0;i<dl.length;i++){var d=dl[i];if(d.doctype=='DocField'){var key=d.fieldname?d.fieldname:d.label;local_dt[dt][dn][key]=copy_dict(d);}}}
Meta.get_field=function(dt,fn,dn){if(dn&&local_dt[dt]&&local_dt[dt][dn]){return local_dt[dt][dn][fn];}else{if(fields[dt])var d=fields[dt][fn];if(d)return d;}
return{};}
Meta.set_field_property=function(fn,key,val,doc){if(!doc&&(cur_frm.doc))doc=cur_frm.doc;try{local_dt[doc.doctype][doc.name][fn][key]=val;refresh_field(fn);}catch(e){alert("Client Script Error: Unknown values for "+doc.name+','+fn+'.'+key+'='+val);}}
function get_doctype_label(dt){if(session.dt_labels&&session.dt_labels[dt])
return session.dt_labels[dt]
else
return dt}
function get_label_doctype(label){if(session.rev_dt_labels&&session.rev_dt_labels[label])
return session.rev_dt_labels[label]
else
return label}
var getchildren=LocalDB.getchildren;var get_field=Meta.get_field;var createLocal=LocalDB.create;
/*
 *	lib/js/legacy/model/doclist.js
 */
function compress_doclist(list){var kl={};var vl=[];var flx={};for(var i=0;i<list.length;i++){var o=list[i];var fl=[];if(!kl[o.doctype]){var tfl=['doctype','name','docstatus','owner','parent','parentfield','parenttype','idx','creation','modified','modified_by','__islocal','__deleted','__newname','__modified','_user_tags'];var fl=['doctype','name','docstatus','owner','parent','parentfield','parenttype','idx','creation','modified','modified_by','__islocal','__deleted','__newname','__modified','_user_tags'];for(key in fields[o.doctype]){if(!in_list(fl,key)&&!in_list(no_value_fields,fields[o.doctype][key].fieldtype)&&!fields[o.doctype][key].no_column){fl[fl.length]=key;tfl[tfl.length]=key}}
flx[o.doctype]=fl;kl[o.doctype]=tfl}
var nl=[];var fl=flx[o.doctype];for(var j=0;j<fl.length;j++){var v=o[fl[j]];nl.push(v);}
vl.push(nl);}
return JSON.stringify({'_vl':vl,'_kl':kl});}
function expand_doclist(docs){var l=[];for(var i=0;i<docs._vl.length;i++)
l[l.length]=zip(docs._kl[docs._vl[i][0]],docs._vl[i]);return l;}
function zip(k,v){var obj={};for(var i=0;i<k.length;i++){obj[k[i]]=v[i];}
return obj;}
function save_doclist(dt,dn,save_action,onsave,onerr){var doc=locals[dt][dn];var doctype=locals['DocType'][dt];var tmplist=[];var doclist=make_doclist(dt,dn,1);var all_clear=true;if(save_action!='Cancel'){for(var n in doclist){var tmp=check_required(doclist[n].doctype,doclist[n].name,doclist[0].doctype);if(doclist[n].docstatus+''!='2'&&all_clear)
all_clear=tmp;}}
var f=frms[dt];if(f&&!all_clear){if(f)f.savingflag=false;return'Error';}
var _save=function(){page_body.set_status('Saving...')
$c('webnotes.widgets.form.save.savedocs',{'docs':compress_doclist(doclist),'docname':dn,'action':save_action,'user':user},function(r,rtxt){if(f){f.savingflag=false;}
if(r.saved){if(onsave)onsave(r);}else{if(onerr)onerr(r);}},function(){if(f){f.savingflag=false;}},0,(f?'Saving...':''));}
if(doc.__islocal&&(doctype&&doctype.autoname&&doctype.autoname.toLowerCase()=='prompt')){var newname=prompt('Enter the name of the new '+dt,'');if(newname){doc.__newname=strip(newname);_save();}else{msgprint('Not Saved');onerr();}}else{_save();}}
function check_required(dt,dn,parent_dt){var doc=locals[dt][dn];if(doc.docstatus>1)return true;var fl=fields_list[dt];if(!fl)return true;var all_clear=true;var errfld=[];for(var i=0;i<fl.length;i++){var key=fl[i].fieldname;var v=doc[key];if(fl[i].reqd&&is_null(v)&&fl[i].fieldname){errfld[errfld.length]=fl[i].label;if(cur_frm){var f=cur_frm.fields_dict[fl[i].fieldname];if(f){if(f.set_as_error)f.set_as_error(1);if(!cur_frm.error_in_section&&f.parent_section){cur_frm.set_section(f.parent_section.sec_id);cur_frm.error_in_section=1;}}}
if(all_clear)all_clear=false;}}
if(errfld.length)msgprint('<b>Mandatory fields required in '+
(doc.parenttype?(fields[doc.parenttype][doc.parentfield].label+' (Table)'):get_doctype_label(doc.doctype))+':</b>\n'+errfld.join('\n'));return all_clear;}
/*
 *	lib/js/legacy/webpage/body.js
 */
function Body(){this.left_sidebar=null;this.right_sidebar=null;this.status_area=null;var me=this;page_body=this;this.no_of_columns=function(){var n=2;if(cint(me&&me.cp&&me.cp.right_sidebar_width))
n=n+1;return n;}
this.ready=function(){$dh('startup_div');$ds('body_div');}
this.setup_page_areas=function(){var n=this.no_of_columns();this.body_table=make_table(this.body,1,n,'100%');$y(this.body_table,{tableLayout:'fixed'});var c=0;this.left_sidebar=$td(this.body_table,0,c);$y(this.left_sidebar,{width:cint(this.cp.left_sidebar_width)+'px'});c++;this.center=$a($td(this.body_table,0,c),'div');c++;if(cint(this.cp.right_sidebar_width)){this.right_sidebar=$td(this.body_table,0,c);$y(this.right_sidebar,{width:cint(this.cp.right_sidebar_width)+'px'})
c++;}
this.center.header=$a(this.center,'div');this.center.body=$a(this.center,'div');this.center.loading=$a(this.center,'div','',{margin:'200px 0px',fontSize:'14px',color:'#999',textAlign:'center'});this.center.loading.innerHTML='Loading...'}
this.setup_sidebar_menu=function(){if(this.left_sidebar&&this.cp.show_sidebar_menu){sidebar_menu=new SidebarMenu();sidebar_menu.make_menu('');}}
this.run_startup_code=function(){$(document).trigger('startup');try{if(this.cp.custom_startup_code)
eval(this.cp.custom_startup_code);}catch(e){errprint(e);}}
this.setup=function(){this.cp=wn.control_panel;this.wrapper=$a($i('body_div'),'div');this.body=$a(this.wrapper,'div');this.setup_page_areas();if(user=='Guest')user_defaults.hide_webnotes_toolbar=1;if(!cint(user_defaults.hide_webnotes_toolbar)||user=='Administrator'){this.wntoolbar=new wn.ui.toolbar.Toolbar();}
if(this.cp.page_width)$y(this.wrapper,{width:cint(this.cp.page_width)+'px'});}
this.pages={};this.cur_page=null;this.add_page=function(label,onshow,onhide){var c=$a(this.center.body,'div');if(onshow)
c.onshow=onshow;if(onhide)
c.onhide=onhide;this.pages[label]=c;$dh(c);return c;}
this.change_to=function(label){$dh(this.center.loading);if(me.cur_page&&me.pages[label]!=me.cur_page){if(me.cur_page.onhide)
me.cur_page.onhide();$dh(me.cur_page);}
me.cur_page=me.pages[label];me.cur_page_label=label;$(me.cur_page).fadeIn();if(me.cur_page.onshow)
me.cur_page.onshow(me.cur_page);}
this.set_status=function(txt){if(this.status_area)
this.status_area.innerHTML=txt;}
this.set_session_changed=function(){if(this.session_message_set)return;var div=$a($i('body_div').parentNode,'div','',{textAlign:'center',fontSize:'14px',margin:'150px auto'});$dh('body_div');div.innerHTML='This session has been changed. Please <span class="link_type" onclick="window.location.reload()">refresh</span> to continue';this.session_message_set=1;}
this.setup();}
/*
 *	lib/js/legacy/app.js
 */
var popup_cont;var session={};var start_sid=null;if(!wn)var wn={};function startup(){start_sid=get_cookie('sid');popup_cont=$a(document.getElementsByTagName('body')[0],'div');var setup_globals=function(r){wn.boot=r;profile=r.profile;user=r.profile.name;user_fullname=profile.first_name+(r.profile.last_name?(' '+r.profile.last_name):'');user_defaults=profile.defaults;user_roles=profile.roles;user_email=profile.email;profile.start_items=r.start_items;home_page=r.home_page;_p.letter_heads=r.letter_heads;sys_defaults=r.sysdefaults;session.rt=profile.can_read;if(r.ipinfo)session.ipinfo=r.ipinfo;session.dt_labels=r.dt_labels;session.rev_dt_labels={}
if(r.dt_labels){for(key in r.dt_labels)session.rev_dt_labels[r.dt_labels[key]]=key;}
wn.control_panel=r.control_panel;}
var setup_history=function(r){rename_observers.push(nav_obj);}
var callback=function(r,rt){if(r.exc)console.log(r.exc);setup_globals(r);setup_history();var a=new Body();page_body.run_startup_code();page_body.setup_sidebar_menu();for(var i=0;i<startup_list.length;i++){startup_list[i]();}
if(get_url_arg('embed')){newdoc(get_url_arg('embed'));return;}
var t=to_open();if(t){historyChange(t);}else if(home_page){loadpage(home_page);}
page_body.ready();}
if(wn.boot){LocalDB.sync(wn.boot.docs);callback(wn.boot,'');if(wn.boot.error_messages)
console.log(wn.boot.error_messages)
if(wn.boot.server_messages)
msgprint(wn.boot.server_messages);}else{if($i('startup_div'))
$c('startup',{},callback,null,1);}}
function to_open(){if(get_url_arg('page'))
return get_url_arg('page');var h=location.hash;if(h){return h.substr(1);}}
function logout(){$c('logout',args={},function(r,rt){if(r.exc){msgprint(r.exc);return;}
redirect_to_login();});}
function redirect_to_login(){if(login_file)
window.location.href=login_file;else{window.location.reload();}}
_p.def_print_style_body="html, body, div, span, td { font-family: Arial, Helvetica; font-size: 12px; }"+"\npre { margin:0; padding:0;}"
_p.def_print_style_other="\n.simpletable, .noborder { border-collapse: collapse; margin-bottom: 10px;}"
+"\n.simpletable td {border: 1pt solid #000; vertical-align: top; padding: 2px; }"
+"\n.noborder td { vertical-align: top; }"
_p.go=function(html){var d=document.createElement('div')
d.innerHTML=html
$(d).printElement();}
_p.preview=function(html){var w=window.open('');w.document.write(html)
w.document.close();}
function setup_calendar(){var p=new Page('_calendar');p.wrapper.style.height='100%';p.wrapper.onshow=function(){wn.require('lib/js/legacy/widgets/calendar.js');if(!_c.calendar){_c.calendar=new Calendar();_c.calendar.init(p.cont);rename_observers.push(_c.calendar);}}}
startup_list.push(setup_calendar);var resize_observers=[]
function set_resize_observer(fn){if(resize_observers.indexOf(fn)==-1)resize_observers.push(fn);}
window.onresize=function(){return;var ht=get_window_height();for(var i=0;i<resize_observers.length;i++){resize_observers[i](ht);}}
get_window_height=function(){var ht=window.innerHeight?window.innerHeight:document.documentElement.offsetHeight?document.documentElement.offsetHeight:document.body.offsetHeight;return ht;}
/*
 *	js/app.js
 */
wn.app={name:'ERPNext',license:'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',source:'https://github.com/webnotes/erpnext',publisher:'Web Notes Technologies Pvt Ltd, Mumbai',copyright:'&copy; Web Notes Technologies Pvt Ltd',version:'2.'+window._version_number}
wn.modules_path='erpnext';wn.settings.no_history=true;$(document).bind('ready',function(){startup();});$(document).bind('toolbar_setup',function(){$('.brand').html('<b>erp</b>next');})
/*
 *	lib/js/bootstrap/bootstrap-dropdown.js
 *//* ============================================================
 * bootstrap-dropdown.js v1.4.0
 * http://twitter.github.com/bootstrap/javascript.html#dropdown
 * ============================================================
 * Copyright 2011 Twitter, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ============================================================ */

!function( $ ){

  "use strict"

  /* DROPDOWN PLUGIN DEFINITION
   * ========================== */

  $.fn.dropdown = function ( selector ) {
    return this.each(function () {
      $(this).delegate(selector || d, 'click', function (e) {
        var li = $(this).parent('li')
          , isActive = li.hasClass('open')

        clearMenus()
        !isActive && li.toggleClass('open')
        return false
      })
    })
  }

  /* APPLY TO STANDARD DROPDOWN ELEMENTS
   * =================================== */

  var d = 'a.menu, .dropdown-toggle'

  function clearMenus() {
    $(d).parent('li').removeClass('open')
  }

  $(function () {
    $('html').bind("click", clearMenus)
    $('body').dropdown( '[data-dropdown] a.menu, [data-dropdown] .dropdown-toggle' )
  })

}( window.jQuery || window.ender );

/*
 *	erpnext/startup/startup.js
 */
var current_module;var is_system_manager=0;var module_content_dict={};var user_full_nm={};wn.provide('erpnext.startup');erpnext.startup.set_globals=function(){pscript.is_erpnext_saas=cint(wn.control_panel.sync_with_gateway)
if(inList(user_roles,'System Manager'))is_system_manager=1;}
erpnext.startup.start=function(){$('#startup_div').html('Starting up...').toggle(true);erpnext.startup.set_globals();if(user=='Guest'){$dh(page_body.left_sidebar);if(wn.boot.custom_css){set_style(wn.boot.custom_css);}
if(wn.boot.website_settings.title_prefix){wn.title_prefix=wn.boot.website_settings.title_prefix;}}else{pscript.startup_make_sidebar();erpnext.toolbar.setup();$('footer').html('<div class="erpnext-footer">\
   Powered by <a href="https://erpnext.com">ERPNext</a></div>');}
$('#startup_div').toggle(false);}
show_chart_browser=function(nm,chart_type){var call_back=function(){if(nm=='Sales Browser'){var sb_obj=new SalesBrowser();sb_obj.set_val(chart_type);}
else if(nm=='Accounts Browser')
pscript.make_chart(chart_type);}
loadpage(nm,call_back);}
ModulePage=function(parent,module_name,module_label,help_page,callback){this.parent=parent;page_body.cur_page.module_page=this;this.wrapper=$a(parent,'div');this.module_name=module_name;this.transactions=[];this.page_head=new PageHeader(this.wrapper,module_label);if(help_page){var btn=this.page_head.add_button('Help',function(){loadpage(this.help_page)},1,'ui-icon-help')
btn.help_page=help_page;}
if(callback)this.callback=function(){callback();}}
$(document).bind('startup',function(){erpnext.startup.start();});
/*
 *	erpnext/website/js/topbar.js
 */
wn.provide('erpnext.topbar');erpnext.topbar.TopBar=Class.extend({init:function(){this.make();$('.brand').html(wn.boot.website_settings.brand_html);this.make_items();$('.topbar').dropdown();},make:function(){$('header').append('<div class="topbar">\
   <div class="topbar-inner">\
   <div class="container">\
    <a class="brand">[brand]</a>\
    <ul class="nav">\
    </ul>\
    <img src="lib/images/ui/spinner.gif" id="spinner"/>\
    <ul class="nav secondary-nav">\
     <li><a href="#!Login Page">Login</a></li>\
    </ul>\
   </div>\
   </div>\
   </div>');$('.brand').attr('href','#!'+(wn.boot.website_settings.home_page||'Login Page'))},make_items:function(){var items=wn.boot.website_menus;for(var i=0;i<items.length;i++){var item=items[i];if(!item.parent_label&&item.parentfield=='top_bar_items'){item.route=item.url||item.custom_page;$('header .nav:first').append(repl('<li data-label="%(label)s">\
     <a href="#!%(route)s">%(label)s</a></li>',item))}}
for(var i=0;i<items.length;i++){var item=items[i];if(item.parent_label&&item.parentfield=='top_bar_items'){$parent_li=$(repl('header li[data-label="%(parent_label)s"]',item));if(!$parent_li.hasClass('dropdown')){$parent_li.addClass('dropdown');$parent_li.find('a:first').addClass('dropdown-toggle');$parent_li.append('<ul class="dropdown-menu"></ul>');}
item.route=item.url||item.custom_page;$parent_li.find('.dropdown-menu').append(repl('<li data-label="%(label)s">\
     <a href="#!%(route)s">%(label)s</a></li>',item))}}}});erpnext.Footer=Class.extend({init:function(){$('footer').html(repl('<div class="web-footer">\
   <div class="web-footer-menu"><ul></ul></div>\
   <div class="web-footer-address">%(address)s</div>\
   <div class="web-footer-copyright">&copy; %(copyright)s</div>\
   <div class="web-footer-powered">Powered by \
    <a href="https://erpnext.com">erpnext.com</a></div>\
  </div>',wn.boot.website_settings));this.make_items();},make_items:function(){var items=wn.boot.website_menus
for(var i=0;i<items.length;i++){var item=items[i];if(!item.parent_label&&item.parentfield=='footer_items'){item.route=item.url||item.custom_page;$('.web-footer-menu ul').append(repl('<li><a href="#!%(route)s" \
     data-label="%(label)s">%(label)s</a></li>',item))}}}});$(document).bind('startup',function(){erpnext.footer=new erpnext.Footer();erpnext.topbar.topbar=new erpnext.topbar.TopBar();})