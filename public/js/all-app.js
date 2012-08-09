
/*
 *	lib/js/lib/jquery/jquery.ui.core.js
 */
;/*!
 * jQuery UI 1.8.18
 *
 * Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI
 */
(function(a,b){function d(b){return!a(b).parents().andSelf().filter(function(){return a.curCSS(this,"visibility")==="hidden"||a.expr.filters.hidden(this)}).length}function c(b,c){var e=b.nodeName.toLowerCase();if("area"===e){var f=b.parentNode,g=f.name,h;if(!b.href||!g||f.nodeName.toLowerCase()!=="map")return!1;h=a("img[usemap=#"+g+"]")[0];return!!h&&d(h)}return(/input|select|textarea|button|object/.test(e)?!b.disabled:"a"==e?b.href||c:c)&&d(b)}a.ui=a.ui||{};a.ui.version||(a.extend(a.ui,{version:"1.8.18",keyCode:{ALT:18,BACKSPACE:8,CAPS_LOCK:20,COMMA:188,COMMAND:91,COMMAND_LEFT:91,COMMAND_RIGHT:93,CONTROL:17,DELETE:46,DOWN:40,END:35,ENTER:13,ESCAPE:27,HOME:36,INSERT:45,LEFT:37,MENU:93,NUMPAD_ADD:107,NUMPAD_DECIMAL:110,NUMPAD_DIVIDE:111,NUMPAD_ENTER:108,NUMPAD_MULTIPLY:106,NUMPAD_SUBTRACT:109,PAGE_DOWN:34,PAGE_UP:33,PERIOD:190,RIGHT:39,SHIFT:16,SPACE:32,TAB:9,UP:38,WINDOWS:91}}),a.fn.extend({propAttr:a.fn.prop||a.fn.attr,_focus:a.fn.focus,focus:function(b,c){return typeof b=="number"?this.each(function(){var d=this;setTimeout(function(){a(d).focus(),c&&c.call(d)},b)}):this._focus.apply(this,arguments)},scrollParent:function(){var b;a.browser.msie&&/(static|relative)/.test(this.css("position"))||/absolute/.test(this.css("position"))?b=this.parents().filter(function(){return/(relative|absolute|fixed)/.test(a.curCSS(this,"position",1))&&/(auto|scroll)/.test(a.curCSS(this,"overflow",1)+a.curCSS(this,"overflow-y",1)+a.curCSS(this,"overflow-x",1))}).eq(0):b=this.parents().filter(function(){return/(auto|scroll)/.test(a.curCSS(this,"overflow",1)+a.curCSS(this,"overflow-y",1)+a.curCSS(this,"overflow-x",1))}).eq(0);return/fixed/.test(this.css("position"))||!b.length?a(document):b},zIndex:function(c){if(c!==b)return this.css("zIndex",c);if(this.length){var d=a(this[0]),e,f;while(d.length&&d[0]!==document){e=d.css("position");if(e==="absolute"||e==="relative"||e==="fixed"){f=parseInt(d.css("zIndex"),10);if(!isNaN(f)&&f!==0)return f}d=d.parent()}}return 0},disableSelection:function(){return this.bind((a.support.selectstart?"selectstart":"mousedown")+".ui-disableSelection",function(a){a.preventDefault()})},enableSelection:function(){return this.unbind(".ui-disableSelection")}}),a.each(["Width","Height"],function(c,d){function h(b,c,d,f){a.each(e,function(){c-=parseFloat(a.curCSS(b,"padding"+this,!0))||0,d&&(c-=parseFloat(a.curCSS(b,"border"+this+"Width",!0))||0),f&&(c-=parseFloat(a.curCSS(b,"margin"+this,!0))||0)});return c}var e=d==="Width"?["Left","Right"]:["Top","Bottom"],f=d.toLowerCase(),g={innerWidth:a.fn.innerWidth,innerHeight:a.fn.innerHeight,outerWidth:a.fn.outerWidth,outerHeight:a.fn.outerHeight};a.fn["inner"+d]=function(c){if(c===b)return g["inner"+d].call(this);return this.each(function(){a(this).css(f,h(this,c)+"px")})},a.fn["outer"+d]=function(b,c){if(typeof b!="number")return g["outer"+d].call(this,b);return this.each(function(){a(this).css(f,h(this,b,!0,c)+"px")})}}),a.extend(a.expr[":"],{data:function(b,c,d){return!!a.data(b,d[3])},focusable:function(b){return c(b,!isNaN(a.attr(b,"tabindex")))},tabbable:function(b){var d=a.attr(b,"tabindex"),e=isNaN(d);return(e||d>=0)&&c(b,!e)}}),a(function(){var b=document.body,c=b.appendChild(c=document.createElement("div"));c.offsetHeight,a.extend(c.style,{minHeight:"100px",height:"auto",padding:0,borderWidth:0}),a.support.minHeight=c.offsetHeight===100,a.support.selectstart="onselectstart"in c,b.removeChild(c).style.display="none"}),a.extend(a.ui,{plugin:{add:function(b,c,d){var e=a.ui[b].prototype;for(var f in d)e.plugins[f]=e.plugins[f]||[],e.plugins[f].push([c,d[f]])},call:function(a,b,c){var d=a.plugins[b];if(!!d&&!!a.element[0].parentNode)for(var e=0;e<d.length;e++)a.options[d[e][0]]&&d[e][1].apply(a.element,c)}},contains:function(a,b){return document.compareDocumentPosition?a.compareDocumentPosition(b)&16:a!==b&&a.contains(b)},hasScroll:function(b,c){if(a(b).css("overflow")==="hidden")return!1;var d=c&&c==="left"?"scrollLeft":"scrollTop",e=!1;if(b[d]>0)return!0;b[d]=1,e=b[d]>0,b[d]=0;return e},isOverAxis:function(a,b,c){return a>b&&a<b+c},isOver:function(b,c,d,e,f,g){return a.ui.isOverAxis(b,d,f)&&a.ui.isOverAxis(c,e,g)}}))})(jQuery);
/*!
 * jQuery UI Widget 1.8.18
 *
 * Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Widget
 */
(function(a,b){if(a.cleanData){var c=a.cleanData;a.cleanData=function(b){for(var d=0,e;(e=b[d])!=null;d++)try{a(e).triggerHandler("remove")}catch(f){}c(b)}}else{var d=a.fn.remove;a.fn.remove=function(b,c){return this.each(function(){c||(!b||a.filter(b,[this]).length)&&a("*",this).add([this]).each(function(){try{a(this).triggerHandler("remove")}catch(b){}});return d.call(a(this),b,c)})}}a.widget=function(b,c,d){var e=b.split(".")[0],f;b=b.split(".")[1],f=e+"-"+b,d||(d=c,c=a.Widget),a.expr[":"][f]=function(c){return!!a.data(c,b)},a[e]=a[e]||{},a[e][b]=function(a,b){arguments.length&&this._createWidget(a,b)};var g=new c;g.options=a.extend(!0,{},g.options),a[e][b].prototype=a.extend(!0,g,{namespace:e,widgetName:b,widgetEventPrefix:a[e][b].prototype.widgetEventPrefix||b,widgetBaseClass:f},d),a.widget.bridge(b,a[e][b])},a.widget.bridge=function(c,d){a.fn[c]=function(e){var f=typeof e=="string",g=Array.prototype.slice.call(arguments,1),h=this;e=!f&&g.length?a.extend.apply(null,[!0,e].concat(g)):e;if(f&&e.charAt(0)==="_")return h;f?this.each(function(){var d=a.data(this,c),f=d&&a.isFunction(d[e])?d[e].apply(d,g):d;if(f!==d&&f!==b){h=f;return!1}}):this.each(function(){var b=a.data(this,c);b?b.option(e||{})._init():a.data(this,c,new d(e,this))});return h}},a.Widget=function(a,b){arguments.length&&this._createWidget(a,b)},a.Widget.prototype={widgetName:"widget",widgetEventPrefix:"",options:{disabled:!1},_createWidget:function(b,c){a.data(c,this.widgetName,this),this.element=a(c),this.options=a.extend(!0,{},this.options,this._getCreateOptions(),b);var d=this;this.element.bind("remove."+this.widgetName,function(){d.destroy()}),this._create(),this._trigger("create"),this._init()},_getCreateOptions:function(){return a.metadata&&a.metadata.get(this.element[0])[this.widgetName]},_create:function(){},_init:function(){},destroy:function(){this.element.unbind("."+this.widgetName).removeData(this.widgetName),this.widget().unbind("."+this.widgetName).removeAttr("aria-disabled").removeClass(this.widgetBaseClass+"-disabled "+"ui-state-disabled")},widget:function(){return this.element},option:function(c,d){var e=c;if(arguments.length===0)return a.extend({},this.options);if(typeof c=="string"){if(d===b)return this.options[c];e={},e[c]=d}this._setOptions(e);return this},_setOptions:function(b){var c=this;a.each(b,function(a,b){c._setOption(a,b)});return this},_setOption:function(a,b){this.options[a]=b,a==="disabled"&&this.widget()[b?"addClass":"removeClass"](this.widgetBaseClass+"-disabled"+" "+"ui-state-disabled").attr("aria-disabled",b);return this},enable:function(){return this._setOption("disabled",!1)},disable:function(){return this._setOption("disabled",!0)},_trigger:function(b,c,d){var e,f,g=this.options[b];d=d||{},c=a.Event(c),c.type=(b===this.widgetEventPrefix?b:this.widgetEventPrefix+b).toLowerCase(),c.target=this.element[0],f=c.originalEvent;if(f)for(e in f)e in c||(c[e]=f[e]);this.element.trigger(c,d);return!(a.isFunction(g)&&g.call(this.element[0],c,d)===!1||c.isDefaultPrevented())}}})(jQuery);
/*!
 * jQuery UI Mouse 1.8.18
 *
 * Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Mouse
 *
 * Depends:
 *	jquery.ui.widget.js
 */
(function(a,b){var c=!1;a(document).mouseup(function(a){c=!1}),a.widget("ui.mouse",{options:{cancel:":input,option",distance:1,delay:0},_mouseInit:function(){var b=this;this.element.bind("mousedown."+this.widgetName,function(a){return b._mouseDown(a)}).bind("click."+this.widgetName,function(c){if(!0===a.data(c.target,b.widgetName+".preventClickEvent")){a.removeData(c.target,b.widgetName+".preventClickEvent"),c.stopImmediatePropagation();return!1}}),this.started=!1},_mouseDestroy:function(){this.element.unbind("."+this.widgetName)},_mouseDown:function(b){if(!c){this._mouseStarted&&this._mouseUp(b),this._mouseDownEvent=b;var d=this,e=b.which==1,f=typeof this.options.cancel=="string"&&b.target.nodeName?a(b.target).closest(this.options.cancel).length:!1;if(!e||f||!this._mouseCapture(b))return!0;this.mouseDelayMet=!this.options.delay,this.mouseDelayMet||(this._mouseDelayTimer=setTimeout(function(){d.mouseDelayMet=!0},this.options.delay));if(this._mouseDistanceMet(b)&&this._mouseDelayMet(b)){this._mouseStarted=this._mouseStart(b)!==!1;if(!this._mouseStarted){b.preventDefault();return!0}}!0===a.data(b.target,this.widgetName+".preventClickEvent")&&a.removeData(b.target,this.widgetName+".preventClickEvent"),this._mouseMoveDelegate=function(a){return d._mouseMove(a)},this._mouseUpDelegate=function(a){return d._mouseUp(a)},a(document).bind("mousemove."+this.widgetName,this._mouseMoveDelegate).bind("mouseup."+this.widgetName,this._mouseUpDelegate),b.preventDefault(),c=!0;return!0}},_mouseMove:function(b){if(a.browser.msie&&!(document.documentMode>=9)&&!b.button)return this._mouseUp(b);if(this._mouseStarted){this._mouseDrag(b);return b.preventDefault()}this._mouseDistanceMet(b)&&this._mouseDelayMet(b)&&(this._mouseStarted=this._mouseStart(this._mouseDownEvent,b)!==!1,this._mouseStarted?this._mouseDrag(b):this._mouseUp(b));return!this._mouseStarted},_mouseUp:function(b){a(document).unbind("mousemove."+this.widgetName,this._mouseMoveDelegate).unbind("mouseup."+this.widgetName,this._mouseUpDelegate),this._mouseStarted&&(this._mouseStarted=!1,b.target==this._mouseDownEvent.target&&a.data(b.target,this.widgetName+".preventClickEvent",!0),this._mouseStop(b));return!1},_mouseDistanceMet:function(a){return Math.max(Math.abs(this._mouseDownEvent.pageX-a.pageX),Math.abs(this._mouseDownEvent.pageY-a.pageY))>=this.options.distance},_mouseDelayMet:function(a){return this.mouseDelayMet},_mouseStart:function(a){},_mouseDrag:function(a){},_mouseStop:function(a){},_mouseCapture:function(a){return!0}})})(jQuery);
/*
 * jQuery UI Position 1.8.18
 *
 * Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Position
 */
(function(a,b){a.ui=a.ui||{};var c=/left|center|right/,d=/top|center|bottom/,e="center",f={},g=a.fn.position,h=a.fn.offset;a.fn.position=function(b){if(!b||!b.of)return g.apply(this,arguments);b=a.extend({},b);var h=a(b.of),i=h[0],j=(b.collision||"flip").split(" "),k=b.offset?b.offset.split(" "):[0,0],l,m,n;i.nodeType===9?(l=h.width(),m=h.height(),n={top:0,left:0}):i.setTimeout?(l=h.width(),m=h.height(),n={top:h.scrollTop(),left:h.scrollLeft()}):i.preventDefault?(b.at="left top",l=m=0,n={top:b.of.pageY,left:b.of.pageX}):(l=h.outerWidth(),m=h.outerHeight(),n=h.offset()),a.each(["my","at"],function(){var a=(b[this]||"").split(" ");a.length===1&&(a=c.test(a[0])?a.concat([e]):d.test(a[0])?[e].concat(a):[e,e]),a[0]=c.test(a[0])?a[0]:e,a[1]=d.test(a[1])?a[1]:e,b[this]=a}),j.length===1&&(j[1]=j[0]),k[0]=parseInt(k[0],10)||0,k.length===1&&(k[1]=k[0]),k[1]=parseInt(k[1],10)||0,b.at[0]==="right"?n.left+=l:b.at[0]===e&&(n.left+=l/2),b.at[1]==="bottom"?n.top+=m:b.at[1]===e&&(n.top+=m/2),n.left+=k[0],n.top+=k[1];return this.each(function(){var c=a(this),d=c.outerWidth(),g=c.outerHeight(),h=parseInt(a.curCSS(this,"marginLeft",!0))||0,i=parseInt(a.curCSS(this,"marginTop",!0))||0,o=d+h+(parseInt(a.curCSS(this,"marginRight",!0))||0),p=g+i+(parseInt(a.curCSS(this,"marginBottom",!0))||0),q=a.extend({},n),r;b.my[0]==="right"?q.left-=d:b.my[0]===e&&(q.left-=d/2),b.my[1]==="bottom"?q.top-=g:b.my[1]===e&&(q.top-=g/2),f.fractions||(q.left=Math.round(q.left),q.top=Math.round(q.top)),r={left:q.left-h,top:q.top-i},a.each(["left","top"],function(c,e){a.ui.position[j[c]]&&a.ui.position[j[c]][e](q,{targetWidth:l,targetHeight:m,elemWidth:d,elemHeight:g,collisionPosition:r,collisionWidth:o,collisionHeight:p,offset:k,my:b.my,at:b.at})}),a.fn.bgiframe&&c.bgiframe(),c.offset(a.extend(q,{using:b.using}))})},a.ui.position={fit:{left:function(b,c){var d=a(window),e=c.collisionPosition.left+c.collisionWidth-d.width()-d.scrollLeft();b.left=e>0?b.left-e:Math.max(b.left-c.collisionPosition.left,b.left)},top:function(b,c){var d=a(window),e=c.collisionPosition.top+c.collisionHeight-d.height()-d.scrollTop();b.top=e>0?b.top-e:Math.max(b.top-c.collisionPosition.top,b.top)}},flip:{left:function(b,c){if(c.at[0]!==e){var d=a(window),f=c.collisionPosition.left+c.collisionWidth-d.width()-d.scrollLeft(),g=c.my[0]==="left"?-c.elemWidth:c.my[0]==="right"?c.elemWidth:0,h=c.at[0]==="left"?c.targetWidth:-c.targetWidth,i=-2*c.offset[0];b.left+=c.collisionPosition.left<0?g+h+i:f>0?g+h+i:0}},top:function(b,c){if(c.at[1]!==e){var d=a(window),f=c.collisionPosition.top+c.collisionHeight-d.height()-d.scrollTop(),g=c.my[1]==="top"?-c.elemHeight:c.my[1]==="bottom"?c.elemHeight:0,h=c.at[1]==="top"?c.targetHeight:-c.targetHeight,i=-2*c.offset[1];b.top+=c.collisionPosition.top<0?g+h+i:f>0?g+h+i:0}}}},a.offset.setOffset||(a.offset.setOffset=function(b,c){/static/.test(a.curCSS(b,"position"))&&(b.style.position="relative");var d=a(b),e=d.offset(),f=parseInt(a.curCSS(b,"top",!0),10)||0,g=parseInt(a.curCSS(b,"left",!0),10)||0,h={top:c.top-e.top+f,left:c.left-e.left+g};"using"in c?c.using.call(b,h):d.css(h)},a.fn.offset=function(b){var c=this[0];if(!c||!c.ownerDocument)return null;if(b)return this.each(function(){a.offset.setOffset(this,b)});return h.call(this)}),function(){var b=document.getElementsByTagName("body")[0],c=document.createElement("div"),d,e,g,h,i;d=document.createElement(b?"div":"body"),g={visibility:"hidden",width:0,height:0,border:0,margin:0,background:"none"},b&&a.extend(g,{position:"absolute",left:"-1000px",top:"-1000px"});for(var j in g)d.style[j]=g[j];d.appendChild(c),e=b||document.documentElement,e.insertBefore(d,e.firstChild),c.style.cssText="position: absolute; left: 10.7432222px; top: 10.432325px; height: 30px; width: 201px;",h=a(c).offset(function(a,b){return b}).offset(),d.innerHTML="",e.removeChild(d),i=h.top+h.left+(b?2e3:0),f.fractions=i>21&&i<22}()})(jQuery);


/*
 *	lib/js/lib/jquery/jquery.ui.datepicker.js
 */
/* jQuery UI Datepicker 1.8.18
 *
 * Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://jquery.org/license
 *
 * http://docs.jquery.com/UI/Datepicker
 *
 * Depends:
 *	jquery.ui.core.js
 */(function($,undefined){function isArray(a){return a&&($.browser.safari&&typeof a=="object"&&a.length||a.constructor&&a.constructor.toString().match(/\Array\(\)/))}function extendRemove(a,b){$.extend(a,b);for(var c in b)if(b[c]==null||b[c]==undefined)a[c]=b[c];return a}function bindHover(a){var b="button, .ui-datepicker-prev, .ui-datepicker-next, .ui-datepicker-calendar td a";return a.bind("mouseout",function(a){var c=$(a.target).closest(b);!c.length||c.removeClass("ui-state-hover ui-datepicker-prev-hover ui-datepicker-next-hover")}).bind("mouseover",function(c){var d=$(c.target).closest(b);!$.datepicker._isDisabledDatepicker(instActive.inline?a.parent()[0]:instActive.input[0])&&!!d.length&&(d.parents(".ui-datepicker-calendar").find("a").removeClass("ui-state-hover"),d.addClass("ui-state-hover"),d.hasClass("ui-datepicker-prev")&&d.addClass("ui-datepicker-prev-hover"),d.hasClass("ui-datepicker-next")&&d.addClass("ui-datepicker-next-hover"))})}function Datepicker(){this.debug=!1,this._curInst=null,this._keyEvent=!1,this._disabledInputs=[],this._datepickerShowing=!1,this._inDialog=!1,this._mainDivId="ui-datepicker-div",this._inlineClass="ui-datepicker-inline",this._appendClass="ui-datepicker-append",this._triggerClass="ui-datepicker-trigger",this._dialogClass="ui-datepicker-dialog",this._disableClass="ui-datepicker-disabled",this._unselectableClass="ui-datepicker-unselectable",this._currentClass="ui-datepicker-current-day",this._dayOverClass="ui-datepicker-days-cell-over",this.regional=[],this.regional[""]={closeText:"Done",prevText:"Prev",nextText:"Next",currentText:"Today",monthNames:["January","February","March","April","May","June","July","August","September","October","November","December"],monthNamesShort:["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],dayNames:["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],dayNamesShort:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],dayNamesMin:["Su","Mo","Tu","We","Th","Fr","Sa"],weekHeader:"Wk",dateFormat:"mm/dd/yy",firstDay:0,isRTL:!1,showMonthAfterYear:!1,yearSuffix:""},this._defaults={showOn:"focus",showAnim:"fadeIn",showOptions:{},defaultDate:null,appendText:"",buttonText:"...",buttonImage:"",buttonImageOnly:!1,hideIfNoPrevNext:!1,navigationAsDateFormat:!1,gotoCurrent:!1,changeMonth:!1,changeYear:!1,yearRange:"c-10:c+10",showOtherMonths:!1,selectOtherMonths:!1,showWeek:!1,calculateWeek:this.iso8601Week,shortYearCutoff:"+10",minDate:null,maxDate:null,duration:"fast",beforeShowDay:null,beforeShow:null,onSelect:null,onChangeMonthYear:null,onClose:null,numberOfMonths:1,showCurrentAtPos:0,stepMonths:1,stepBigMonths:12,altField:"",altFormat:"",constrainInput:!0,showButtonPanel:!1,autoSize:!1,disabled:!1},$.extend(this._defaults,this.regional[""]),this.dpDiv=bindHover($('<div id="'+this._mainDivId+'" class="ui-datepicker ui-widget ui-widget-content ui-helper-clearfix ui-corner-all"></div>'))}$.extend($.ui,{datepicker:{version:"1.8.18"}});var PROP_NAME="datepicker",dpuuid=(new Date).getTime(),instActive;$.extend(Datepicker.prototype,{markerClassName:"hasDatepicker",maxRows:4,log:function(){this.debug&&console.log.apply("",arguments)},_widgetDatepicker:function(){return this.dpDiv},setDefaults:function(a){extendRemove(this._defaults,a||{});return this},_attachDatepicker:function(target,settings){var inlineSettings=null;for(var attrName in this._defaults){var attrValue=target.getAttribute("date:"+attrName);if(attrValue){inlineSettings=inlineSettings||{};try{inlineSettings[attrName]=eval(attrValue)}catch(err){inlineSettings[attrName]=attrValue}}}var nodeName=target.nodeName.toLowerCase(),inline=nodeName=="div"||nodeName=="span";target.id||(this.uuid+=1,target.id="dp"+this.uuid);var inst=this._newInst($(target),inline);inst.settings=$.extend({},settings||{},inlineSettings||{}),nodeName=="input"?this._connectDatepicker(target,inst):inline&&this._inlineDatepicker(target,inst)},_newInst:function(a,b){var c=a[0].id.replace(/([^A-Za-z0-9_-])/g,"\\\\$1");return{id:c,input:a,selectedDay:0,selectedMonth:0,selectedYear:0,drawMonth:0,drawYear:0,inline:b,dpDiv:b?bindHover($('<div class="'+this._inlineClass+' ui-datepicker ui-widget ui-widget-content ui-helper-clearfix ui-corner-all"></div>')):this.dpDiv}},_connectDatepicker:function(a,b){var c=$(a);b.append=$([]),b.trigger=$([]);c.hasClass(this.markerClassName)||(this._attachments(c,b),c.addClass(this.markerClassName).keydown(this._doKeyDown).keypress(this._doKeyPress).keyup(this._doKeyUp).bind("setData.datepicker",function(a,c,d){b.settings[c]=d}).bind("getData.datepicker",function(a,c){return this._get(b,c)}),this._autoSize(b),$.data(a,PROP_NAME,b),b.settings.disabled&&this._disableDatepicker(a))},_attachments:function(a,b){var c=this._get(b,"appendText"),d=this._get(b,"isRTL");b.append&&b.append.remove(),c&&(b.append=$('<span class="'+this._appendClass+'">'+c+"</span>"),a[d?"before":"after"](b.append)),a.unbind("focus",this._showDatepicker),b.trigger&&b.trigger.remove();var e=this._get(b,"showOn");(e=="focus"||e=="both")&&a.focus(this._showDatepicker);if(e=="button"||e=="both"){var f=this._get(b,"buttonText"),g=this._get(b,"buttonImage");b.trigger=$(this._get(b,"buttonImageOnly")?$("<img/>").addClass(this._triggerClass).attr({src:g,alt:f,title:f}):$('<button type="button"></button>').addClass(this._triggerClass).html(g==""?f:$("<img/>").attr({src:g,alt:f,title:f}))),a[d?"before":"after"](b.trigger),b.trigger.click(function(){$.datepicker._datepickerShowing&&$.datepicker._lastInput==a[0]?$.datepicker._hideDatepicker():$.datepicker._datepickerShowing&&$.datepicker._lastInput!=a[0]?($.datepicker._hideDatepicker(),$.datepicker._showDatepicker(a[0])):$.datepicker._showDatepicker(a[0]);return!1})}},_autoSize:function(a){if(this._get(a,"autoSize")&&!a.inline){var b=new Date(2009,11,20),c=this._get(a,"dateFormat");if(c.match(/[DM]/)){var d=function(a){var b=0,c=0;for(var d=0;d<a.length;d++)a[d].length>b&&(b=a[d].length,c=d);return c};b.setMonth(d(this._get(a,c.match(/MM/)?"monthNames":"monthNamesShort"))),b.setDate(d(this._get(a,c.match(/DD/)?"dayNames":"dayNamesShort"))+20-b.getDay())}a.input.attr("size",this._formatDate(a,b).length)}},_inlineDatepicker:function(a,b){var c=$(a);c.hasClass(this.markerClassName)||(c.addClass(this.markerClassName).append(b.dpDiv).bind("setData.datepicker",function(a,c,d){b.settings[c]=d}).bind("getData.datepicker",function(a,c){return this._get(b,c)}),$.data(a,PROP_NAME,b),this._setDate(b,this._getDefaultDate(b),!0),this._updateDatepicker(b),this._updateAlternate(b),b.settings.disabled&&this._disableDatepicker(a),b.dpDiv.css("display","block"))},_dialogDatepicker:function(a,b,c,d,e){var f=this._dialogInst;if(!f){this.uuid+=1;var g="dp"+this.uuid;this._dialogInput=$('<input type="text" id="'+g+'" style="position: absolute; top: -100px; width: 0px; z-index: -10;"/>'),this._dialogInput.keydown(this._doKeyDown),$("body").append(this._dialogInput),f=this._dialogInst=this._newInst(this._dialogInput,!1),f.settings={},$.data(this._dialogInput[0],PROP_NAME,f)}extendRemove(f.settings,d||{}),b=b&&b.constructor==Date?this._formatDate(f,b):b,this._dialogInput.val(b),this._pos=e?e.length?e:[e.pageX,e.pageY]:null;if(!this._pos){var h=document.documentElement.clientWidth,i=document.documentElement.clientHeight,j=document.documentElement.scrollLeft||document.body.scrollLeft,k=document.documentElement.scrollTop||document.body.scrollTop;this._pos=[h/2-100+j,i/2-150+k]}this._dialogInput.css("left",this._pos[0]+20+"px").css("top",this._pos[1]+"px"),f.settings.onSelect=c,this._inDialog=!0,this.dpDiv.addClass(this._dialogClass),this._showDatepicker(this._dialogInput[0]),$.blockUI&&$.blockUI(this.dpDiv),$.data(this._dialogInput[0],PROP_NAME,f);return this},_destroyDatepicker:function(a){var b=$(a),c=$.data(a,PROP_NAME);if(!!b.hasClass(this.markerClassName)){var d=a.nodeName.toLowerCase();$.removeData(a,PROP_NAME),d=="input"?(c.append.remove(),c.trigger.remove(),b.removeClass(this.markerClassName).unbind("focus",this._showDatepicker).unbind("keydown",this._doKeyDown).unbind("keypress",this._doKeyPress).unbind("keyup",this._doKeyUp)):(d=="div"||d=="span")&&b.removeClass(this.markerClassName).empty()}},_enableDatepicker:function(a){var b=$(a),c=$.data(a,PROP_NAME);if(!!b.hasClass(this.markerClassName)){var d=a.nodeName.toLowerCase();if(d=="input")a.disabled=!1,c.trigger.filter("button").each(function(){this.disabled=!1}).end().filter("img").css({opacity:"1.0",cursor:""});else if(d=="div"||d=="span"){var e=b.children("."+this._inlineClass);e.children().removeClass("ui-state-disabled"),e.find("select.ui-datepicker-month, select.ui-datepicker-year").removeAttr("disabled")}this._disabledInputs=$.map(this._disabledInputs,function(b){return b==a?null:b})}},_disableDatepicker:function(a){var b=$(a),c=$.data(a,PROP_NAME);if(!!b.hasClass(this.markerClassName)){var d=a.nodeName.toLowerCase();if(d=="input")a.disabled=!0,c.trigger.filter("button").each(function(){this.disabled=!0}).end().filter("img").css({opacity:"0.5",cursor:"default"});else if(d=="div"||d=="span"){var e=b.children("."+this._inlineClass);e.children().addClass("ui-state-disabled"),e.find("select.ui-datepicker-month, select.ui-datepicker-year").attr("disabled","disabled")}this._disabledInputs=$.map(this._disabledInputs,function(b){return b==a?null:b}),this._disabledInputs[this._disabledInputs.length]=a}},_isDisabledDatepicker:function(a){if(!a)return!1;for(var b=0;b<this._disabledInputs.length;b++)if(this._disabledInputs[b]==a)return!0;return!1},_getInst:function(a){try{return $.data(a,PROP_NAME)}catch(b){throw"Missing instance data for this datepicker"}},_optionDatepicker:function(a,b,c){var d=this._getInst(a);if(arguments.length==2&&typeof b=="string")return b=="defaults"?$.extend({},$.datepicker._defaults):d?b=="all"?$.extend({},d.settings):this._get(d,b):null;var e=b||{};typeof b=="string"&&(e={},e[b]=c);if(d){this._curInst==d&&this._hideDatepicker();var f=this._getDateDatepicker(a,!0),g=this._getMinMaxDate(d,"min"),h=this._getMinMaxDate(d,"max");extendRemove(d.settings,e),g!==null&&e.dateFormat!==undefined&&e.minDate===undefined&&(d.settings.minDate=this._formatDate(d,g)),h!==null&&e.dateFormat!==undefined&&e.maxDate===undefined&&(d.settings.maxDate=this._formatDate(d,h)),this._attachments($(a),d),this._autoSize(d),this._setDate(d,f),this._updateAlternate(d),this._updateDatepicker(d)}},_changeDatepicker:function(a,b,c){this._optionDatepicker(a,b,c)},_refreshDatepicker:function(a){var b=this._getInst(a);b&&this._updateDatepicker(b)},_setDateDatepicker:function(a,b){var c=this._getInst(a);c&&(this._setDate(c,b),this._updateDatepicker(c),this._updateAlternate(c))},_getDateDatepicker:function(a,b){var c=this._getInst(a);c&&!c.inline&&this._setDateFromField(c,b);return c?this._getDate(c):null},_doKeyDown:function(a){var b=$.datepicker._getInst(a.target),c=!0,d=b.dpDiv.is(".ui-datepicker-rtl");b._keyEvent=!0;if($.datepicker._datepickerShowing)switch(a.keyCode){case 9:$.datepicker._hideDatepicker(),c=!1;break;case 13:var e=$("td."+$.datepicker._dayOverClass+":not(."+$.datepicker._currentClass+")",b.dpDiv);e[0]&&$.datepicker._selectDay(a.target,b.selectedMonth,b.selectedYear,e[0]);var f=$.datepicker._get(b,"onSelect");if(f){var g=$.datepicker._formatDate(b);f.apply(b.input?b.input[0]:null,[g,b])}else $.datepicker._hideDatepicker();return!1;case 27:$.datepicker._hideDatepicker();break;case 33:$.datepicker._adjustDate(a.target,a.ctrlKey?-$.datepicker._get(b,"stepBigMonths"):-$.datepicker._get(b,"stepMonths"),"M");break;case 34:$.datepicker._adjustDate(a.target,a.ctrlKey?+$.datepicker._get(b,"stepBigMonths"):+$.datepicker._get(b,"stepMonths"),"M");break;case 35:(a.ctrlKey||a.metaKey)&&$.datepicker._clearDate(a.target),c=a.ctrlKey||a.metaKey;break;case 36:(a.ctrlKey||a.metaKey)&&$.datepicker._gotoToday(a.target),c=a.ctrlKey||a.metaKey;break;case 37:(a.ctrlKey||a.metaKey)&&$.datepicker._adjustDate(a.target,d?1:-1,"D"),c=a.ctrlKey||a.metaKey,a.originalEvent.altKey&&$.datepicker._adjustDate(a.target,a.ctrlKey?-$.datepicker._get(b,"stepBigMonths"):-$.datepicker._get(b,"stepMonths"),"M");break;case 38:(a.ctrlKey||a.metaKey)&&$.datepicker._adjustDate(a.target,-7,"D"),c=a.ctrlKey||a.metaKey;break;case 39:(a.ctrlKey||a.metaKey)&&$.datepicker._adjustDate(a.target,d?-1:1,"D"),c=a.ctrlKey||a.metaKey,a.originalEvent.altKey&&$.datepicker._adjustDate(a.target,a.ctrlKey?+$.datepicker._get(b,"stepBigMonths"):+$.datepicker._get(b,"stepMonths"),"M");break;case 40:(a.ctrlKey||a.metaKey)&&$.datepicker._adjustDate(a.target,7,"D"),c=a.ctrlKey||a.metaKey;break;default:c=!1}else a.keyCode==36&&a.ctrlKey?$.datepicker._showDatepicker(this):c=!1;c&&(a.preventDefault(),a.stopPropagation())},_doKeyPress:function(a){var b=$.datepicker._getInst(a.target);if($.datepicker._get(b,"constrainInput")){var c=$.datepicker._possibleChars($.datepicker._get(b,"dateFormat")),d=String.fromCharCode(a.charCode==undefined?a.keyCode:a.charCode);return a.ctrlKey||a.metaKey||d<" "||!c||c.indexOf(d)>-1}},_doKeyUp:function(a){var b=$.datepicker._getInst(a.target);if(b.input.val()!=b.lastVal)try{var c=$.datepicker.parseDate($.datepicker._get(b,"dateFormat"),b.input?b.input.val():null,$.datepicker._getFormatConfig(b));c&&($.datepicker._setDateFromField(b),$.datepicker._updateAlternate(b),$.datepicker._updateDatepicker(b))}catch(a){$.datepicker.log(a)}return!0},_showDatepicker:function(a){a=a.target||a,a.nodeName.toLowerCase()!="input"&&(a=$("input",a.parentNode)[0]);if(!$.datepicker._isDisabledDatepicker(a)&&$.datepicker._lastInput!=a){var b=$.datepicker._getInst(a);$.datepicker._curInst&&$.datepicker._curInst!=b&&($.datepicker._curInst.dpDiv.stop(!0,!0),b&&$.datepicker._datepickerShowing&&$.datepicker._hideDatepicker($.datepicker._curInst.input[0]));var c=$.datepicker._get(b,"beforeShow"),d=c?c.apply(a,[a,b]):{};if(d===!1)return;extendRemove(b.settings,d),b.lastVal=null,$.datepicker._lastInput=a,$.datepicker._setDateFromField(b),$.datepicker._inDialog&&(a.value=""),$.datepicker._pos||($.datepicker._pos=$.datepicker._findPos(a),$.datepicker._pos[1]+=a.offsetHeight);var e=!1;$(a).parents().each(function(){e|=$(this).css("position")=="fixed";return!e}),e&&$.browser.opera&&($.datepicker._pos[0]-=document.documentElement.scrollLeft,$.datepicker._pos[1]-=document.documentElement.scrollTop);var f={left:$.datepicker._pos[0],top:$.datepicker._pos[1]};$.datepicker._pos=null,b.dpDiv.empty(),b.dpDiv.css({position:"absolute",display:"block",top:"-1000px"}),$.datepicker._updateDatepicker(b),f=$.datepicker._checkOffset(b,f,e),b.dpDiv.css({position:$.datepicker._inDialog&&$.blockUI?"static":e?"fixed":"absolute",display:"none",left:f.left+"px",top:f.top+"px"});if(!b.inline){var g=$.datepicker._get(b,"showAnim"),h=$.datepicker._get(b,"duration"),i=function(){var a=b.dpDiv.find("iframe.ui-datepicker-cover");if(!!a.length){var c=$.datepicker._getBorders(b.dpDiv);a.css({left:-c[0],top:-c[1],width:b.dpDiv.outerWidth(),height:b.dpDiv.outerHeight()})}};b.dpDiv.zIndex($(a).zIndex()+1),$.datepicker._datepickerShowing=!0,$.effects&&$.effects[g]?b.dpDiv.show(g,$.datepicker._get(b,"showOptions"),h,i):b.dpDiv[g||"show"](g?h:null,i),(!g||!h)&&i(),b.input.is(":visible")&&!b.input.is(":disabled")&&b.input.focus(),$.datepicker._curInst=b}}},_updateDatepicker:function(a){var b=this;b.maxRows=4;var c=$.datepicker._getBorders(a.dpDiv);instActive=a,a.dpDiv.empty().append(this._generateHTML(a));var d=a.dpDiv.find("iframe.ui-datepicker-cover");!d.length||d.css({left:-c[0],top:-c[1],width:a.dpDiv.outerWidth(),height:a.dpDiv.outerHeight()}),a.dpDiv.find("."+this._dayOverClass+" a").mouseover();var e=this._getNumberOfMonths(a),f=e[1],g=17;a.dpDiv.removeClass("ui-datepicker-multi-2 ui-datepicker-multi-3 ui-datepicker-multi-4").width(""),f>1&&a.dpDiv.addClass("ui-datepicker-multi-"+f).css("width",g*f+"em"),a.dpDiv[(e[0]!=1||e[1]!=1?"add":"remove")+"Class"]("ui-datepicker-multi"),a.dpDiv[(this._get(a,"isRTL")?"add":"remove")+"Class"]("ui-datepicker-rtl"),a==$.datepicker._curInst&&$.datepicker._datepickerShowing&&a.input&&a.input.is(":visible")&&!a.input.is(":disabled")&&a.input[0]!=document.activeElement&&a.input.focus();if(a.yearshtml){var h=a.yearshtml;setTimeout(function(){h===a.yearshtml&&a.yearshtml&&a.dpDiv.find("select.ui-datepicker-year:first").replaceWith(a.yearshtml),h=a.yearshtml=null},0)}},_getBorders:function(a){var b=function(a){return{thin:1,medium:2,thick:3}[a]||a};return[parseFloat(b(a.css("border-left-width"))),parseFloat(b(a.css("border-top-width")))]},_checkOffset:function(a,b,c){var d=a.dpDiv.outerWidth(),e=a.dpDiv.outerHeight(),f=a.input?a.input.outerWidth():0,g=a.input?a.input.outerHeight():0,h=document.documentElement.clientWidth+$(document).scrollLeft(),i=document.documentElement.clientHeight+$(document).scrollTop();b.left-=this._get(a,"isRTL")?d-f:0,b.left-=c&&b.left==a.input.offset().left?$(document).scrollLeft():0,b.top-=c&&b.top==a.input.offset().top+g?$(document).scrollTop():0,b.left-=Math.min(b.left,b.left+d>h&&h>d?Math.abs(b.left+d-h):0),b.top-=Math.min(b.top,b.top+e>i&&i>e?Math.abs(e+g):0);return b},_findPos:function(a){var b=this._getInst(a),c=this._get(b,"isRTL");while(a&&(a.type=="hidden"||a.nodeType!=1||$.expr.filters.hidden(a)))a=a[c?"previousSibling":"nextSibling"];var d=$(a).offset();return[d.left,d.top]},_hideDatepicker:function(a){var b=this._curInst;if(!(!b||a&&b!=$.data(a,PROP_NAME))&&this._datepickerShowing){var c=this._get(b,"showAnim"),d=this._get(b,"duration"),e=this,f=function(){$.datepicker._tidyDialog(b),e._curInst=null};$.effects&&$.effects[c]?b.dpDiv.hide(c,$.datepicker._get(b,"showOptions"),d,f):b.dpDiv[c=="slideDown"?"slideUp":c=="fadeIn"?"fadeOut":"hide"](c?d:null,f),c||f(),this._datepickerShowing=!1;var g=this._get(b,"onClose");g&&g.apply(b.input?b.input[0]:null,[b.input?b.input.val():"",b]),this._lastInput=null,this._inDialog&&(this._dialogInput.css({position:"absolute",left:"0",top:"-100px"}),$.blockUI&&($.unblockUI(),$("body").append(this.dpDiv))),this._inDialog=!1}},_tidyDialog:function(a){a.dpDiv.removeClass(this._dialogClass).unbind(".ui-datepicker-calendar")},_checkExternalClick:function(a){if(!!$.datepicker._curInst){var b=$(a.target),c=$.datepicker._getInst(b[0]);(b[0].id!=$.datepicker._mainDivId&&b.parents("#"+$.datepicker._mainDivId).length==0&&!b.hasClass($.datepicker.markerClassName)&&!b.closest("."+$.datepicker._triggerClass).length&&$.datepicker._datepickerShowing&&(!$.datepicker._inDialog||!$.blockUI)||b.hasClass($.datepicker.markerClassName)&&$.datepicker._curInst!=c)&&$.datepicker._hideDatepicker()}},_adjustDate:function(a,b,c){var d=$(a),e=this._getInst(d[0]);this._isDisabledDatepicker(d[0])||(this._adjustInstDate(e,b+(c=="M"?this._get(e,"showCurrentAtPos"):0),c),this._updateDatepicker(e))},_gotoToday:function(a){var b=$(a),c=this._getInst(b[0]);if(this._get(c,"gotoCurrent")&&c.currentDay)c.selectedDay=c.currentDay,c.drawMonth=c.selectedMonth=c.currentMonth,c.drawYear=c.selectedYear=c.currentYear;else{var d=new Date;c.selectedDay=d.getDate(),c.drawMonth=c.selectedMonth=d.getMonth(),c.drawYear=c.selectedYear=d.getFullYear()}this._notifyChange(c),this._adjustDate(b)},_selectMonthYear:function(a,b,c){var d=$(a),e=this._getInst(d[0]);e["selected"+(c=="M"?"Month":"Year")]=e["draw"+(c=="M"?"Month":"Year")]=parseInt(b.options[b.selectedIndex].value,10),this._notifyChange(e),this._adjustDate(d)},_selectDay:function(a,b,c,d){var e=$(a);if(!$(d).hasClass(this._unselectableClass)&&!this._isDisabledDatepicker(e[0])){var f=this._getInst(e[0]);f.selectedDay=f.currentDay=$("a",d).html(),f.selectedMonth=f.currentMonth=b,f.selectedYear=f.currentYear=c,this._selectDate(a,this._formatDate(f,f.currentDay,f.currentMonth,f.currentYear))}},_clearDate:function(a){var b=$(a),c=this._getInst(b[0]);this._selectDate(b,"")},_selectDate:function(a,b){var c=$(a),d=this._getInst(c[0]);b=b!=null?b:this._formatDate(d),d.input&&d.input.val(b),this._updateAlternate(d);var e=this._get(d,"onSelect");e?e.apply(d.input?d.input[0]:null,[b,d]):d.input&&d.input.trigger("change"),d.inline?this._updateDatepicker(d):(this._hideDatepicker(),this._lastInput=d.input[0],typeof d.input[0]!="object"&&d.input.focus(),this._lastInput=null)},_updateAlternate:function(a){var b=this._get(a,"altField");if(b){var c=this._get(a,"altFormat")||this._get(a,"dateFormat"),d=this._getDate(a),e=this.formatDate(c,d,this._getFormatConfig(a));$(b).each(function(){$(this).val(e)})}},noWeekends:function(a){var b=a.getDay();return[b>0&&b<6,""]},iso8601Week:function(a){var b=new Date(a.getTime());b.setDate(b.getDate()+4-(b.getDay()||7));var c=b.getTime();b.setMonth(0),b.setDate(1);return Math.floor(Math.round((c-b)/864e5)/7)+1},parseDate:function(a,b,c){if(a==null||b==null)throw"Invalid arguments";b=typeof b=="object"?b.toString():b+"";if(b=="")return null;var d=(c?c.shortYearCutoff:null)||this._defaults.shortYearCutoff;d=typeof d!="string"?d:(new Date).getFullYear()%100+parseInt(d,10);var e=(c?c.dayNamesShort:null)||this._defaults.dayNamesShort,f=(c?c.dayNames:null)||this._defaults.dayNames,g=(c?c.monthNamesShort:null)||this._defaults.monthNamesShort,h=(c?c.monthNames:null)||this._defaults.monthNames,i=-1,j=-1,k=-1,l=-1,m=!1,n=function(b){var c=s+1<a.length&&a.charAt(s+1)==b;c&&s++;return c},o=function(a){var c=n(a),d=a=="@"?14:a=="!"?20:a=="y"&&c?4:a=="o"?3:2,e=new RegExp("^\\d{1,"+d+"}"),f=b.substring(r).match(e);if(!f)throw"Missing number at position "+r;r+=f[0].length;return parseInt(f[0],10)},p=function(a,c,d){var e=$.map(n(a)?d:c,function(a,b){return[[b,a]]}).sort(function(a,b){return-(a[1].length-b[1].length)}),f=-1;$.each(e,function(a,c){var d=c[1];if(b.substr(r,d.length).toLowerCase()==d.toLowerCase()){f=c[0],r+=d.length;return!1}});if(f!=-1)return f+1;throw"Unknown name at position "+r},q=function(){if(b.charAt(r)!=a.charAt(s))throw"Unexpected literal at position "+r;r++},r=0;for(var s=0;s<a.length;s++)if(m)a.charAt(s)=="'"&&!n("'")?m=!1:q();else switch(a.charAt(s)){case"d":k=o("d");break;case"D":p("D",e,f);break;case"o":l=o("o");break;case"m":j=o("m");break;case"M":j=p("M",g,h);break;case"y":i=o("y");break;case"@":var t=new Date(o("@"));i=t.getFullYear(),j=t.getMonth()+1,k=t.getDate();break;case"!":var t=new Date((o("!")-this._ticksTo1970)/1e4);i=t.getFullYear(),j=t.getMonth()+1,k=t.getDate();break;case"'":n("'")?q():m=!0;break;default:q()}if(r<b.length)throw"Extra/unparsed characters found in date: "+b.substring(r);i==-1?i=(new Date).getFullYear():i<100&&(i+=(new Date).getFullYear()-(new Date).getFullYear()%100+(i<=d?0:-100));if(l>-1){j=1,k=l;for(;;){var u=this._getDaysInMonth(i,j-1);if(k<=u)break;j++,k-=u}}var t=this._daylightSavingAdjust(new Date(i,j-1,k));if(t.getFullYear()!=i||t.getMonth()+1!=j||t.getDate()!=k)throw"Invalid date";return t},ATOM:"yy-mm-dd",COOKIE:"D, dd M yy",ISO_8601:"yy-mm-dd",RFC_822:"D, d M y",RFC_850:"DD, dd-M-y",RFC_1036:"D, d M y",RFC_1123:"D, d M yy",RFC_2822:"D, d M yy",RSS:"D, d M y",TICKS:"!",TIMESTAMP:"@",W3C:"yy-mm-dd",_ticksTo1970:(718685+Math.floor(492.5)-Math.floor(19.7)+Math.floor(4.925))*24*60*60*1e7,formatDate:function(a,b,c){if(!b)return"";var d=(c?c.dayNamesShort:null)||this._defaults.dayNamesShort,e=(c?c.dayNames:null)||this._defaults.dayNames,f=(c?c.monthNamesShort:null)||this._defaults.monthNamesShort,g=(c?c.monthNames:null)||this._defaults.monthNames,h=function(b){var c=m+1<a.length&&a.charAt(m+1)==b;c&&m++;return c},i=function(a,b,c){var d=""+b;if(h(a))while(d.length<c)d="0"+d;return d},j=function(a,b,c,d){return h(a)?d[b]:c[b]},k="",l=!1;if(b)for(var m=0;m<a.length;m++)if(l)a.charAt(m)=="'"&&!h("'")?l=!1:k+=a.charAt(m);else switch(a.charAt(m)){case"d":k+=i("d",b.getDate(),2);break;case"D":k+=j("D",b.getDay(),d,e);break;case"o":k+=i("o",Math.round(((new Date(b.getFullYear(),b.getMonth(),b.getDate())).getTime()-(new Date(b.getFullYear(),0,0)).getTime())/864e5),3);break;case"m":k+=i("m",b.getMonth()+1,2);break;case"M":k+=j("M",b.getMonth(),f,g);break;case"y":k+=h("y")?b.getFullYear():(b.getYear()%100<10?"0":"")+b.getYear()%100;break;case"@":k+=b.getTime();break;case"!":k+=b.getTime()*1e4+this._ticksTo1970;break;case"'":h("'")?k+="'":l=!0;break;default:k+=a.charAt(m)}return k},_possibleChars:function(a){var b="",c=!1,d=function(b){var c=e+1<a.length&&a.charAt(e+1)==b;c&&e++;return c};for(var e=0;e<a.length;e++)if(c)a.charAt(e)=="'"&&!d("'")?c=!1:b+=a.charAt(e);else switch(a.charAt(e)){case"d":case"m":case"y":case"@":b+="0123456789";break;case"D":case"M":return null;case"'":d("'")?b+="'":c=!0;break;default:b+=a.charAt(e)}return b},_get:function(a,b){return a.settings[b]!==undefined?a.settings[b]:this._defaults[b]},_setDateFromField:function(a,b){if(a.input.val()!=a.lastVal){var c=this._get(a,"dateFormat"),d=a.lastVal=a.input?a.input.val():null,e,f;e=f=this._getDefaultDate(a);var g=this._getFormatConfig(a);try{e=this.parseDate(c,d,g)||f}catch(h){this.log(h),d=b?"":d}a.selectedDay=e.getDate(),a.drawMonth=a.selectedMonth=e.getMonth(),a.drawYear=a.selectedYear=e.getFullYear(),a.currentDay=d?e.getDate():0,a.currentMonth=d?e.getMonth():0,a.currentYear=d?e.getFullYear():0,this._adjustInstDate(a)}},_getDefaultDate:function(a){return this._restrictMinMax(a,this._determineDate(a,this._get(a,"defaultDate"),new Date))},_determineDate:function(a,b,c){var d=function(a){var b=new Date;b.setDate(b.getDate()+a);return b},e=function(b){try{return $.datepicker.parseDate($.datepicker._get(a,"dateFormat"),b,$.datepicker._getFormatConfig(a))}catch(c){}var d=(b.toLowerCase().match(/^c/)?$.datepicker._getDate(a):null)||new Date,e=d.getFullYear(),f=d.getMonth(),g=d.getDate(),h=/([+-]?[0-9]+)\s*(d|D|w|W|m|M|y|Y)?/g,i=h.exec(b);while(i){switch(i[2]||"d"){case"d":case"D":g+=parseInt(i[1],10);break;case"w":case"W":g+=parseInt(i[1],10)*7;break;case"m":case"M":f+=parseInt(i[1],10),g=Math.min(g,$.datepicker._getDaysInMonth(e,f));break;case"y":case"Y":e+=parseInt(i[1],10),g=Math.min(g,$.datepicker._getDaysInMonth(e,f))}i=h.exec(b)}return new Date(e,f,g)},f=b==null||b===""?c:typeof b=="string"?e(b):typeof b=="number"?isNaN(b)?c:d(b):new Date(b.getTime());f=f&&f.toString()=="Invalid Date"?c:f,f&&(f.setHours(0),f.setMinutes(0),f.setSeconds(0),f.setMilliseconds(0));return this._daylightSavingAdjust(f)},_daylightSavingAdjust:function(a){if(!a)return null;a.setHours(a.getHours()>12?a.getHours()+2:0);return a},_setDate:function(a,b,c){var d=!b,e=a.selectedMonth,f=a.selectedYear,g=this._restrictMinMax(a,this._determineDate(a,b,new Date));a.selectedDay=a.currentDay=g.getDate(),a.drawMonth=a.selectedMonth=a.currentMonth=g.getMonth(),a.drawYear=a.selectedYear=a.currentYear=g.getFullYear(),(e!=a.selectedMonth||f!=a.selectedYear)&&!c&&this._notifyChange(a),this._adjustInstDate(a),a.input&&a.input.val(d?"":this._formatDate(a))},_getDate:function(a){var b=!a.currentYear||a.input&&a.input.val()==""?null:this._daylightSavingAdjust(new Date(a.currentYear,a.currentMonth,a.currentDay));return b},_generateHTML:function(a){var b=new Date;b=this._daylightSavingAdjust(new Date(b.getFullYear(),b.getMonth(),b.getDate()));var c=this._get(a,"isRTL"),d=this._get(a,"showButtonPanel"),e=this._get(a,"hideIfNoPrevNext"),f=this._get(a,"navigationAsDateFormat"),g=this._getNumberOfMonths(a),h=this._get(a,"showCurrentAtPos"),i=this._get(a,"stepMonths"),j=g[0]!=1||g[1]!=1,k=this._daylightSavingAdjust(a.currentDay?new Date(a.currentYear,a.currentMonth,a.currentDay):new Date(9999,9,9)),l=this._getMinMaxDate(a,"min"),m=this._getMinMaxDate(a,"max"),n=a.drawMonth-h,o=a.drawYear;n<0&&(n+=12,o--);if(m){var p=this._daylightSavingAdjust(new Date(m.getFullYear(),m.getMonth()-g[0]*g[1]+1,m.getDate()));p=l&&p<l?l:p;while(this._daylightSavingAdjust(new Date(o,n,1))>p)n--,n<0&&(n=11,o--)}a.drawMonth=n,a.drawYear=o;var q=this._get(a,"prevText");q=f?this.formatDate(q,this._daylightSavingAdjust(new Date(o,n-i,1)),this._getFormatConfig(a)):q;var r=this._canAdjustMonth(a,-1,o,n)?'<a class="ui-datepicker-prev ui-corner-all" onclick="DP_jQuery_'+dpuuid+".datepicker._adjustDate('#"+a.id+"', -"+i+", 'M');\""+' title="'+q+'"><span class="ui-icon ui-icon-circle-triangle-'+(c?"e":"w")+'">'+q+"</span></a>":e?"":'<a class="ui-datepicker-prev ui-corner-all ui-state-disabled" title="'+q+'"><span class="ui-icon ui-icon-circle-triangle-'+(c?"e":"w")+'">'+q+"</span></a>",s=this._get(a,"nextText");s=f?this.formatDate(s,this._daylightSavingAdjust(new Date(o,n+i,1)),this._getFormatConfig(a)):s;var t=this._canAdjustMonth(a,1,o,n)?'<a class="ui-datepicker-next ui-corner-all" onclick="DP_jQuery_'+dpuuid+".datepicker._adjustDate('#"+a.id+"', +"+i+", 'M');\""+' title="'+s+'"><span class="ui-icon ui-icon-circle-triangle-'+(c?"w":"e")+'">'+s+"</span></a>":e?"":'<a class="ui-datepicker-next ui-corner-all ui-state-disabled" title="'+s+'"><span class="ui-icon ui-icon-circle-triangle-'+(c?"w":"e")+'">'+s+"</span></a>",u=this._get(a,"currentText"),v=this._get(a,"gotoCurrent")&&a.currentDay?k:b;u=f?this.formatDate(u,v,this._getFormatConfig(a)):u;var w=a.inline?"":'<button type="button" class="ui-datepicker-close ui-state-default ui-priority-primary ui-corner-all" onclick="DP_jQuery_'+dpuuid+'.datepicker._hideDatepicker();">'+this._get(a,"closeText")+"</button>",x=d?'<div class="ui-datepicker-buttonpane ui-widget-content">'+(c?w:"")+(this._isInRange(a,v)?'<button type="button" class="ui-datepicker-current ui-state-default ui-priority-secondary ui-corner-all" onclick="DP_jQuery_'+dpuuid+".datepicker._gotoToday('#"+a.id+"');\""+">"+u+"</button>":"")+(c?"":w)+"</div>":"",y=parseInt(this._get(a,"firstDay"),10);y=isNaN(y)?0:y;var z=this._get(a,"showWeek"),A=this._get(a,"dayNames"),B=this._get(a,"dayNamesShort"),C=this._get(a,"dayNamesMin"),D=this._get(a,"monthNames"),E=this._get(a,"monthNamesShort"),F=this._get(a,"beforeShowDay"),G=this._get(a,"showOtherMonths"),H=this._get(a,"selectOtherMonths"),I=this._get(a,"calculateWeek")||this.iso8601Week,J=this._getDefaultDate(a),K="";for(var L=0;L<g[0];L++){var M="";this.maxRows=4;for(var N=0;N<g[1];N++){var O=this._daylightSavingAdjust(new Date(o,n,a.selectedDay)),P=" ui-corner-all",Q="";if(j){Q+='<div class="ui-datepicker-group';if(g[1]>1)switch(N){case 0:Q+=" ui-datepicker-group-first",P=" ui-corner-"+(c?"right":"left");break;case g[1]-1:Q+=" ui-datepicker-group-last",P=" ui-corner-"+(c?"left":"right");break;default:Q+=" ui-datepicker-group-middle",P=""}Q+='">'}Q+='<div class="ui-datepicker-header ui-widget-header ui-helper-clearfix'+P+'">'+(/all|left/.test(P)&&L==0?c?t:r:"")+(/all|right/.test(P)&&L==0?c?r:t:"")+this._generateMonthYearHeader(a,n,o,l,m,L>0||N>0,D,E)+'</div><table class="ui-datepicker-calendar"><thead>'+"<tr>";var R=z?'<th class="ui-datepicker-week-col">'+this._get(a,"weekHeader")+"</th>":"";for(var S=0;S<7;S++){var T=(S+y)%7;R+="<th"+((S+y+6)%7>=5?' class="ui-datepicker-week-end"':"")+">"+'<span title="'+A[T]+'">'+C[T]+"</span></th>"}Q+=R+"</tr></thead><tbody>";var U=this._getDaysInMonth(o,n);o==a.selectedYear&&n==a.selectedMonth&&(a.selectedDay=Math.min(a.selectedDay,U));var V=(this._getFirstDayOfMonth(o,n)-y+7)%7,W=Math.ceil((V+U)/7),X=j?this.maxRows>W?this.maxRows:W:W;this.maxRows=X;var Y=this._daylightSavingAdjust(new Date(o,n,1-V));for(var Z=0;Z<X;Z++){Q+="<tr>";var _=z?'<td class="ui-datepicker-week-col">'+this._get(a,"calculateWeek")(Y)+"</td>":"";for(var S=0;S<7;S++){var ba=F?F.apply(a.input?a.input[0]:null,[Y]):[!0,""],bb=Y.getMonth()!=n,bc=bb&&!H||!ba[0]||l&&Y<l||m&&Y>m;_+='<td class="'+((S+y+6)%7>=5?" ui-datepicker-week-end":"")+(bb?" ui-datepicker-other-month":"")+(Y.getTime()==O.getTime()&&n==a.selectedMonth&&a._keyEvent||J.getTime()==Y.getTime()&&J.getTime()==O.getTime()?" "+this._dayOverClass:"")+(bc?" "+this._unselectableClass+" ui-state-disabled":"")+(bb&&!G?"":" "+ba[1]+(Y.getTime()==k.getTime()?" "+this._currentClass:"")+(Y.getTime()==b.getTime()?" ui-datepicker-today":""))+'"'+((!bb||G)&&ba[2]?' title="'+ba[2]+'"':"")+(bc?"":' onclick="DP_jQuery_'+dpuuid+".datepicker._selectDay('#"+a.id+"',"+Y.getMonth()+","+Y.getFullYear()+', this);return false;"')+">"+(bb&&!G?"&#xa0;":bc?'<span class="ui-state-default">'+Y.getDate()+"</span>":'<a class="ui-state-default'+(Y.getTime()==b.getTime()?" ui-state-highlight":"")+(Y.getTime()==k.getTime()?" ui-state-active":"")+(bb?" ui-priority-secondary":"")+'" href="#">'+Y.getDate()+"</a>")+"</td>",Y.setDate(Y.getDate()+1),Y=this._daylightSavingAdjust(Y)}Q+=_+"</tr>"}n++,n>11&&(n=0,o++),Q+="</tbody></table>"+(j?"</div>"+(g[0]>0&&N==g[1]-1?'<div class="ui-datepicker-row-break"></div>':""):""),M+=Q}K+=M}K+=x+($.browser.msie&&parseInt($.browser.version,10)<7&&!a.inline?'<iframe src="javascript:false;" class="ui-datepicker-cover" frameborder="0"></iframe>':""),
a._keyEvent=!1;return K},_generateMonthYearHeader:function(a,b,c,d,e,f,g,h){var i=this._get(a,"changeMonth"),j=this._get(a,"changeYear"),k=this._get(a,"showMonthAfterYear"),l='<div class="ui-datepicker-title">',m="";if(f||!i)m+='<span class="ui-datepicker-month">'+g[b]+"</span>";else{var n=d&&d.getFullYear()==c,o=e&&e.getFullYear()==c;m+='<select class="ui-datepicker-month" onchange="DP_jQuery_'+dpuuid+".datepicker._selectMonthYear('#"+a.id+"', this, 'M');\" "+">";for(var p=0;p<12;p++)(!n||p>=d.getMonth())&&(!o||p<=e.getMonth())&&(m+='<option value="'+p+'"'+(p==b?' selected="selected"':"")+">"+h[p]+"</option>");m+="</select>"}k||(l+=m+(f||!i||!j?"&#xa0;":""));if(!a.yearshtml){a.yearshtml="";if(f||!j)l+='<span class="ui-datepicker-year">'+c+"</span>";else{var q=this._get(a,"yearRange").split(":"),r=(new Date).getFullYear(),s=function(a){var b=a.match(/c[+-].*/)?c+parseInt(a.substring(1),10):a.match(/[+-].*/)?r+parseInt(a,10):parseInt(a,10);return isNaN(b)?r:b},t=s(q[0]),u=Math.max(t,s(q[1]||""));t=d?Math.max(t,d.getFullYear()):t,u=e?Math.min(u,e.getFullYear()):u,a.yearshtml+='<select class="ui-datepicker-year" onchange="DP_jQuery_'+dpuuid+".datepicker._selectMonthYear('#"+a.id+"', this, 'Y');\" "+">";for(;t<=u;t++)a.yearshtml+='<option value="'+t+'"'+(t==c?' selected="selected"':"")+">"+t+"</option>";a.yearshtml+="</select>",l+=a.yearshtml,a.yearshtml=null}}l+=this._get(a,"yearSuffix"),k&&(l+=(f||!i||!j?"&#xa0;":"")+m),l+="</div>";return l},_adjustInstDate:function(a,b,c){var d=a.drawYear+(c=="Y"?b:0),e=a.drawMonth+(c=="M"?b:0),f=Math.min(a.selectedDay,this._getDaysInMonth(d,e))+(c=="D"?b:0),g=this._restrictMinMax(a,this._daylightSavingAdjust(new Date(d,e,f)));a.selectedDay=g.getDate(),a.drawMonth=a.selectedMonth=g.getMonth(),a.drawYear=a.selectedYear=g.getFullYear(),(c=="M"||c=="Y")&&this._notifyChange(a)},_restrictMinMax:function(a,b){var c=this._getMinMaxDate(a,"min"),d=this._getMinMaxDate(a,"max"),e=c&&b<c?c:b;e=d&&e>d?d:e;return e},_notifyChange:function(a){var b=this._get(a,"onChangeMonthYear");b&&b.apply(a.input?a.input[0]:null,[a.selectedYear,a.selectedMonth+1,a])},_getNumberOfMonths:function(a){var b=this._get(a,"numberOfMonths");return b==null?[1,1]:typeof b=="number"?[1,b]:b},_getMinMaxDate:function(a,b){return this._determineDate(a,this._get(a,b+"Date"),null)},_getDaysInMonth:function(a,b){return 32-this._daylightSavingAdjust(new Date(a,b,32)).getDate()},_getFirstDayOfMonth:function(a,b){return(new Date(a,b,1)).getDay()},_canAdjustMonth:function(a,b,c,d){var e=this._getNumberOfMonths(a),f=this._daylightSavingAdjust(new Date(c,d+(b<0?b:e[0]*e[1]),1));b<0&&f.setDate(this._getDaysInMonth(f.getFullYear(),f.getMonth()));return this._isInRange(a,f)},_isInRange:function(a,b){var c=this._getMinMaxDate(a,"min"),d=this._getMinMaxDate(a,"max");return(!c||b.getTime()>=c.getTime())&&(!d||b.getTime()<=d.getTime())},_getFormatConfig:function(a){var b=this._get(a,"shortYearCutoff");b=typeof b!="string"?b:(new Date).getFullYear()%100+parseInt(b,10);return{shortYearCutoff:b,dayNamesShort:this._get(a,"dayNamesShort"),dayNames:this._get(a,"dayNames"),monthNamesShort:this._get(a,"monthNamesShort"),monthNames:this._get(a,"monthNames")}},_formatDate:function(a,b,c,d){b||(a.currentDay=a.selectedDay,a.currentMonth=a.selectedMonth,a.currentYear=a.selectedYear);var e=b?typeof b=="object"?b:this._daylightSavingAdjust(new Date(d,c,b)):this._daylightSavingAdjust(new Date(a.currentYear,a.currentMonth,a.currentDay));return this.formatDate(this._get(a,"dateFormat"),e,this._getFormatConfig(a))}}),$.fn.datepicker=function(a){if(!this.length)return this;$.datepicker.initialized||($(document).mousedown($.datepicker._checkExternalClick).find("body").append($.datepicker.dpDiv),$.datepicker.initialized=!0);var b=Array.prototype.slice.call(arguments,1);if(typeof a=="string"&&(a=="isDisabled"||a=="getDate"||a=="widget"))return $.datepicker["_"+a+"Datepicker"].apply($.datepicker,[this[0]].concat(b));if(a=="option"&&arguments.length==2&&typeof arguments[1]=="string")return $.datepicker["_"+a+"Datepicker"].apply($.datepicker,[this[0]].concat(b));return this.each(function(){typeof a=="string"?$.datepicker["_"+a+"Datepicker"].apply($.datepicker,[this].concat(b)):$.datepicker._attachDatepicker(this,a)})},$.datepicker=new Datepicker,$.datepicker.initialized=!1,$.datepicker.uuid=(new Date).getTime(),$.datepicker.version="1.8.18",window["DP_jQuery_"+dpuuid]=$})(jQuery);

/*
 *	lib/js/lib/jquery/jquery.ui.autocomplete.js
 */
/* jQuery UI Autocomplete 1.8.18
*
* Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)
* Dual licensed under the MIT or GPL Version 2 licenses.
* http://jquery.org/license
*
* http://docs.jquery.com/UI/Autocomplete
*
* Depends:
*	jquery.ui.core.js
*	jquery.ui.widget.js
*	jquery.ui.position.js
*/(function(a,b){var c=0;a.widget("ui.autocomplete",{options:{appendTo:"body",autoFocus:!1,delay:300,minLength:1,position:{my:"left top",at:"left bottom",collision:"none"},source:null},pending:0,_create:function(){var b=this,c=this.element[0].ownerDocument,d;this.element.addClass("ui-autocomplete-input").attr("autocomplete","off").attr({role:"textbox","aria-autocomplete":"list","aria-haspopup":"true"}).bind("keydown.autocomplete",function(c){if(!b.options.disabled&&!b.element.propAttr("readOnly")){d=!1;var e=a.ui.keyCode;switch(c.keyCode){case e.PAGE_UP:b._move("previousPage",c);break;case e.PAGE_DOWN:b._move("nextPage",c);break;case e.UP:b._move("previous",c),c.preventDefault();break;case e.DOWN:b._move("next",c),c.preventDefault();break;case e.ENTER:case e.NUMPAD_ENTER:b.menu.active&&(d=!0,c.preventDefault());case e.TAB:if(!b.menu.active)return;b.menu.select(c);break;case e.ESCAPE:b.element.val(b.term),b.close(c);break;default:clearTimeout(b.searching),b.searching=setTimeout(function(){b.term!=b.element.val()&&(b.selectedItem=null,b.search(null,c))},b.options.delay)}}}).bind("keypress.autocomplete",function(a){d&&(d=!1,a.preventDefault())}).bind("focus.autocomplete",function(){b.options.disabled||(b.selectedItem=null,b.previous=b.element.val())}).bind("blur.autocomplete",function(a){b.options.disabled||(clearTimeout(b.searching),b.closing=setTimeout(function(){b.close(a),b._change(a)},150))}),this._initSource(),this.response=function(){return b._response.apply(b,arguments)},this.menu=a("<ul></ul>").addClass("ui-autocomplete").appendTo(a(this.options.appendTo||"body",c)[0]).mousedown(function(c){var d=b.menu.element[0];a(c.target).closest(".ui-menu-item").length||setTimeout(function(){a(document).one("mousedown",function(c){c.target!==b.element[0]&&c.target!==d&&!a.ui.contains(d,c.target)&&b.close()})},1),setTimeout(function(){clearTimeout(b.closing)},13)}).menu({focus:function(a,c){var d=c.item.data("item.autocomplete");!1!==b._trigger("focus",a,{item:d})&&/^key/.test(a.originalEvent.type)&&b.element.val(d.value)},selected:function(a,d){var e=d.item.data("item.autocomplete"),f=b.previous;b.element[0]!==c.activeElement&&(b.element.focus(),b.previous=f,setTimeout(function(){b.previous=f,b.selectedItem=e},1)),!1!==b._trigger("select",a,{item:e})&&b.element.val(e.value),b.term=b.element.val(),b.close(a),b.selectedItem=e},blur:function(a,c){b.menu.element.is(":visible")&&b.element.val()!==b.term&&b.element.val(b.term)}}).zIndex(this.element.zIndex()+1).css({top:0,left:0}).hide().data("menu"),a.fn.bgiframe&&this.menu.element.bgiframe(),b.beforeunloadHandler=function(){b.element.removeAttr("autocomplete")},a(window).bind("beforeunload",b.beforeunloadHandler)},destroy:function(){this.element.removeClass("ui-autocomplete-input").removeAttr("autocomplete").removeAttr("role").removeAttr("aria-autocomplete").removeAttr("aria-haspopup"),this.menu.element.remove(),a(window).unbind("beforeunload",this.beforeunloadHandler),a.Widget.prototype.destroy.call(this)},_setOption:function(b,c){a.Widget.prototype._setOption.apply(this,arguments),b==="source"&&this._initSource(),b==="appendTo"&&this.menu.element.appendTo(a(c||"body",this.element[0].ownerDocument)[0]),b==="disabled"&&c&&this.xhr&&this.xhr.abort()},_initSource:function(){var b=this,d,e;a.isArray(this.options.source)?(d=this.options.source,this.source=function(b,c){c(a.ui.autocomplete.filter(d,b.term))}):typeof this.options.source=="string"?(e=this.options.source,this.source=function(d,f){b.xhr&&b.xhr.abort(),b.xhr=a.ajax({url:e,data:d,dataType:"json",context:{autocompleteRequest:++c},success:function(a,b){this.autocompleteRequest===c&&f(a)},error:function(){this.autocompleteRequest===c&&f([])}})}):this.source=this.options.source},search:function(a,b){a=a!=null?a:this.element.val(),this.term=this.element.val();if(a.length<this.options.minLength)return this.close(b);clearTimeout(this.closing);if(this._trigger("search",b)!==!1)return this._search(a)},_search:function(a){this.pending++,this.element.addClass("ui-autocomplete-loading"),this.source({term:a},this.response)},_response:function(a){!this.options.disabled&&a&&a.length?(a=this._normalize(a),this._suggest(a),this._trigger("open")):this.close(),this.pending--,this.pending||this.element.removeClass("ui-autocomplete-loading")},close:function(a){clearTimeout(this.closing),this.menu.element.is(":visible")&&(this.menu.element.hide(),this.menu.deactivate(),this._trigger("close",a))},_change:function(a){this.previous!==this.element.val()&&this._trigger("change",a,{item:this.selectedItem})},_normalize:function(b){if(b.length&&b[0].label&&b[0].value)return b;return a.map(b,function(b){if(typeof b=="string")return{label:b,value:b};return a.extend({label:b.label||b.value,value:b.value||b.label},b)})},_suggest:function(b){var c=this.menu.element.empty().zIndex(this.element.zIndex()+1);this._renderMenu(c,b),this.menu.deactivate(),this.menu.refresh(),c.show(),this._resizeMenu(),c.position(a.extend({of:this.element},this.options.position)),this.options.autoFocus&&this.menu.next(new a.Event("mouseover"))},_resizeMenu:function(){var a=this.menu.element;a.outerWidth(Math.max(a.width("").outerWidth()+1,this.element.outerWidth()))},_renderMenu:function(b,c){var d=this;a.each(c,function(a,c){d._renderItem(b,c)})},_renderItem:function(b,c){return a("<li></li>").data("item.autocomplete",c).append(a("<a></a>").text(c.label)).appendTo(b)},_move:function(a,b){if(!this.menu.element.is(":visible"))this.search(null,b);else{if(this.menu.first()&&/^previous/.test(a)||this.menu.last()&&/^next/.test(a)){this.element.val(this.term),this.menu.deactivate();return}this.menu[a](b)}},widget:function(){return this.menu.element}}),a.extend(a.ui.autocomplete,{escapeRegex:function(a){return a.replace(/[-[\]{}()*+?.,\\^$|#\s]/g,"\\$&")},filter:function(b,c){var d=new RegExp(a.ui.autocomplete.escapeRegex(c),"i");return a.grep(b,function(a){return d.test(a.label||a.value||a)})}})})(jQuery),function(a){a.widget("ui.menu",{_create:function(){var b=this;this.element.addClass("ui-menu ui-widget ui-widget-content ui-corner-all").attr({role:"listbox","aria-activedescendant":"ui-active-menuitem"}).click(function(c){!a(c.target).closest(".ui-menu-item a").length||(c.preventDefault(),b.select(c))}),this.refresh()},refresh:function(){var b=this,c=this.element.children("li:not(.ui-menu-item):has(a)").addClass("ui-menu-item").attr("role","menuitem");c.children("a").addClass("ui-corner-all").attr("tabindex",-1).mouseenter(function(c){b.activate(c,a(this).parent())}).mouseleave(function(){b.deactivate()})},activate:function(a,b){this.deactivate();if(this.hasScroll()){var c=b.offset().top-this.element.offset().top,d=this.element.scrollTop(),e=this.element.height();c<0?this.element.scrollTop(d+c):c>=e&&this.element.scrollTop(d+c-e+b.height())}this.active=b.eq(0).children("a").addClass("ui-state-hover").attr("id","ui-active-menuitem").end(),this._trigger("focus",a,{item:b})},deactivate:function(){!this.active||(this.active.children("a").removeClass("ui-state-hover").removeAttr("id"),this._trigger("blur"),this.active=null)},next:function(a){this.move("next",".ui-menu-item:first",a)},previous:function(a){this.move("prev",".ui-menu-item:last",a)},first:function(){return this.active&&!this.active.prevAll(".ui-menu-item").length},last:function(){return this.active&&!this.active.nextAll(".ui-menu-item").length},move:function(a,b,c){if(!this.active)this.activate(c,this.element.children(b));else{var d=this.active[a+"All"](".ui-menu-item").eq(0);d.length?this.activate(c,d):this.activate(c,this.element.children(b))}},nextPage:function(b){if(this.hasScroll()){if(!this.active||this.last()){this.activate(b,this.element.children(".ui-menu-item:first"));return}var c=this.active.offset().top,d=this.element.height(),e=this.element.children(".ui-menu-item").filter(function(){var b=a(this).offset().top-c-d+a(this).height();return b<10&&b>-10});e.length||(e=this.element.children(".ui-menu-item:last")),this.activate(b,e)}else this.activate(b,this.element.children(".ui-menu-item").filter(!this.active||this.last()?":first":":last"))},previousPage:function(b){if(this.hasScroll()){if(!this.active||this.first()){this.activate(b,this.element.children(".ui-menu-item:last"));return}var c=this.active.offset().top,d=this.element.height();result=this.element.children(".ui-menu-item").filter(function(){var b=a(this).offset().top-c+d-a(this).height();return b<10&&b>-10}),result.length||(result=this.element.children(".ui-menu-item:first")),this.activate(b,result)}else this.activate(b,this.element.children(".ui-menu-item").filter(!this.active||this.first()?":last":":first"))},hasScroll:function(){return this.element.height()<this.element[a.fn.prop?"prop":"attr"]("scrollHeight")},select:function(a){this._trigger("selected",a,{item:this.active})}})}(jQuery);

/*
 *	lib/js/lib/tiny_mce_33/jquery.tinymce.js
 */
(function(b){var e,d,a=[],c=window;b.fn.tinymce=function(j){var p=this,g,k,h,m,i,l="",n="";if(!p.length){return p}if(!j){return tinyMCE.get(p[0].id)}function o(){var r=[],q=0;if(f){f();f=null}p.each(function(t,u){var s,w=u.id,v=j.oninit;if(!w){u.id=w=tinymce.DOM.uniqueId()}s=new tinymce.Editor(w,j);r.push(s);if(v){s.onInit.add(function(){var x,y=v;if(++q==r.length){if(tinymce.is(y,"string")){x=(y.indexOf(".")===-1)?null:tinymce.resolve(y.replace(/\.\w+$/,""));y=tinymce.resolve(y)}y.apply(x||tinymce,r)}})}});b.each(r,function(t,s){s.render()})}if(!c.tinymce&&!d&&(g=j.script_url)){d=1;h=g.substring(0,g.lastIndexOf("/"));if(/_(src|dev)\.js/g.test(g)){n="_src"}m=g.lastIndexOf("?");if(m!=-1){l=g.substring(m+1)}c.tinyMCEPreInit=c.tinyMCEPreInit||{base:h,suffix:n,query:l};if(g.indexOf("gzip")!=-1){i=j.language||"en";g=g+(/\?/.test(g)?"&":"?")+"js=true&core=true&suffix="+escape(n)+"&themes="+escape(j.theme)+"&plugins="+escape(j.plugins)+"&languages="+i;if(!c.tinyMCE_GZ){tinyMCE_GZ={start:function(){tinymce.suffix=n;function q(r){tinymce.ScriptLoader.markDone(tinyMCE.baseURI.toAbsolute(r))}q("langs/"+i+".js");q("themes/"+j.theme+"/editor_template"+n+".js");q("themes/"+j.theme+"/langs/"+i+".js");b.each(j.plugins.split(","),function(s,r){if(r){q("plugins/"+r+"/editor_plugin"+n+".js");q("plugins/"+r+"/langs/"+i+".js")}})},end:function(){}}}}b.ajax({type:"GET",url:g,dataType:"script",cache:true,success:function(){tinymce.dom.Event.domLoaded=1;d=2;if(j.script_loaded){j.script_loaded()}o();b.each(a,function(q,r){r()})}})}else{if(d===1){a.push(o)}else{o()}}return p};b.extend(b.expr[":"],{tinymce:function(g){return g.id&&!!tinyMCE.get(g.id)}});function f(){function i(l){if(l==="remove"){this.each(function(n,o){var m=h(o);if(m){m.remove()}})}this.find("span.mceEditor,div.mceEditor").each(function(n,o){var m=tinyMCE.get(o.id.replace(/_parent$/,""));if(m){m.remove()}})}function k(n){var m=this,l;if(n!==e){i.call(m);m.each(function(p,q){var o;if(o=tinyMCE.get(q.id)){o.setContent(n)}})}else{if(m.length>0){if(l=tinyMCE.get(m[0].id)){return l.getContent()}}}}function h(m){var l=null;(m)&&(m.id)&&(c.tinymce)&&(l=tinyMCE.get(m.id));return l}function g(l){return !!((l)&&(l.length)&&(c.tinymce)&&(l.is(":tinymce")))}var j={};b.each(["text","html","val"],function(n,l){var o=j[l]=b.fn[l],m=(l==="text");b.fn[l]=function(s){var p=this;if(!g(p)){return o.apply(p,arguments)}if(s!==e){k.call(p.filter(":tinymce"),s);o.apply(p.not(":tinymce"),arguments);return p}else{var r="";var q=arguments;(m?p:p.eq(0)).each(function(u,v){var t=h(v);r+=t?(m?t.getContent().replace(/<(?:"[^"]*"|'[^']*'|[^'">])*>/g,""):t.getContent()):o.apply(b(v),q)});return r}}});b.each(["append","prepend"],function(n,m){var o=j[m]=b.fn[m],l=(m==="prepend");b.fn[m]=function(q){var p=this;if(!g(p)){return o.apply(p,arguments)}if(q!==e){p.filter(":tinymce").each(function(s,t){var r=h(t);r&&r.setContent(l?q+r.getContent():r.getContent()+q)});o.apply(p.not(":tinymce"),arguments);return p}}});b.each(["remove","replaceWith","replaceAll","empty"],function(m,l){var n=j[l]=b.fn[l];b.fn[l]=function(){i.call(this,l);return n.apply(this,arguments)}});j.attr=b.fn.attr;b.fn.attr=function(n,q,o){var m=this;if((!n)||(n!=="value")||(!g(m))){return j.attr.call(m,n,q,o)}if(q!==e){k.call(m.filter(":tinymce"),q);j.attr.call(m.not(":tinymce"),n,q,o);return m}else{var p=m[0],l=h(p);return l?l.getContent():j.attr.call(b(p),n,q,o)}}}})(jQuery);

/*
 *	lib/js/lib/bootstrap.min.js
 */
!function(a){a(function(){"use strict",a.support.transition=function(){var b=document.body||document.documentElement,c=b.style,d=c.transition!==undefined||c.WebkitTransition!==undefined||c.MozTransition!==undefined||c.MsTransition!==undefined||c.OTransition!==undefined;return d&&{end:function(){var b="TransitionEnd";return a.browser.webkit?b="webkitTransitionEnd":a.browser.mozilla?b="transitionend":a.browser.opera&&(b="oTransitionEnd"),b}()}}()})}(window.jQuery),!function(a){"use strict";var b='[data-dismiss="alert"]',c=function(c){a(c).on("click",b,this.close)};c.prototype={constructor:c,close:function(b){function f(){e.remove(),e.trigger("closed")}var c=a(this),d=c.attr("data-target"),e;d||(d=c.attr("href"),d=d&&d.replace(/.*(?=#[^\s]*$)/,"")),e=a(d),e.trigger("close"),b&&b.preventDefault(),e.length||(e=c.hasClass("alert")?c:c.parent()),e.removeClass("in"),a.support.transition&&e.hasClass("fade")?e.on(a.support.transition.end,f):f()}},a.fn.alert=function(b){return this.each(function(){var d=a(this),e=d.data("alert");e||d.data("alert",e=new c(this)),typeof b=="string"&&e[b].call(d)})},a.fn.alert.Constructor=c,a(function(){a("body").on("click.alert.data-api",b,c.prototype.close)})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.button.defaults,c)};b.prototype={constructor:b,setState:function(a){var b="disabled",c=this.$element,d=c.data(),e=c.is("input")?"val":"html";a+="Text",d.resetText||c.data("resetText",c[e]()),c[e](d[a]||this.options[a]),setTimeout(function(){a=="loadingText"?c.addClass(b).attr(b,b):c.removeClass(b).removeAttr(b)},0)},toggle:function(){var a=this.$element.parent('[data-toggle="buttons-radio"]');a&&a.find(".active").removeClass("active"),this.$element.toggleClass("active")}},a.fn.button=function(c){return this.each(function(){var d=a(this),e=d.data("button"),f=typeof c=="object"&&c;e||d.data("button",e=new b(this,f)),c=="toggle"?e.toggle():c&&e.setState(c)})},a.fn.button.defaults={loadingText:"loading..."},a.fn.button.Constructor=b,a(function(){a("body").on("click.button.data-api","[data-toggle^=button]",function(b){a(b.target).button("toggle")})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.carousel.defaults,c),this.options.slide&&this.slide(this.options.slide)};b.prototype={cycle:function(){return this.interval=setInterval(a.proxy(this.next,this),this.options.interval),this},to:function(b){var c=this.$element.find(".active"),d=c.parent().children(),e=d.index(c),f=this;if(b>d.length-1||b<0)return;return this.sliding?this.$element.one("slid",function(){f.to(b)}):e==b?this.pause().cycle():this.slide(b>e?"next":"prev",a(d[b]))},pause:function(){return clearInterval(this.interval),this},next:function(){if(this.sliding)return;return this.slide("next")},prev:function(){if(this.sliding)return;return this.slide("prev")},slide:function(b,c){var d=this.$element.find(".active"),e=c||d[b](),f=this.interval,g=b=="next"?"left":"right",h=b=="next"?"first":"last",i=this;return this.sliding=!0,f&&this.pause(),e=e.length?e:this.$element.find(".item")[h](),!a.support.transition&&this.$element.hasClass("slide")?(this.$element.trigger("slide"),d.removeClass("active"),e.addClass("active"),this.sliding=!1,this.$element.trigger("slid")):(e.addClass(b),e[0].offsetWidth,d.addClass(g),e.addClass(g),this.$element.trigger("slide"),this.$element.one(a.support.transition.end,function(){e.removeClass([b,g].join(" ")).addClass("active"),d.removeClass(["active",g].join(" ")),i.sliding=!1,setTimeout(function(){i.$element.trigger("slid")},0)})),f&&this.cycle(),this}},a.fn.carousel=function(c){return this.each(function(){var d=a(this),e=d.data("carousel"),f=typeof c=="object"&&c;e||d.data("carousel",e=new b(this,f)),typeof c=="number"?e.to(c):typeof c=="string"||(c=f.slide)?e[c]():e.cycle()})},a.fn.carousel.defaults={interval:5e3},a.fn.carousel.Constructor=b,a(function(){a("body").on("click.carousel.data-api","[data-slide]",function(b){var c=a(this),d,e=a(c.attr("data-target")||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,"")),f=!e.data("modal")&&a.extend({},e.data(),c.data());e.carousel(f),b.preventDefault()})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.collapse.defaults,c),this.options.parent&&(this.$parent=a(this.options.parent)),this.options.toggle&&this.toggle()};b.prototype={constructor:b,dimension:function(){var a=this.$element.hasClass("width");return a?"width":"height"},show:function(){var b=this.dimension(),c=a.camelCase(["scroll",b].join("-")),d=this.$parent&&this.$parent.find(".in"),e;d&&d.length&&(e=d.data("collapse"),d.collapse("hide"),e||d.data("collapse",null)),this.$element[b](0),this.transition("addClass","show","shown"),this.$element[b](this.$element[0][c])},hide:function(){var a=this.dimension();this.reset(this.$element[a]()),this.transition("removeClass","hide","hidden"),this.$element[a](0)},reset:function(a){var b=this.dimension();this.$element.removeClass("collapse")[b](a||"auto")[0].offsetWidth,this.$element.addClass("collapse")},transition:function(b,c,d){var e=this,f=function(){c=="show"&&e.reset(),e.$element.trigger(d)};this.$element.trigger(c)[b]("in"),a.support.transition&&this.$element.hasClass("collapse")?this.$element.one(a.support.transition.end,f):f()},toggle:function(){this[this.$element.hasClass("in")?"hide":"show"]()}},a.fn.collapse=function(c){return this.each(function(){var d=a(this),e=d.data("collapse"),f=typeof c=="object"&&c;e||d.data("collapse",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.collapse.defaults={toggle:!0},a.fn.collapse.Constructor=b,a(function(){a("body").on("click.collapse.data-api","[data-toggle=collapse]",function(b){var c=a(this),d,e=c.attr("data-target")||b.preventDefault()||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,""),f=a(e).data("collapse")?"toggle":c.data();a(e).collapse(f)})})}(window.jQuery),!function(a){function d(){a(b).parent().removeClass("open")}"use strict";var b='[data-toggle="dropdown"]',c=function(b){var c=a(b).on("click.dropdown.data-api",this.toggle);a("html").on("click.dropdown.data-api",function(){c.parent().removeClass("open")})};c.prototype={constructor:c,toggle:function(b){var c=a(this),e=c.attr("data-target"),f,g;return e||(e=c.attr("href"),e=e&&e.replace(/.*(?=#[^\s]*$)/,"")),f=a(e),f.length||(f=c.parent()),g=f.hasClass("open"),d(),!g&&f.toggleClass("open"),!1}},a.fn.dropdown=function(b){return this.each(function(){var d=a(this),e=d.data("dropdown");e||d.data("dropdown",e=new c(this)),typeof b=="string"&&e[b].call(d)})},a.fn.dropdown.Constructor=c,a(function(){a("html").on("click.dropdown.data-api",d),a("body").on("click.dropdown.data-api",b,c.prototype.toggle)})}(window.jQuery),!function(a){function c(){var b=this,c=setTimeout(function(){b.$element.off(a.support.transition.end),d.call(b)},500);this.$element.one(a.support.transition.end,function(){clearTimeout(c),d.call(b)})}function d(a){this.$element.hide().trigger("hidden"),e.call(this)}function e(b){var c=this,d=this.$element.hasClass("fade")?"fade":"";if(this.isShown&&this.options.backdrop){var e=a.support.transition&&d;this.$backdrop=a('<div class="modal-backdrop '+d+'" />').appendTo(document.body),this.options.backdrop!="static"&&this.$backdrop.click(a.proxy(this.hide,this)),e&&this.$backdrop[0].offsetWidth,this.$backdrop.addClass("in"),e?this.$backdrop.one(a.support.transition.end,b):b()}else!this.isShown&&this.$backdrop?(this.$backdrop.removeClass("in"),a.support.transition&&this.$element.hasClass("fade")?this.$backdrop.one(a.support.transition.end,a.proxy(f,this)):f.call(this)):b&&b()}function f(){this.$backdrop.remove(),this.$backdrop=null}function g(){var b=this;this.isShown&&this.options.keyboard?a(document).on("keyup.dismiss.modal",function(a){a.which==27&&b.hide()}):this.isShown||a(document).off("keyup.dismiss.modal")}"use strict";var b=function(b,c){this.options=a.extend({},a.fn.modal.defaults,c),this.$element=a(b).delegate('[data-dismiss="modal"]',"click.dismiss.modal",a.proxy(this.hide,this))};b.prototype={constructor:b,toggle:function(){return this[this.isShown?"hide":"show"]()},show:function(){var b=this;if(this.isShown)return;a("body").addClass("modal-open"),this.isShown=!0,this.$element.trigger("show"),g.call(this),e.call(this,function(){var c=a.support.transition&&b.$element.hasClass("fade");!b.$element.parent().length&&b.$element.appendTo(document.body),b.$element.show(),c&&b.$element[0].offsetWidth,b.$element.addClass("in"),c?b.$element.one(a.support.transition.end,function(){b.$element.trigger("shown")}):b.$element.trigger("shown")})},hide:function(b){b&&b.preventDefault();if(!this.isShown)return;var e=this;this.isShown=!1,a("body").removeClass("modal-open"),g.call(this),this.$element.trigger("hide").removeClass("in"),a.support.transition&&this.$element.hasClass("fade")?c.call(this):d.call(this)}},a.fn.modal=function(c){return this.each(function(){var d=a(this),e=d.data("modal"),f=typeof c=="object"&&c;e||d.data("modal",e=new b(this,f)),typeof c=="string"?e[c]():e.show()})},a.fn.modal.defaults={backdrop:!0,keyboard:!0},a.fn.modal.Constructor=b,a(function(){a("body").on("click.modal.data-api",'[data-toggle="modal"]',function(b){var c=a(this),d,e=a(c.attr("data-target")||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,"")),f=e.data("modal")?"toggle":a.extend({},e.data(),c.data());b.preventDefault(),e.modal(f)})})}(window.jQuery),!function(a){"use strict";var b=function(a,b){this.init("tooltip",a,b)};b.prototype={constructor:b,init:function(b,c,d){var e,f;this.type=b,this.$element=a(c),this.options=this.getOptions(d),this.enabled=!0,this.options.trigger!="manual"&&(e=this.options.trigger=="hover"?"mouseenter":"focus",f=this.options.trigger=="hover"?"mouseleave":"blur",this.$element.on(e,this.options.selector,a.proxy(this.enter,this)),this.$element.on(f,this.options.selector,a.proxy(this.leave,this))),this.options.selector?this._options=a.extend({},this.options,{trigger:"manual",selector:""}):this.fixTitle()},getOptions:function(b){return b=a.extend({},a.fn[this.type].defaults,b,this.$element.data()),b.delay&&typeof b.delay=="number"&&(b.delay={show:b.delay,hide:b.delay}),b},enter:function(b){var c=a(b.currentTarget)[this.type](this._options).data(this.type);!c.options.delay||!c.options.delay.show?c.show():(c.hoverState="in",setTimeout(function(){c.hoverState=="in"&&c.show()},c.options.delay.show))},leave:function(b){var c=a(b.currentTarget)[this.type](this._options).data(this.type);!c.options.delay||!c.options.delay.hide?c.hide():(c.hoverState="out",setTimeout(function(){c.hoverState=="out"&&c.hide()},c.options.delay.hide))},show:function(){var a,b,c,d,e,f,g;if(this.hasContent()&&this.enabled){a=this.tip(),this.setContent(),this.options.animation&&a.addClass("fade"),f=typeof this.options.placement=="function"?this.options.placement.call(this,a[0],this.$element[0]):this.options.placement,b=/in/.test(f),a.remove().css({top:0,left:0,display:"block"}).appendTo(b?this.$element:document.body),c=this.getPosition(b),d=a[0].offsetWidth,e=a[0].offsetHeight;switch(b?f.split(" ")[1]:f){case"bottom":g={top:c.top+c.height,left:c.left+c.width/2-d/2};break;case"top":g={top:c.top-e,left:c.left+c.width/2-d/2};break;case"left":g={top:c.top+c.height/2-e/2,left:c.left-d};break;case"right":g={top:c.top+c.height/2-e/2,left:c.left+c.width}}a.css(g).addClass(f).addClass("in")}},setContent:function(){var a=this.tip();a.find(".tooltip-inner").html(this.getTitle()),a.removeClass("fade in top bottom left right")},hide:function(){function d(){var b=setTimeout(function(){c.off(a.support.transition.end).remove()},500);c.one(a.support.transition.end,function(){clearTimeout(b),c.remove()})}var b=this,c=this.tip();c.removeClass("in"),a.support.transition&&this.$tip.hasClass("fade")?d():c.remove()},fixTitle:function(){var a=this.$element;(a.attr("title")||typeof a.attr("data-original-title")!="string")&&a.attr("data-original-title",a.attr("title")||"").removeAttr("title")},hasContent:function(){return this.getTitle()},getPosition:function(b){return a.extend({},b?{top:0,left:0}:this.$element.offset(),{width:this.$element[0].offsetWidth,height:this.$element[0].offsetHeight})},getTitle:function(){var a,b=this.$element,c=this.options;return a=b.attr("data-original-title")||(typeof c.title=="function"?c.title.call(b[0]):c.title),a=a.toString().replace(/(^\s*|\s*$)/,""),a},tip:function(){return this.$tip=this.$tip||a(this.options.template)},validate:function(){this.$element[0].parentNode||(this.hide(),this.$element=null,this.options=null)},enable:function(){this.enabled=!0},disable:function(){this.enabled=!1},toggleEnabled:function(){this.enabled=!this.enabled},toggle:function(){this[this.tip().hasClass("in")?"hide":"show"]()}},a.fn.tooltip=function(c){return this.each(function(){var d=a(this),e=d.data("tooltip"),f=typeof c=="object"&&c;e||d.data("tooltip",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.tooltip.Constructor=b,a.fn.tooltip.defaults={animation:!0,delay:0,selector:!1,placement:"top",trigger:"hover",title:"",template:'<div class="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'}}(window.jQuery),!function(a){"use strict";var b=function(a,b){this.init("popover",a,b)};b.prototype=a.extend({},a.fn.tooltip.Constructor.prototype,{constructor:b,setContent:function(){var b=this.tip(),c=this.getTitle(),d=this.getContent();b.find(".popover-title")[a.type(c)=="object"?"append":"html"](c),b.find(".popover-content > *")[a.type(d)=="object"?"append":"html"](d),b.removeClass("fade top bottom left right in")},hasContent:function(){return this.getTitle()||this.getContent()},getContent:function(){var a,b=this.$element,c=this.options;return a=b.attr("data-content")||(typeof c.content=="function"?c.content.call(b[0]):c.content),a=a.toString().replace(/(^\s*|\s*$)/,""),a},tip:function(){return this.$tip||(this.$tip=a(this.options.template)),this.$tip}}),a.fn.popover=function(c){return this.each(function(){var d=a(this),e=d.data("popover"),f=typeof c=="object"&&c;e||d.data("popover",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.popover.Constructor=b,a.fn.popover.defaults=a.extend({},a.fn.tooltip.defaults,{placement:"right",content:"",template:'<div class="popover"><div class="arrow"></div><div class="popover-inner"><h3 class="popover-title"></h3><div class="popover-content"><p></p></div></div></div>'})}(window.jQuery),!function(a){function b(b,c){var d=a.proxy(this.process,this),e=a(b).is("body")?a(window):a(b),f;this.options=a.extend({},a.fn.scrollspy.defaults,c),this.$scrollElement=e.on("scroll.scroll.data-api",d),this.selector=(this.options.target||(f=a(b).attr("href"))&&f.replace(/.*(?=#[^\s]+$)/,"")||"")+" .nav li > a",this.$body=a("body").on("click.scroll.data-api",this.selector,d),this.refresh(),this.process()}"use strict",b.prototype={constructor:b,refresh:function(){this.targets=this.$body.find(this.selector).map(function(){var b=a(this).attr("href");return/^#\w/.test(b)&&a(b).length?b:null}),this.offsets=a.map(this.targets,function(b){return a(b).position().top})},process:function(){var a=this.$scrollElement.scrollTop()+this.options.offset,b=this.offsets,c=this.targets,d=this.activeTarget,e;for(e=b.length;e--;)d!=c[e]&&a>=b[e]&&(!b[e+1]||a<=b[e+1])&&this.activate(c[e])},activate:function(a){var b;this.activeTarget=a,this.$body.find(this.selector).parent(".active").removeClass("active"),b=this.$body.find(this.selector+'[href="'+a+'"]').parent("li").addClass("active"),b.parent(".dropdown-menu")&&b.closest("li.dropdown").addClass("active")}},a.fn.scrollspy=function(c){return this.each(function(){var d=a(this),e=d.data("scrollspy"),f=typeof c=="object"&&c;e||d.data("scrollspy",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.scrollspy.Constructor=b,a.fn.scrollspy.defaults={offset:10},a(function(){a('[data-spy="scroll"]').each(function(){var b=a(this);b.scrollspy(b.data())})})}(window.jQuery),!function(a){"use strict";var b=function(b){this.element=a(b)};b.prototype={constructor:b,show:function(){var b=this.element,c=b.closest("ul:not(.dropdown-menu)"),d=b.attr("data-target"),e,f;d||(d=b.attr("href"),d=d&&d.replace(/.*(?=#[^\s]*$)/,""));if(b.parent("li").hasClass("active"))return;e=c.find(".active a").last()[0],b.trigger({type:"show",relatedTarget:e}),f=a(d),this.activate(b.parent("li"),c),this.activate(f,f.parent(),function(){b.trigger({type:"shown",relatedTarget:e})})},activate:function(b,c,d){function g(){e.removeClass("active").find("> .dropdown-menu > .active").removeClass("active"),b.addClass("active"),f?(b[0].offsetWidth,b.addClass("in")):b.removeClass("fade"),b.parent(".dropdown-menu")&&b.closest("li.dropdown").addClass("active"),d&&d()}var e=c.find("> .active"),f=d&&a.support.transition&&e.hasClass("fade");f?e.one(a.support.transition.end,g):g(),e.removeClass("in")}},a.fn.tab=function(c){return this.each(function(){var d=a(this),e=d.data("tab");e||d.data("tab",e=new b(this)),typeof c=="string"&&e[c]()})},a.fn.tab.Constructor=b,a(function(){a("body").on("click.tab.data-api",'[data-toggle="tab"], [data-toggle="pill"]',function(b){b.preventDefault(),a(this).tab("show")})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.typeahead.defaults,c),this.matcher=this.options.matcher||this.matcher,this.sorter=this.options.sorter||this.sorter,this.highlighter=this.options.highlighter||this.highlighter,this.$menu=a(this.options.menu).appendTo("body"),this.source=this.options.source,this.shown=!1,this.listen()};b.prototype={constructor:b,select:function(){var a=this.$menu.find(".active").attr("data-value");return this.$element.val(a),this.hide()},show:function(){var b=a.extend({},this.$element.offset(),{height:this.$element[0].offsetHeight});return this.$menu.css({top:b.top+b.height,left:b.left}),this.$menu.show(),this.shown=!0,this},hide:function(){return this.$menu.hide(),this.shown=!1,this},lookup:function(b){var c=this,d,e;return this.query=this.$element.val(),this.query?(d=a.grep(this.source,function(a){if(c.matcher(a))return a}),d=this.sorter(d),d.length?this.render(d.slice(0,this.options.items)).show():this.shown?this.hide():this):this.shown?this.hide():this},matcher:function(a){return~a.toLowerCase().indexOf(this.query.toLowerCase())},sorter:function(a){var b=[],c=[],d=[],e;while(e=a.shift())e.toLowerCase().indexOf(this.query.toLowerCase())?~e.indexOf(this.query)?c.push(e):d.push(e):b.push(e);return b.concat(c,d)},highlighter:function(a){return a.replace(new RegExp("("+this.query+")","ig"),function(a,b){return"<strong>"+b+"</strong>"})},render:function(b){var c=this;return b=a(b).map(function(b,d){return b=a(c.options.item).attr("data-value",d),b.find("a").html(c.highlighter(d)),b[0]}),b.first().addClass("active"),this.$menu.html(b),this},next:function(b){var c=this.$menu.find(".active").removeClass("active"),d=c.next();d.length||(d=a(this.$menu.find("li")[0])),d.addClass("active")},prev:function(a){var b=this.$menu.find(".active").removeClass("active"),c=b.prev();c.length||(c=this.$menu.find("li").last()),c.addClass("active")},listen:function(){this.$element.on("blur",a.proxy(this.blur,this)).on("keypress",a.proxy(this.keypress,this)).on("keyup",a.proxy(this.keyup,this)),(a.browser.webkit||a.browser.msie)&&this.$element.on("keydown",a.proxy(this.keypress,this)),this.$menu.on("click",a.proxy(this.click,this)).on("mouseenter","li",a.proxy(this.mouseenter,this))},keyup:function(a){a.stopPropagation(),a.preventDefault();switch(a.keyCode){case 40:case 38:break;case 9:case 13:if(!this.shown)return;this.select();break;case 27:this.hide();break;default:this.lookup()}},keypress:function(a){a.stopPropagation();if(!this.shown)return;switch(a.keyCode){case 9:case 13:case 27:a.preventDefault();break;case 38:a.preventDefault(),this.prev();break;case 40:a.preventDefault(),this.next()}},blur:function(a){var b=this;a.stopPropagation(),a.preventDefault(),setTimeout(function(){b.hide()},150)},click:function(a){a.stopPropagation(),a.preventDefault(),this.select()},mouseenter:function(b){this.$menu.find(".active").removeClass("active"),a(b.currentTarget).addClass("active")}},a.fn.typeahead=function(c){return this.each(function(){var d=a(this),e=d.data("typeahead"),f=typeof c=="object"&&c;e||d.data("typeahead",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.typeahead.defaults={source:[],items:8,menu:'<ul class="typeahead dropdown-menu"></ul>',item:'<li><a href="#"></a></li>'},a.fn.typeahead.Constructor=b,a(function(){a("body").on("focus.typeahead.data-api",'[data-provide="typeahead"]',function(b){var c=a(this);if(c.data("typeahead"))return;b.preventDefault(),c.typeahead(c.data())})})}(window.jQuery);

/*
 *	lib/js/lib/sprintf.js
 */
var sprintf=(function(){function get_type(variable){return Object.prototype.toString.call(variable).slice(8,-1).toLowerCase();}
function str_repeat(input,multiplier){for(var output=[];multiplier>0;output[--multiplier]=input){}
return output.join('');}
var str_format=function(){if(!str_format.cache.hasOwnProperty(arguments[0])){str_format.cache[arguments[0]]=str_format.parse(arguments[0]);}
return str_format.format.call(null,str_format.cache[arguments[0]],arguments);};str_format.format=function(parse_tree,argv){var cursor=1,tree_length=parse_tree.length,node_type='',arg,output=[],i,k,match,pad,pad_character,pad_length;for(i=0;i<tree_length;i++){node_type=get_type(parse_tree[i]);if(node_type==='string'){output.push(parse_tree[i]);}
else if(node_type==='array'){match=parse_tree[i];if(match[2]){arg=argv[cursor];for(k=0;k<match[2].length;k++){if(!arg.hasOwnProperty(match[2][k])){arg='';}else{arg=arg[match[2][k]];}}}
else if(match[1]){arg=argv[match[1]];}
else{arg=argv[cursor++];}
if(/[^s]/.test(match[8])&&(get_type(arg)!='number')){throw(sprintf('[sprintf] expecting number but found %s',get_type(arg)));}
switch(match[8]){case'b':arg=arg.toString(2);break;case'c':arg=String.fromCharCode(arg);break;case'd':arg=parseInt(arg,10);break;case'e':arg=match[7]?arg.toExponential(match[7]):arg.toExponential();break;case'f':arg=match[7]?parseFloat(arg).toFixed(match[7]):parseFloat(arg);break;case'o':arg=arg.toString(8);break;case's':arg=((arg=String(arg))&&match[7]?arg.substring(0,match[7]):arg);break;case'u':arg=Math.abs(arg);break;case'x':arg=arg.toString(16);break;case'X':arg=arg.toString(16).toUpperCase();break;}
arg=(/[def]/.test(match[8])&&match[3]&&arg>=0?'+'+arg:arg);pad_character=match[4]?match[4]=='0'?'0':match[4].charAt(1):' ';pad_length=match[6]-String(arg).length;pad=match[6]?str_repeat(pad_character,pad_length):'';output.push(match[5]?arg+pad:pad+arg);}}
return output.join('');};str_format.cache={};str_format.parse=function(fmt){var _fmt=fmt,match=[],parse_tree=[],arg_names=0;while(_fmt){if((match=/^[^\x25]+/.exec(_fmt))!==null){parse_tree.push(match[0]);}
else if((match=/^\x25{2}/.exec(_fmt))!==null){parse_tree.push('%');}
else if((match=/^\x25(?:([1-9]\d*)\$|\(([^\)]+)\))?(\+)?(0|'[^$])?(-)?(\d+)?(?:\.(\d+))?([b-fosuxX])/.exec(_fmt))!==null){if(match[2]){arg_names|=1;var field_list=[],replacement_field=match[2],field_match=[];if((field_match=/^([a-z_][a-z_\d]*)/i.exec(replacement_field))!==null){field_list.push(field_match[1]);while((replacement_field=replacement_field.substring(field_match[0].length))!==''){if((field_match=/^\.([a-z_][a-z_\d]*)/i.exec(replacement_field))!==null){field_list.push(field_match[1]);}
else if((field_match=/^\[(\d+)\]/.exec(replacement_field))!==null){field_list.push(field_match[1]);}
else{throw('[sprintf] huh?');}}}
else{throw('[sprintf] huh?');}
match[2]=field_list;}
else{arg_names|=2;}
if(arg_names===3){throw('[sprintf] mixing positional and named placeholders is not (yet) supported');}
parse_tree.push(match);}
else{throw('[sprintf] huh?');}
_fmt=_fmt.substring(match[0].length);}
return parse_tree;};return str_format;})();var vsprintf=function(fmt,argv){argv.unshift(fmt);return sprintf.apply(null,argv);};
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
 *	lib/js/wn/versions.js
 */
wn.versions={check:function(){if(window.localStorage){var localversion=localStorage._version_number;localStorage.clear();}}}
/*
 *	lib/js/wn/assets.js
 */
wn.assets={executed_:{},exists:function(src){if('localStorage'in window&&localStorage.getItem(src))
return true},add:function(src,txt){if('localStorage'in window){localStorage.setItem(src,txt);}},get:function(src){return localStorage.getItem(src);},extn:function(src){if(src.indexOf('?')!=-1){src=src.split('?').slice(-1)[0];}
return src.split('.').slice(-1)[0];},load:function(src){var t=src;$.ajax({url:t,data:{q:Math.floor(Math.random()*1000)},dataType:'text',success:function(txt){wn.assets.add(src,txt);},async:false})},execute:function(src){if(!wn.assets.exists(src)){wn.assets.load(src);}
var type=wn.assets.extn(src);if(wn.assets.handler[type]){wn.assets.handler[type](wn.assets.get(src),src);wn.assets.executed_[src]=1;}},handler:{js:function(txt,src){wn.dom.eval(txt);},css:function(txt,src){wn.dom.set_style(txt);},cgi:function(txt,src){wn.dom.eval(txt)}}}
/*
 *	lib/js/wn/require.js
 */
wn.require=function(items){if(typeof items==="string"){items=[items];}
var l=items.length;for(var i=0;i<l;i++){var src=items[i];wn.assets.execute(src);}}
/*
 *	lib/js/wn/dom.js
 */
wn.provide('wn.dom');wn.dom={id_count:0,by_id:function(id){return document.getElementById(id);},set_unique_id:function(ele){var id='unique-'+wn.dom.id_count;if(ele)
ele.setAttribute('id',id);wn.dom.id_count++;return id;},eval:function(txt){if(!txt)return;var el=document.createElement('script');el.appendChild(document.createTextNode(txt));document.getElementsByTagName('head')[0].appendChild(el);},set_style:function(txt){if(!txt)return;var se=document.createElement('style');se.type="text/css";if(se.styleSheet){se.styleSheet.cssText=txt;}else{se.appendChild(document.createTextNode(txt));}
document.getElementsByTagName('head')[0].appendChild(se);},add:function(parent,newtag,className,cs,innerHTML,onclick){if(parent&&parent.substr)parent=wn.dom.by_id(parent);var c=document.createElement(newtag);if(parent)
parent.appendChild(c);if(className){if(newtag.toLowerCase()=='img')
c.src=className
else
c.className=className;}
if(cs)wn.dom.css(c,cs);if(innerHTML)c.innerHTML=innerHTML;if(onclick)c.onclick=onclick;return c;},css:function(ele,s){if(ele&&s){for(var i in s)ele.style[i]=s[i];};return ele;},placeholder:function(dim,letter){function getsinglecol(){return Math.min(Math.round(Math.random()*9)*Math.round(Math.random()*1)+3,9)}
function getcol(){return''+getsinglecol()+getsinglecol()+getsinglecol();}
args={width:Math.round(flt(dim)*0.7)+'px',height:Math.round(flt(dim)*0.7)+'px',padding:Math.round(flt(dim)*0.15)+'px','font-size':Math.round(flt(dim)*0.6)+'px',col1:getcol(),col2:getcol(),letter:letter.substr(0,1).toUpperCase()}
return repl('<div style="\
   height: %(height)s; \
   width: %(width)s; \
   font-size: %(font-size)s; \
   color: #fff; \
   text-align: center; \
   padding: %(padding)s; \
   background: -moz-linear-gradient(top,  #%(col1)s 0%, #%(col2)s 99%); /* FF3.6+ */\
   background: -webkit-gradient(linear, left top, left bottom, color-stop(0%,#%(col1)s), color-stop(99%,#%(col2)s)); /* Chrome,Safari4+ */\
   background: -webkit-linear-gradient(top,  #%(col1)s 0%,#%(col2)s 99%); /* Chrome10+,Safari5.1+ */\
   background: -o-linear-gradient(top,  #%(col1)s 0%,#%(col2)s 99%); /* Opera 11.10+ */\
   background: -ms-linear-gradient(top,  #%(col1)s 0%,#%(col2)s 99%); /* IE10+ */\
   background: linear-gradient(top,  #%(col1)s 0%,#%(col2)s 99%); /* W3C */\
   filter: progid:DXImageTransform.Microsoft.gradient( startColorstr=\'#%(col1)s\', endColorstr=\'#%(col2)s\',GradientType=0 ); /* IE6-9 */\
   ">%(letter)s</div>',args);}}
wn.get_cookie=function(c){var clist=(document.cookie+'').split(';');var cookies={};for(var i=0;i<clist.length;i++){var tmp=clist[i].split('=');cookies[strip(tmp[0])]=strip(tmp[1]);}
return cookies[c];}
wn.dom.set_box_shadow=function(ele,spread){$(ele).css('-moz-box-shadow','0px 0px '+spread+'px rgba(0,0,0,0.3);')
$(ele).css('-webkit-box-shadow','0px 0px '+spread+'px rgba(0,0,0,0.3);')
$(ele).css('-box-shadow','0px 0px '+spread+'px rgba(0,0,0,0.3);')};(function($){$.fn.add_options=function(options_list){for(var i=0;i<options_list.length;i++){var v=options_list[i];value=v.value||v;label=v.label||v;$('<option>').html(label).attr('value',value).appendTo(this);}
$(this).val(options_list[0].value||options_list[0]);}
$.fn.set_working=function(){var ele=this.get(0);$(ele).attr('disabled','disabled');if(ele.loading_img){$(ele.loading_img).toggle(true);}else{ele.loading_img=$('<img src="images/lib/ui/button-load.gif" \
    style="margin-left: 4px; margin-bottom: -2px; display: inline;" />').insertAfter(ele);}}
$.fn.done_working=function(){var ele=this.get(0);$(ele).attr('disabled',null);if(ele.loading_img){$(ele.loading_img).toggle(false);};}})(jQuery);
/*
 *	lib/js/wn/model.js
 */
wn.provide('wn.model');wn.model={no_value_type:['Section Break','Column Break','HTML','Table','Button','Image'],new_names:{},with_doctype:function(doctype,callback){if(locals.DocType[doctype]){callback();}else{wn.call({method:'webnotes.widgets.form.load.getdoctype',args:{doctype:doctype},callback:callback});}},with_doc:function(doctype,name,callback){if(!name)name=doctype;if(locals[doctype]&&locals[doctype][name]){callback(name);}else{wn.call({method:'webnotes.widgets.form.load.getdoc',args:{doctype:doctype,name:name},callback:function(r){callback(name,r);}});}},can_delete:function(doctype){if(!doctype)return false;return wn.boot.profile.can_cancel.indexOf(doctype)!=-1;}}
/*
 *	lib/js/wn/meta.js
 */
wn.provide('wn.meta.docfield_map');wn.provide('wn.meta.docfield_list');wn.provide('wn.meta.doctypes');$.extend(wn.meta,{add_field:function(df){wn.provide('wn.meta.docfield_map.'+df.parent);wn.meta.docfield_map[df.parent][df.fieldname||df.label]=df;if(!wn.meta.docfield_list[df.parent])
wn.meta.docfield_list[df.parent]=[];for(var i in wn.meta.docfield_list[df.parent]){var d=wn.meta.docfield_list[df.parent][i];if(df.fieldname==d.fieldname)
return;}
wn.meta.docfield_list[df.parent].push(df);}});
/*
 *	lib/js/wn/misc/tools.js
 */
wn.markdown=function(txt){if(!wn.md2html){wn.require('js/lib/showdown.js');wn.md2html=new Showdown.converter();}
return wn.md2html.makeHtml(txt);}
/*
 *	lib/js/wn/misc/user.js
 */
wn.user_info=function(uid){var def={'fullname':uid,'image':'images/lib/ui/no_img_m.gif'}
if(!wn.boot.user_info)return def
if(!wn.boot.user_info[uid])return def
if(!wn.boot.user_info[uid].fullname)
wn.boot.user_info[uid].fullname=uid;if(!wn.boot.user_info[uid].image)
wn.boot.user_info[uid].image=def.image;return wn.boot.user_info[uid];}
wn.provide('wn.user');$.extend(wn.user,{name:(wn.boot?wn.boot.profile.name:'Guest'),has_role:function(rl){if(typeof rl=='string')
rl=[rl];for(var i in rl){if((wn.boot?wn.boot.profile.roles:['Guest']).indexOf(rl[i])!=-1)
return true;}},is_report_manager:function(){return wn.user.has_role(['Administrator','System Manager','Report Manager']);}})
wn.session_alive=true;$(document).bind('mousemove',function(){wn.session_alive=true;if(wn.session_alive_timeout)
clearTimeout(wn.session_alive_timeout);wn.session_alive_timeout=setTimeout('wn.session_alive=false;',30000);})
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
 *	lib/js/wn/router.js
 */
wn.re_route={}
wn.route=function(){if(wn.re_route[window.location.hash]){var re_route_val=wn.get_route_str(wn.re_route[window.location.hash]);var cur_route_val=wn.get_route_str(wn._cur_route);if(decodeURIComponent(re_route_val)===decodeURIComponent(cur_route_val)){window.history.back();return;}else{window.location.hash=wn.re_route[window.location.hash];}}
wn._cur_route=window.location.hash;route=wn.get_route();switch(route[0]){case"List":wn.views.doclistview.show(route[1]);break;case"Form":if(route.length>3){route[2]=route.splice(2).join('/');}
wn.views.formview.show(route[1],route[2]);break;case"Report":wn.views.reportview.show(route[1],route[2]);break;case"Report2":wn.views.reportview2.show();break;default:wn.views.pageview.show(route[0]);}}
wn.get_route=function(route){return $.map(wn.get_route_str(route).split('/'),function(r){return decodeURIComponent(r);});}
wn.get_route_str=function(route){if(!route)
route=window.location.hash;if(route.substr(0,1)=='#')route=route.substr(1);if(route.substr(0,1)=='!')route=route.substr(1);return route;}
wn.set_route=function(){route=$.map(arguments,function(a){return encodeURIComponent(a)}).join('/');window.location.hash=route;wn.app.set_favicon();}
wn._cur_route=null;$(window).bind('hashchange',function(){if(location.hash==wn._cur_route)
return;wn.route();});
/*
 *	lib/js/wn/ui/listing.js
 */
wn.provide('wn.ui');wn.ui.Listing=Class.extend({init:function(opts){this.opts=opts||{};this.page_length=20;this.start=0;this.data=[];if(opts){this.make();}},prepare_opts:function(){if(this.opts.new_doctype){if(wn.boot.profile.can_read.indexOf(this.opts.new_doctype)==-1){this.opts.new_doctype=null;}else{this.opts.new_doctype=get_doctype_label(this.opts.new_doctype);}}
if(!this.opts.no_result_message){this.opts.no_result_message='Nothing to show'}},make:function(opts){if(opts){this.opts=opts;}
this.prepare_opts();$.extend(this,this.opts);$(this.parent).html(repl('\
   <div class="wnlist">\
    <h3 class="title hide">%(title)s</h3>\
    \
    <div class="list-filters hide">\
     <div class="show_filters well">\
      <div class="filter_area"></div>\
      <div>\
       <button class="btn btn-small btn-info search-btn">\
        <i class="icon-refresh icon-white"></i> Search</button>\
       <button class="btn btn-small add-filter-btn">\
        <i class="icon-plus"></i> Add Filter</button>\
      </div>\
     </div>\
    </div>\
    \
    <div style="margin-bottom:9px" class="list-toolbar-wrapper">\
     <div class="list-toolbar" style="display:inline-block; margin-right: 10px;">\
     </div>\
     <div style="display:inline-block; width: 24px; margin-left: 4px">\
      <img src="images/lib/ui/button-load.gif" \
      class="img-load"/></div>\
    </div><div style="clear:both"></div>\
    \
    <div class="no-result help hide">\
     %(no_result_message)s\
    </div>\
    \
    <div class="result">\
     <div class="result-list"></div>\
    </div>\
    \
    <div class="paging-button">\
     <button class="btn btn-small btn-more hide">More...</div>\
    </div>\
   </div>\
  ',this.opts));this.$w=$(this.parent).find('.wnlist');this.set_events();if(this.appframe){this.$w.find('.list-toolbar-wrapper').toggle(false);}
if(this.show_filters){this.make_filters();}},add_button:function(label,click,icon){if(this.appframe){return this.appframe.add_button(label,click,icon)}else{$button=$('<button class="btn btn-small"></button>').appendTo(this.$w.find('.list-toolbar'))
if(icon){$('<i>').addClass(icon).appendTo($button);}
$button.html(label).click(click);return $button}},show_view:function($btn,$div,$btn_unsel,$div_unsel){$btn_unsel.removeClass('btn-info');$btn_unsel.find('i').removeClass('icon-white');$div_unsel.toggle(false);$btn.addClass('btn-info');$btn.find('i').addClass('icon-white');$div.toggle(true);},set_events:function(){var me=this;this.$w.find('.btn-more').click(function(){me.run({append:true});});if(this.title){this.$w.find('h3').html(this.title).toggle(true);}
if(!(this.hide_refresh||this.no_refresh)){this.add_button('Refresh',function(){me.run();},'icon-refresh');}
if(this.new_doctype){this.add_button('New '+this.new_doctype,function(){me.make_new_doc(me.new_doctype);},'icon-plus');}
if(me.show_filters){this.add_button('Show Filters',function(){me.filter_list.show_filters();},'icon-search').addClass('btn-filter');}
if(me.no_toolbar||me.hide_toolbar){me.$w.find('.list-toolbar-wrapper').toggle(false);}},make_new_doc:function(new_doctype){new_doc(new_doctype);},make_filters:function(){this.filter_list=new wn.ui.FilterList({listobj:this,$parent:this.$w.find('.list-filters').toggle(true),doctype:this.doctype,filter_fields:this.filter_fields});},clear:function(){this.data=[];this.$w.find('.result-list').empty();this.$w.find('.result').toggle(true);this.$w.find('.no-result').toggle(false);this.start=0;},run:function(){var me=this;var a0=arguments[0];var a1=arguments[1];if(a0&&typeof a0=='function')
this.onrun=a0;if(a0&&a0.callback)
this.onrun=a0.callback;if(!a1&&!(a0&&a0.append))
this.start=0;me.set_working(true);wn.call({method:this.opts.method||'webnotes.widgets.query_builder.runquery',args:this.get_call_args(a0),callback:function(r){me.set_working(false);me.render_results(r)},no_spinner:this.opts.no_loading});},set_working:function(flag){this.$w.find('.img-load').toggle(flag);},get_call_args:function(opts){if(!this.method){var query=this.get_query?this.get_query():this.query;query=this.add_limits(query);var args={query_max:this.query_max,as_dict:1}
args.simple_query=query;}else{var args={limit_start:this.start,limit_page_length:this.page_length}}
if(this.args)
$.extend(args,this.args)
if(this.get_args){$.extend(args,this.get_args(opts));}
return args;},render_results:function(r){if(this.start==0)this.clear();this.$w.find('.btn-more').toggle(false);if(r.message)r.values=r.message;if(r.values&&r.values.length){this.data=this.data.concat(r.values);this.render_list(r.values);this.update_paging(r.values);}else{if(this.start==0){this.$w.find('.result').toggle(false);this.$w.find('.no-result').toggle(true);}}
if(this.onrun)this.onrun();if(this.callback)this.callback(r);},render_list:function(values){var m=Math.min(values.length,this.page_length);for(var i=0;i<m;i++){this.render_row(this.add_row(),values[i],this,i);}},update_paging:function(values){if(values.length>=this.page_length){this.$w.find('.btn-more').toggle(true);this.start+=this.page_length;}},add_row:function(){return $('<div class="list-row">').appendTo(this.$w.find('.result-list')).get(0);},refresh:function(){this.run();},add_limits:function(query){query+=' LIMIT '+this.start+','+(this.page_length+1);return query}});
/*
 *	lib/js/wn/ui/filters.js
 */
wn.ui.FilterList=Class.extend({init:function(opts){wn.require('js/fields.js');$.extend(this,opts);this.filters=[];this.$w=this.$parent;this.set_events();},set_events:function(){var me=this;this.$w.find('.add-filter-btn').bind('click',function(){me.add_filter();});this.$w.find('.search-btn').bind('click',function(){me.listobj.run();});},show_filters:function(){this.$w.find('.show_filters').toggle();if(!this.filters.length)
this.add_filter();},add_filter:function(fieldname,condition,value){this.push_new_filter(fieldname,condition,value);if(fieldname){this.$w.find('.show_filters').toggle(true);}},push_new_filter:function(fieldname,condition,value){this.filters.push(new wn.ui.Filter({flist:this,fieldname:fieldname,condition:condition,value:value}));},get_filters:function(){var values=[];$.each(this.filters,function(i,f){if(f.field)
values.push(f.get_value());})
return values;},update_filters:function(){var fl=[];$.each(this.filters,function(i,f){if(f.field)fl.push(f);})
this.filters=fl;},get_filter:function(fieldname){for(var i in this.filters){if(this.filters[i].field.df.fieldname==fieldname)
return this.filters[i];}}});wn.ui.Filter=Class.extend({init:function(opts){$.extend(this,opts);this.doctype=this.flist.doctype;this.make();this.make_select();this.set_events();},make:function(){this.flist.$w.find('.filter_area').append('<div class="list_filter">\
  <span class="fieldname_select_area"></span>\
  <select class="condition">\
   <option value="=">Equals</option>\
   <option value="like">Like</option>\
   <option value=">=">Greater or equals</option>\
   <option value="<=">Less or equals</option>\
   <option value=">">Greater than</option>\
   <option value="<">Less than</option>\
   <option value="in">In</option>\
   <option value="!=">Not equals</option>\
  </select>\
  <span class="filter_field"></span>\
  <a class="close">&times;</a>\
  </div>');this.$w=this.flist.$w.find('.list_filter:last-child');},make_select:function(){this.fieldselect=new wn.ui.FieldSelect(this.$w.find('.fieldname_select_area'),this.doctype,this.filter_fields);},set_events:function(){var me=this;this.fieldselect.$select.bind('change',function(){me.set_field(this.value);});this.$w.find('a.close').bind('click',function(){me.$w.css('display','none');var value=me.field.get_value();me.field=null;if(!me.flist.get_filters().length){me.flist.$w.find('.set_filters').toggle(true);me.flist.$w.find('.show_filters').toggle(false);}
if(value){me.flist.listobj.run();}
me.flist.update_filters();return false;});me.$w.find('.condition').change(function(){if($(this).val()=='in'){me.set_field(me.field.df.fieldname,'Data');if(!me.field.desc_area)
me.field.desc_area=$a(me.field.wrapper,'span','help',null,'values separated by comma');}else{me.set_field(me.field.df.fieldname);}});if(me.fieldname){this.set_values(me.fieldname,me.condition,me.value);}else{me.set_field('name');}},set_values:function(fieldname,condition,value){this.set_field(fieldname);if(condition)this.$w.find('.condition').val(condition).change();if(value)this.field.set_input(value)},set_field:function(fieldname,fieldtype){var me=this;var cur=me.field?{fieldname:me.field.df.fieldname,fieldtype:me.field.df.fieldtype}:{}
var df=me.fieldselect.fields_by_name[fieldname];this.set_fieldtype(df,fieldtype);if(me.field&&cur.fieldname==fieldname&&df.fieldtype==cur.fieldtype){return;}
me.fieldselect.$select.val(fieldname);var field_area=me.$w.find('.filter_field').empty().get(0);f=make_field(df,null,field_area,null,0,1);f.df.single_select=1;f.not_in_form=1;f.with_label=0;f.refresh();me.field=f;this.set_default_condition(df,fieldtype);$(me.field.wrapper).find(':input').keydown(function(ev){if(ev.which==13){me.flist.listobj.run();}})},set_fieldtype:function(df,fieldtype){if(df.original_type)
df.fieldtype=df.original_type;else
df.original_type=df.fieldtype;df.description='';df.reqd=0;if(fieldtype){df.fieldtype=fieldtype;return;}
if(df.fieldtype=='Check'){df.fieldtype='Select';df.options='No\nYes';}else if(['Text','Text Editor','Code','Link'].indexOf(df.fieldtype)!=-1){df.fieldtype='Data';}},set_default_condition:function(df,fieldtype){if(!fieldtype){if(df.fieldtype=='Data'){this.$w.find('.condition').val('like');}else{this.$w.find('.condition').val('=');}}},get_value:function(){var me=this;var val=me.field.get_value();var cond=me.$w.find('.condition').val();if(me.field.df.original_type=='Check'){val=(val=='Yes'?1:0);}
if(cond=='like'){val=val+'%';}
return[me.fieldselect.$select.find('option:selected').attr('table'),me.field.df.fieldname,me.$w.find('.condition').val(),cstr(val)];}});wn.ui.FieldSelect=Class.extend({init:function(parent,doctype,filter_fields,with_blank){this.doctype=doctype;this.fields_by_name={};this.with_blank=with_blank;this.$select=$('<select>').appendTo(parent);if(filter_fields){for(var i in filter_fields)
this.add_field_option(this.filter_fields[i])}else{this.build_options();}},build_options:function(){var me=this;me.table_fields=[];var std_filters=[{fieldname:'name',fieldtype:'Data',label:'ID',parent:me.doctype},{fieldname:'modified',fieldtype:'Date',label:'Last Modified',parent:me.doctype},{fieldname:'owner',fieldtype:'Data',label:'Created By',parent:me.doctype},{fieldname:'creation',fieldtype:'Date',label:'Created On',parent:me.doctype},{fieldname:'_user_tags',fieldtype:'Data',label:'Tags',parent:me.doctype},{fieldname:'docstatus',fieldtype:'Int',label:'Doc Status',parent:me.doctype},];var doctype_obj=locals['DocType'][me.doctype];if(doctype_obj&&cint(doctype_obj.istable)){std_filters=std_filters.concat([{fieldname:'parent',fieldtype:'Data',label:'Parent',parent:me.doctype}]);}
if(this.with_blank){this.$select.append($('<option>',{value:''}).text(''));}
$.each(std_filters.concat(wn.meta.docfield_list[me.doctype]),function(i,df){me.add_field_option(df);});$.each(me.table_fields,function(i,table_df){if(table_df.options){$.each(wn.meta.docfield_list[table_df.options],function(i,df){me.add_field_option(df);});}});},add_field_option:function(df){var me=this;if(me.doctype&&df.parent==me.doctype){var label=df.label;var table=me.doctype;if(df.fieldtype=='Table')me.table_fields.push(df);}else{var label=df.label+' ('+df.parent+')';var table=df.parent;}
if(wn.model.no_value_type.indexOf(df.fieldtype)==-1&&!(me.fields_by_name[df.fieldname]&&me.fields_by_name[df.fieldname]['parent']==df.parent)){this.$select.append($('<option>',{value:df.fieldname,table:table}).text(label));me.fields_by_name[df.fieldname]=df;}}})
/*
 *	lib/js/wn/views/container.js
 */
wn.provide('wn.pages');wn.provide('wn.views');wn.views.Container=Class.extend({init:function(){this.container=$('#body_div').get(0);this.page=null;this.pagewidth=$('#body_div').width();this.pagemargin=50;},add_page:function(label,onshow,onhide){var page=$('<div class="content"></div>').attr('id',"page-"+label).appendTo(this.container).get(0);if(onshow)
$(page).bind('show',onshow);if(onshow)
$(page).bind('hide',onhide);page.label=label;wn.pages[label]=page;return page;},change_to:function(label){if(this.page&&this.page.label==label){return;}
var me=this;if(label.tagName){var page=label;}else{var page=wn.pages[label];}
if(!page){console.log('Page not found '+label);return;}
if(this.page){$(this.page).toggle(false);$(this.page).trigger('hide');}
this.page=page;$(this.page).fadeIn();$(this.page).trigger('show');this.page._route=window.location.hash;document.title=this.page.label;scroll(0,0);return this.page;}});wn.views.add_module_btn=function(parent,module){$(parent).append(repl('<span class="label" style="margin-right: 8px; cursor: pointer;"\
     onclick="wn.set_route(\'%(module_small)s-home\')">\
     <i class="icon-home icon-white"></i> %(module)s Home\
    </span>',{module:module,module_small:module.toLowerCase()}));}
wn.views.add_list_btn=function(parent,doctype){$(parent).append(repl('<span class="label" style="margin-right: 8px; cursor: pointer;"\
     onclick="wn.set_route(\'List\', \'%(doctype)s\')">\
     <i class="icon-list icon-white"></i> %(doctype)s List\
    </span>',{doctype:doctype}));}
/*
 *	lib/js/wn/views/pageview.js
 */
wn.provide('wn.views.pageview');wn.views.pageview={with_page:function(name,callback){if((locals.Page&&locals.Page[name])||name==window.page_name){callback();}else{wn.call({method:'webnotes.widgets.page.getpage',args:{'name':name},callback:callback});}},show:function(name){if(!name)name=(wn.boot?wn.boot.home_page:window.page_name);wn.views.pageview.with_page(name,function(r){if(r&&r.exc){if(!r['403'])wn.container.change_to('404');}else if(!wn.pages[name]){new wn.views.Page(name);}
wn.container.change_to(name);});}}
wn.views.Page=Class.extend({init:function(name,wrapper){this.name=name;var me=this;if(name==window.page_name){this.wrapper=document.getElementById('page-'+name);this.wrapper.label=document.title||window.page_name;this.wrapper.page_name=window.page_name;wn.pages[window.page_name]=this.wrapper;}else{this.pagedoc=locals.Page[this.name];this.wrapper=wn.container.add_page(this.name);this.wrapper.label=this.pagedoc.title||this.pagedoc.name;this.wrapper.page_name=this.pagedoc.name;this.wrapper.innerHTML=this.pagedoc.content;wn.dom.eval(this.pagedoc.__script||this.pagedoc.script||'');wn.dom.set_style(this.pagedoc.style||'');}
this.trigger('onload');$(this.wrapper).bind('show',function(){cur_frm=null;me.trigger('onshow');me.trigger('refresh');});},trigger:function(eventname){var me=this;try{if(pscript[eventname+'_'+this.name]){pscript[eventname+'_'+this.name](me.wrapper);}else if(me.wrapper[eventname]){me.wrapper[eventname](me.wrapper);}}catch(e){console.log(e);}}})
wn.views.make_404=function(){var page=wn.container.add_page('404');$(page).html('<div class="layout-wrapper">\
  <h1>Not Found</h1><br>\
  <p>Sorry we were unable to find what you were looking for.</p>\
  <p><a href="#">Go back to home</a></p>\
  </div>').toggle(false);};wn.views.make_403=function(){var page=wn.container.add_page('403');$(page).html('<div class="layout-wrapper">\
  <h1>Not Permitted</h1><br>\
  <p>Sorry you are not permitted to view this page.</p>\
  <p><a href="#">Go back to home</a></p>\
  </div>').toggle(false);};
/*
 *	lib/js/wn/request.js
 */
wn.provide('wn.request');wn.request.url='server.py';wn.request.prepare=function(opts){if(opts.btn)$(opts.btn).set_working();if(opts.show_spinner)set_loading();if(opts.freeze)freeze();if(!opts.args.cmd){console.log(opts)
throw"Incomplete Request";}}
wn.request.cleanup=function(opts,r){if(opts.btn)$(opts.btn).done_working();if(opts.show_spinner)hide_loading();if(opts.freeze)unfreeze();if(wn.boot&&wn.boot.sid&&wn.get_cookie('sid')!=wn.boot.sid){if(!wn.app.logged_out){msgprint('Session Expired. Logging you out');wn.app.logout();}
return;}
if(r.server_messages)msgprint(r.server_messages)
if(r.exc){console.log(r.exc);};if(r['403']){wn.container.change_to('403');}
if(r.docs){LocalDB.sync(r.docs);}}
wn.request.call=function(opts){wn.request.prepare(opts);$.ajax({url:opts.url||wn.request.url,data:opts.args,type:opts.type||'POST',dataType:opts.dataType||'json',success:function(r,xhr){wn.request.cleanup(opts,r);opts.success(r,xhr.responseText);},error:function(xhr,textStatus){wn.request.cleanup(opts,{});show_alert('Unable to complete request: '+textStatus)
if(opts.error)opts.error(xhr)}})}
wn.call=function(opts){var args=$.extend({},opts.args)
if(opts.module&&opts.page){args.cmd=opts.module+'.page.'+opts.page+'.'+opts.page+'.'+opts.method}else if(opts.method){args.cmd=opts.method;}
for(key in args){if(args[key]&&typeof args[key]!='string'){args[key]=JSON.stringify(args[key]);}}
wn.request.call({args:args,success:opts.callback,error:opts.error,btn:opts.btn,freeze:opts.freeze,show_spinner:!opts.no_spinner});}
/*
 *	lib/js/core.js
 */
if(!console){var console={log:function(txt){}}}
$(document).ready(function(){wn.versions.check();wn.provide('wn.app');$.extend(wn.app,new wn.Application());});

/*
 *	lib/js/legacy/globals.js
 */
wn.provide('wn.widgets.form');wn.provide('wn.widgets.report');wn.provide('wn.utils');wn.provide('wn.model');wn.provide('wn.profile');wn.provide('wn.session');wn.provide('_f');wn.provide('_p');wn.provide('_r');wn.provide('_c');wn.provide('_e');wn.provide('_startup_data')
wn.settings.no_history=1;var NEWLINE='\n';var profile=null;var user=null;var user_defaults=null;var user_roles=null;var user_fullname=null;var user_email=null;var user_img={};var pscript={};var selector=null;var top_index=91;var _f={};var _p={};var _e={};var _r={};var FILTER_SEP='\1';var frms={};var cur_frm=null;var pscript={};var validated=true;var validation_message='';var tinymce_loaded=null;
/*
 *	lib/js/legacy/utils/datatype.js
 */
wn.utils.full_name=function(fn,ln){return fn+(ln?' ':'')+(ln?ln:'')}
function fmt_money(v){if(v==null||v=='')return'0.00';v=(v+'').replace(/,/g,'');v=parseFloat(v);if(isNaN(v)){return'';}else{var val=2;if(wn.boot.sysdefaults.currency_format=='Millions')val=3;v=v.toFixed(2);var delimiter=",";amount=v+'';var a=amount.split('.',2)
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
ele.innerHTML=fmt_money(v);}else if(ftype=='Int'){ele.style.textAlign='right';ele.innerHTML=v;}else if(ftype=='Check'){if(v)ele.innerHTML='<img src="images/lib/ui/tick.gif">';else ele.innerHTML='';}else{ele.innerHTML=v;}}
function clean_smart_quotes(s){if(s){s=s.replace(/\u2018/g,"'");s=s.replace(/\u2019/g,"'");s=s.replace(/\u201c/g,'"');s=s.replace(/\u201d/g,'"');s=s.replace(/\u2013/g,'-');s=s.replace(/\u2014/g,'--');}
return s;}
function copy_dict(d){var n={};for(var k in d)n[k]=d[k];return n;}
function $p(ele,top,left){ele.style.position='absolute';ele.style.top=top+'px';ele.style.left=left+'px';}
function replace_newlines(t){return t?t.replace(/\n/g,'<br>'):'';}
function cstr(s){if(s==null)return'';return s+'';}
function nth(number){number=cint(number);var s='th';if((number+'').substr(-1)=='1')s='st';if((number+'').substr(-1)=='2')s='nd';if((number+'').substr(-1)=='3')s='rd';return number+s;}
function flt(v,decimals){if(v==null||v=='')return 0;v=(v+'').replace(/,/g,'');v=parseFloat(v);if(isNaN(v))
v=0;if(decimals!=null)
return parseFloat(v.toFixed(decimals));return v;}
function esc_quotes(s){if(s==null)s='';return s.replace(/'/,"\'");}
var crop=function(s,len){if(s.length>len)
return s.substr(0,len-3)+'...';else
return s;}
var strip=function(s,chars){var s=lstrip(s,chars)
s=rstrip(s,chars);return s;}
var lstrip=function(s,chars){if(!chars)chars=['\n','\t',' '];var first_char=s.substr(0,1);while(in_list(chars,first_char)){var s=s.substr(1);first_char=s.substr(0,1);}
return s;}
var rstrip=function(s,chars){if(!chars)chars=['\n','\t',' '];var last_char=s.substr(s.length-1);while(in_list(chars,last_char)){var s=s.substr(0,s.length-1);last_char=s.substr(s.length-1);}
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
function docstring(obj){return JSON.stringify(obj);}
function DocLink(p,doctype,name,onload){var a=$a(p,'span','link_type');a.innerHTML=a.dn=name;a.dt=doctype;a.onclick=function(){loaddoc(this.dt,this.dn,onload)};return a;}
var doc_link=DocLink;function roundNumber(num,dec){var result=Math.round(num*Math.pow(10,dec))/Math.pow(10,dec);return result;}
/*
 *	lib/js/legacy/utils/datetime.js
 */
function same_day(d1,d2){if(d1.getFullYear()==d2.getFullYear()&&d1.getMonth()==d2.getMonth()&&d1.getDate()==d2.getDate())return true;else return false;}
var month_list=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];var month_last={1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
var month_list_full=['January','February','March','April','May','June','July','August','September','October','November','December'];var week_list=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];var week_list_full=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];function int_to_str(i,len){i=''+i;if(i.length<len)for(c=0;c<(len-i.length);c++)i='0'+i;return i}
wn.datetime={str_to_obj:function(d){if(typeof d=="object")return d;if(!d)return new Date();var tm=[null,null];if(d.search(' ')!=-1){var tm=d.split(' ')[1].split(':');var d=d.split(' ')[0];}
if(d.search('-')!=-1){var t=d.split('-');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else if(d.search('/')!=-1){var t=d.split('/');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else{return new Date();}},obj_to_str:function(d){if(typeof d=='string')return d;return d.getFullYear()+'-'+int_to_str(d.getMonth()+1,2)+'-'+int_to_str(d.getDate(),2);},obj_to_user:function(d){return dateutil.str_to_user(dateutil.obj_to_str(d));},get_diff:function(d1,d2){if(typeof d1=='string')d1=dateutil.str_to_obj(d1);if(typeof d2=='string')d2=dateutil.str_to_obj(d2);return((d1-d2)/86400000);},get_day_diff:function(d1,d2){return dateutil.get_diff(new Date(d1.getYear(),d1.getMonth(),d1.getDate(),0,0),new Date(d2.getYear(),d2.getMonth(),d2.getDate(),0,0))},add_days:function(d,days){var dt=dateutil.str_to_obj(d);var new_dt=new Date(dt.getTime()+(days*24*60*60*1000));return dateutil.obj_to_str(new_dt);},add_months:function(d,months){dt=dateutil.str_to_obj(d)
new_dt=new Date(dt.getFullYear(),dt.getMonth()+months,dt.getDate())
if(new_dt.getDate()!=dt.getDate()){return dateutil.month_end(new Date(dt.getFullYear(),dt.getMonth()+months,1))}
return dateutil.obj_to_str(new_dt);},month_start:function(){var d=new Date();return d.getFullYear()+'-'+int_to_str(d.getMonth()+1,2)+'-01';},month_end:function(d){if(!d)var d=new Date();var m=d.getMonth()+1;var y=d.getFullYear();last_date=month_last[m];if(m==2&&(y%4)==0&&((y%100)!=0||(y%400)==0))
last_date=29;return y+'-'+int_to_str(m,2)+'-'+last_date;},get_user_fmt:function(){var t=sys_defaults.date_format;if(!t)t='dd-mm-yyyy';return t;},str_to_user:function(val,no_time_str){var user_fmt=dateutil.get_user_fmt();var time_str='';if(val==null||val=='')return null;if(val.search(':')!=-1){var tmp=val.split(' ');if(tmp[1])
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
else if(user_fmt=='mm-dd-yyyy'){var d=d.split('-');return d[2]+'-'+d[0]+'-'+d[1];}},global_date_format:function(d){if(d.substr)d=this.str_to_obj(d);return nth(d.getDate())+' '+month_list_full[d.getMonth()]+' '+d.getFullYear();},get_today:function(){var today=new Date();var m=(today.getMonth()+1)+'';if(m.length==1)m='0'+m;var d=today.getDate()+'';if(d.length==1)d='0'+d;return today.getFullYear()+'-'+m+'-'+d;},get_cur_time:function(){var d=new Date();var hh=d.getHours()+''
var mm=cint(d.getMinutes()/5)*5+''
return(hh.length==1?'0'+hh:hh)+':'+(mm.length==1?'0'+mm:mm);}}
wn.datetime.only_date=function(val){if(val==null||val=='')return null;if(val.search(':')!=-1){var tmp=val.split(' ');var d=tmp[0].split('-');}else{var d=val.split('-');}
if(d.length==3)
val=d[2]+'-'+d[1]+'-'+d[0];return val;}
wn.datetime.time_to_ampm=function(v){if(!v){var d=new Date();var t=[d.getHours(),cint(d.getMinutes()/5)*5+'']}else{var t=v.split(':');}
if(t.length!=2){show_alert('[set_time] Incorect time format');return;}
if(t[1].length==1)t[1]='0'+t[1];if(cint(t[0])==0)var ret=['12',t[1],'AM'];else if(cint(t[0])<12)var ret=[cint(t[0])+'',t[1],'AM'];else if(cint(t[0])==12)var ret=['12',t[1],'PM'];else var ret=[(cint(t[0])-12)+'',t[1],'PM'];return ret;}
wn.datetime.time_to_hhmm=function(hh,mm,am){if(am=='AM'&&hh=='12'){hh='00';}else if(am=='PM'&&hh!='12'){hh=cint(hh)+12;}
if(!mm)mm='00';if(!hh)hh='00';return hh+':'+mm;}
function prettyDate(time){if(!time)return''
var date=time;if(typeof(time)=="string")
date=new Date((time||"").replace(/-/g,"/").replace(/[TZ]/g," ").replace(/\.[0-9]*/,""));var diff=(((new Date()).getTime()-date.getTime())/1000),day_diff=Math.floor(diff/86400);if(isNaN(day_diff)||day_diff<0)
return'';return day_diff==0&&(diff<60&&"just now"||diff<120&&"1 minute ago"||diff<3600&&Math.floor(diff/60)+" minutes ago"||diff<7200&&"1 hour ago"||diff<86400&&Math.floor(diff/3600)+" hours ago")||day_diff==1&&"Yesterday"||day_diff<7&&day_diff+" days ago"||day_diff<31&&Math.ceil(day_diff/7)+" weeks ago"||day_diff<365&&Math.ceil(day_diff/30)+" months ago"||"more than "+Math.floor(day_diff/365)+" year(s) ago";}
if(typeof jQuery!="undefined")
jQuery.fn.prettyDate=function(){return this.each(function(){var date=prettyDate(this.title);if(date)
jQuery(this).text(date);});};var comment_when=prettyDate;wn.datetime.comment_when=prettyDate;var date=dateutil=wn.datetime;var get_today=wn.datetime.get_today
var time_to_ampm=wn.datetime.time_to_ampm;var time_to_hhmm=wn.datetime.time_to_hhmm;var only_date=wn.datetime.only_date;
/*
 *	lib/js/legacy/utils/dom.js
 */
wn.tinymce={add_simple:function(ele,height){if(ele.myid){tinyMCE.execCommand('mceAddControl',true,ele.myid);return;}
ele.myid=wn.dom.set_unique_id(ele);$(ele).tinymce({script_url:'js/lib/tiny_mce_33/tiny_mce.js',height:height?height:'200px',theme:"advanced",theme_advanced_buttons1:"bold,italic,underline,separator,strikethrough,justifyleft,justifycenter,justifyright,justifyfull,bullist,numlist,outdent,indent,link,unlink,forecolor,backcolor,code,",theme_advanced_buttons2:"",theme_advanced_buttons3:"",theme_advanced_toolbar_location:"top",theme_advanced_toolbar_align:"left",theme_advanced_path:false,theme_advanced_resizing:false});},remove:function(ele){tinyMCE.execCommand('mceRemoveControl',true,ele.myid);},get_value:function(ele){return tinymce.get(ele.myid).getContent();}}
wn.ele={link:function(args){var span=$a(args.parent,'span','link_type',args.style);span.loading_img=$a(args.parent,'img','',{margin:'0px 4px -2px 4px',display:'none'});span.loading_img.src='images/lib/ui/button-load.gif';span.innerHTML=args.label;span.user_onclick=args.onclick;span.onclick=function(){if(!this.disabled)this.user_onclick(this);}
span.set_working=function(){this.disabled=1;$di(this.loading_img);}
span.done_working=function(){this.disabled=0;$dh(this.loading_img);}
return span;}}
function $ln(parent,label,onclick,style){return wn.ele.link({parent:parent,label:label,onclick:onclick,style:style})}
function $btn(parent,label,onclick,style,css_class,is_ajax){if(css_class==='green')css_class='btn-info';return new wn.ui.Button({parent:parent,label:label,onclick:onclick,style:style,is_ajax:is_ajax,css_class:css_class}).btn;}
$item_normal=function(ele){$y(ele,{padding:'6px 8px',cursor:'pointer',marginRight:'8px',whiteSpace:'nowrap',overflow:'hidden',borderBottom:'1px solid #DDD'});$bg(ele,'#FFF');$fg(ele,'#000');}
$item_active=function(ele){$bg(ele,'#FE8');$fg(ele,'#000');}
$item_selected=function(ele){$bg(ele,'#777');$fg(ele,'#FFF');}
$item_pressed=function(ele){$bg(ele,'#F90');$fg(ele,'#FFF');};function set_opacity(ele,ieop){var op=ieop/100;if(ele.filters){try{ele.filters.item("DXImageTransform.Microsoft.Alpha").opacity=ieop;}catch(e){ele.style.filter='progid:DXImageTransform.Microsoft.Alpha(opacity='+ieop+')';}}else{ele.style.opacity=op;}}
$br=function(ele,r,corners){if(corners){var cl=['top-left','top-right','bottom-right','bottom-left'];for(var i=0;i<4;i++){if(corners[i]){$(ele).css('-moz-border-radius-'+cl[i].replace('-',''),r).css('-webkit-'+cl[i]+'-border-radius',r);}}}else{$(ele).css('-moz-border-radius',r).css('-webkit-border-radius',r).css('border-radius',r);}}
$bs=function(ele,r){$(ele).css('-moz-box-shadow',r).css('-webkit-box-shadow',r).css('box-shadow',r);}
function SelectWidget(parent,options,width,editable,bg_color){var me=this;this.inp=$a(parent,'select');if(options)add_sel_options(this.inp,options);if(width)$y(this.inp,{width:width});this.set_width=function(w){$y(this.inp,{width:w})};this.set_options=function(o){add_sel_options(this.inp,o);}
this.inp.onchange=function(){if(me.onchange)me.onchange(this);}
return;}
function empty_select(s){if(s.custom_select){s.empty();return;}
if(s.inp)s=s.inp;if(s){var tmplen=s.length;for(var i=0;i<tmplen;i++)s.options[0]=null;}}
function sel_val(s){if(s.custom_select){return s.inp.value?s.inp.value:'';}
if(s.inp)s=s.inp;try{if(s.selectedIndex<s.options.length)return s.options[s.selectedIndex].value;else return'';}catch(err){return'';}}
function add_sel_options(s,list,sel_val,o_style){if(s.custom_select){s.set_options(list)
if(sel_val)s.inp.value=sel_val;return;}
if(s.inp)s=s.inp;for(var i=0,len=list.length;i<len;i++){var o=new Option(list[i],list[i],false,(list[i]==sel_val?true:false));if(o_style)$y(o,o_style);s.options[s.options.length]=o;}}
function cint(v,def){v=v+'';v=lstrip(v,['0']);v=parseInt(v);if(isNaN(v))v=def?def:0;return v;}
function validate_email(id){if(strip(id.toLowerCase()).search("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")==-1)return 0;else return 1;}
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
function $w(e,w){if(e&&e.style&&w)e.style.width=w;}
function $h(e,h){if(e&&e.style&&h)e.style.height=h;}
function $bg(e,w){if(e&&e.style&&w)e.style.backgroundColor=w;}
function $y(ele,s){if(ele&&s){for(var i in s)ele.style[i]=s[i];};return ele;}
function $yt(tab,r,c,s){var rmin=r;var rmax=r;if(r=='*'){rmin=0;rmax=tab.rows.length-1;}
if(r.search&&r.search('-')!=-1){r=r.split('-');rmin=cint(r[0]);rmax=cint(r[1]);}
var cmin=c;var cmax=c;if(c=='*'){cmin=0;cmax=tab.rows[0].cells.length-1;}
if(c.search&&c.search('-')!=-1){c=c.split('-');rmin=cint(c[0]);rmax=cint(c[1]);}
for(var ri=rmin;ri<=rmax;ri++){for(var ci=cmin;ci<=cmax;ci++)
$y($td(tab,ri,ci),s);}}
function set_style(txt){wn.dom.set_style(txt);}
function make_table(parent,nr,nc,table_width,widths,cell_style,table_style){var t=$a(parent,'table');t.style.borderCollapse='collapse';if(table_width)t.style.width=table_width;if(cell_style)t.cell_style=cell_style;for(var ri=0;ri<nr;ri++){var r=t.insertRow(ri);for(var ci=0;ci<nc;ci++){var c=r.insertCell(ci);if(ri==0&&widths&&widths[ci]){c.style.width=widths[ci];}
if(cell_style){for(var s in cell_style)c.style[s]=cell_style[s];}}}
t.append_row=function(){return append_row(this);}
if(table_style)$y(t,table_style);return t;}
function append_row(t,at,style){var r=t.insertRow(at?at:t.rows.length);if(t.rows.length>1){for(var i=0;i<t.rows[0].cells.length;i++){var c=r.insertCell(i);if(style)$y(c,style);}}
return r}
function $td(t,r,c){if(r<0)r=t.rows.length+r;if(c<0)c=t.rows[0].cells.length+c;return t.rows[r].cells[c];}
wn.urllib={get_arg:function(name){name=name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");var regexS="[\\?&]"+name+"=([^&#]*)";var regex=new RegExp(regexS);var results=regex.exec(window.location.href);if(results==null)
return"";else
return decodeURIComponent(results[1]);},get_dict:function(){var d={}
var t=window.location.href.split('?')[1];if(!t)return d;if(t.indexOf('#')!=-1)t=t.split('#')[0];if(!t)return d;t=t.split('&');for(var i=0;i<t.length;i++){var a=t[i].split('=');d[decodeURIComponent(a[0])]=decodeURIComponent(a[1]);}
return d;},get_base_url:function(){var url=window.location.href.split('#')[0].split('?')[0].split('app.html')[0];if(url.substr(url.length-1,1)=='/')url=url.substr(0,url.length-1)
return url},get_file_url:function(file_id){return repl('files/%(fn)s',{fn:file_id})}}
get_url_arg=wn.urllib.get_arg;get_url_dict=wn.urllib.get_dict;
/*
 *	lib/js/legacy/utils/handler.js
 */
function $c(command,args,callback,error,no_spinner,freeze_msg,btn){wn.request.call({args:$.extend(args,{cmd:command}),success:callback,error:error,btn:btn,freeze:freeze_msg,show_spinner:!no_spinner})}
function $c_obj(doclist,method,arg,callback,no_spinner,freeze_msg,btn){if(arg&&typeof arg!='string')arg=JSON.stringify(arg);args={cmd:'runserverobj',arg:arg,method:method};if(typeof doclist=='string')
args.doctype=doclist;else
args.docs=compress_doclist(doclist)
wn.request.call({args:args,success:callback,btn:btn,freeze:freeze_msg,show_spinner:!no_spinner});}
function $c_page(module,page,method,arg,callback,no_spinner,freeze_msg,btn){if(arg&&typeof arg!='string')arg=JSON.stringify(arg);wn.request.call({args:{cmd:module+'.page.'+page+'.'+page+'.'+method,arg:arg,method:method},success:callback,btn:btn,freeze:freeze_msg,show_spinner:!no_spinner});}
function $c_obj_csv(doclist,method,arg){var args={}
args.cmd='runserverobj';args.as_csv=1;args.method=method;args.arg=arg;if(doclist.substr)
args.doctype=doclist;else
args.docs=compress_doclist(doclist);open_url_post(wn.request.url,args);}
function open_url_post(URL,PARAMS,new_window){var temp=document.createElement("form");temp.action=URL;temp.method="POST";temp.style.display="none";if(new_window){temp.target='_blank';}
for(var x in PARAMS){var opt=document.createElement("textarea");opt.name=x;var val=PARAMS[x];if(typeof val!='string')
val=JSON.stringify(val);opt.value=val;temp.appendChild(opt);}
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
if(!msg_dialog.display)msg_dialog.show();var has_msg=msg_dialog.msg_area.innerHTML?1:0;var m=$a(msg_dialog.msg_area,'div','');if(has_msg)$y(m,{marginTop:'4px'});$dh(msg_dialog.msg_icon);if(msg.substr(0,6).toLowerCase()=='error:'){msg_dialog.msg_icon.src='images/lib/icons/error.gif';$di(msg_dialog.msg_icon);msg=msg.substr(6);}else if(msg.substr(0,8).toLowerCase()=='message:'){msg_dialog.msg_icon.src='images/lib/icons/application.gif';$di(msg_dialog.msg_icon);msg=msg.substr(8);}else if(msg.substr(0,3).toLowerCase()=='ok:'){msg_dialog.msg_icon.src='images/lib/icons/accept.gif';$di(msg_dialog.msg_icon);msg=msg.substr(3);}
m.innerHTML=replace_newlines(msg);if(m.offsetHeight>200){$y(m,{height:'200px',width:'400px',overflow:'auto'})}
msg_dialog.custom_onhide=callback;}
var growl_area;function show_alert(txt,id){if(!growl_area){if(!$('#dialog-container').length){$('<div id="dialog-container">').appendTo('body');}
growl_area=$a($i('dialog-container'),'div','',{position:'fixed',bottom:'8px',right:'8px',width:'320px',zIndex:10});}
var wrapper=$a(growl_area,'div','',{position:'relative'});var body=$a(wrapper,'div','notice');var c=$a(body,'i','icon-remove-sign',{cssFloat:'right',cursor:'pointer'});$(c).click(function(){$dh(this.wrapper)});c.wrapper=wrapper;var t=$a(body,'div','',{color:'#FFF'});$(t).html(txt);if(id){$(t).attr('id',id);}
$(wrapper).hide().fadeIn(1000);}
/*
 *	lib/js/legacy/utils/printElement.js
 */;(function(window,undefined){var document=window["document"];var $=window["jQuery"];$.fn["printElement"]=function(options){var mainOptions=$.extend({},$.fn["printElement"]["defaults"],options);if(mainOptions["printMode"]=='iframe'){if($.browser.opera||(/chrome/.test(navigator.userAgent.toLowerCase())))
mainOptions["printMode"]='popup';}
$("[id^='printElement_']").remove();return this.each(function(){var opts=$.meta?$.extend({},mainOptions,$(this).data()):mainOptions;_printElement($(this),opts);});};$.fn["printElement"]["defaults"]={"printMode":'iframe',"pageTitle":'',"overrideElementCSS":null,"printBodyOptions":{"styleToAdd":'padding:10px;margin:10px;',"classNameToAdd":''},"leaveOpen":false,"iframeElementOptions":{"styleToAdd":'border:none;position:absolute;width:0px;height:0px;bottom:0px;left:0px;',"classNameToAdd":''}};$.fn["printElement"]["cssElement"]={"href":'',"media":''};function _printElement(element,opts){var html=_getMarkup(element,opts);var popupOrIframe=null;var documentToWriteTo=null;if(opts["printMode"].toLowerCase()=='popup'){popupOrIframe=window.open('about:blank','printElementWindow','width=650,height=440,scrollbars=yes');documentToWriteTo=popupOrIframe.document;}
else{var printElementID="printElement_"+(Math.round(Math.random()*99999)).toString();var iframe=document.createElement('IFRAME');$(iframe).attr({style:opts["iframeElementOptions"]["styleToAdd"],id:printElementID,className:opts["iframeElementOptions"]["classNameToAdd"],frameBorder:0,scrolling:'no',src:'about:blank'});document.body.appendChild(iframe);documentToWriteTo=(iframe.contentWindow||iframe.contentDocument);if(documentToWriteTo.document)
documentToWriteTo=documentToWriteTo.document;iframe=document.frames?document.frames[printElementID]:document.getElementById(printElementID);popupOrIframe=iframe.contentWindow||iframe;}
focus();documentToWriteTo.open();documentToWriteTo.write(html);documentToWriteTo.close();_callPrint(popupOrIframe);};function _callPrint(element){if(element&&element["printPage"])
element["printPage"]();else
setTimeout(function(){_callPrint(element);},50);}
function _getElementHTMLIncludingFormElements(element){var $element=$(element);var elementHtml=$('<div></div>').append($element.clone()).html();return elementHtml;}
function _getBaseHref(){var port=(window.location.port)?':'+window.location.port:'';return window.location.protocol+'//'+window.location.hostname+port+window.location.pathname;}
function _getMarkup(element,opts){var $element=$(element);var elementHtml=_getElementHTMLIncludingFormElements(element);var html=new Array();html.push('<html><head><title>'+opts["pageTitle"]+'</title>');if(opts["overrideElementCSS"]){if(opts["overrideElementCSS"].length>0){for(var x=0;x<opts["overrideElementCSS"].length;x++){var current=opts["overrideElementCSS"][x];if(typeof(current)=='string')
html.push('<link type="text/css" rel="stylesheet" href="'+current+'" >');else
html.push('<link type="text/css" rel="stylesheet" href="'+current["href"]+'" media="'+current["media"]+'" >');}}}
else{$("link",document).filter(function(){return $(this).attr("rel").toLowerCase()=="stylesheet";}).each(function(){html.push('<link type="text/css" rel="stylesheet" href="'+$(this).attr("href")+'" media="'+$(this).attr('media')+'" >');});}
html.push('<base href="'+_getBaseHref()+'" />');html.push('</head><body style="'+opts["printBodyOptions"]["styleToAdd"]+'" class="'+opts["printBodyOptions"]["classNameToAdd"]+'">');html.push('<div class="'+$element.attr('class')+'">'+elementHtml+'</div>');html.push('<script type="text/javascript">function printPage(){focus();print();'+((!$.browser.opera&&!opts["leaveOpen"]&&opts["printMode"].toLowerCase()=='popup')?'close();':'')+'}</script>');html.push('</body></html>');return html.join('');};})(window);
/*
 *	lib/js/legacy/widgets/form/fields.js
 */
var no_value_fields=['Section Break','Column Break','HTML','Table','FlexTable','Button','Image'];var codeid=0;var code_editors={};function Field(){this.with_label=1;}
Field.prototype.make_body=function(){var ischk=(this.df.fieldtype=='Check'?1:0);if(this.parent)
this.wrapper=$a(this.parent,(this.with_label?'div':'span'));else
this.wrapper=document.createElement((this.with_label?'div':'span'));this.label_area=$a(this.wrapper,'div','',{margin:'0px 0px 2px 0px'});if(ischk&&!this.in_grid){this.input_area=$a(this.label_area,'span','',{marginRight:'4px'});this.disp_area=$a(this.label_area,'span','',{marginRight:'4px'});}
if(this.with_label){this.label_span=$a(this.label_area,'span','small')
this.label_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 4px'});$dh(this.label_icon);this.label_icon.src='images/lib/icons/error.gif';this.label_icon.title='Mandatory value needs to be entered';this.suggest_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 0px'});$dh(this.suggest_icon);this.suggest_icon.src='images/lib/icons/bullet_arrow_down.png';this.suggest_icon.title='With suggestions';}else{this.label_span=$a(this.label_area,'span','',{marginRight:'4px'})
$dh(this.label_area);}
if(!this.input_area){this.input_area=$a(this.wrapper,(this.with_label?'div':'span'));this.disp_area=$a(this.wrapper,(this.with_label?'div':'span'));}
if(this.in_grid){if(this.label_area)$dh(this.label_area);}else{this.input_area.className='input_area';$y(this.wrapper,{marginBottom:'9px'});this.set_description();}
if(this.onmake)this.onmake();}
Field.prototype.set_max_width=function(){var no_max=['Code','Text Editor','Text','Table','HTML']
if(this.wrapper&&this.layout_cell&&this.layout_cell.parentNode.cells&&this.layout_cell.parentNode.cells.length==1&&!in_list(no_max,this.df.fieldtype)){$y(this.wrapper,{paddingRight:'50%'});}}
Field.prototype.set_label=function(){if(this.with_label&&this.label_area&&this.label!=this.df.label){this.label_span.innerHTML=this.df.label;this.label=this.df.label;}}
Field.prototype.set_description=function(){if(this.df.description){var p=in_list(['Text Editor','Code','Check'],this.df.fieldtype)?this.label_area:this.wrapper;this.desc_area=$a(p,'div','help small','',this.df.description)
if(in_list(['Text Editor','Code'],this.df.fieldtype))
$(this.desc_area).addClass('help small');}}
Field.prototype.get_status=function(){if(this.in_filter)this.not_in_form=this.in_filter;if(this.not_in_form){return'Write';}
if(!this.df.permlevel)this.df.permlevel=0;var p=this.perm[this.df.permlevel];var ret;if(cur_frm.editable&&p&&p[WRITE])ret='Write';else if(p&&p[READ])ret='Read';else ret='None';if(this.df.fieldtype=='Binary')
ret='None';if(cint(this.df.hidden))
ret='None';if(ret=='Write'&&cint(cur_frm.doc.docstatus)>0)ret='Read';var a_o_s=cint(this.df.allow_on_submit);if(a_o_s&&(this.in_grid||(this.frm&&this.frm.not_in_container))){a_o_s=null;if(this.in_grid)a_o_s=this.grid.field.df.allow_on_submit;if(this.frm&&this.frm.not_in_container){a_o_s=cur_grid.field.df.allow_on_submit;}}
if(cur_frm.editable&&a_o_s&&cint(cur_frm.doc.docstatus)>0&&!this.df.hidden){tmp_perm=get_perm(cur_frm.doctype,cur_frm.docname,1);if(tmp_perm[this.df.permlevel]&&tmp_perm[this.df.permlevel][WRITE])ret='Write';}
return ret;}
Field.prototype.set_style_mandatory=function(add){if(add){$(this.txt?this.txt:this.input).addClass('input-mandatory');if(this.disp_area)$(this.disp_area).addClass('input-mandatory');}else{$(this.txt?this.txt:this.input).removeClass('input-mandatory');if(this.disp_area)$(this.disp_area).removeClass('input-mandatory');}}
Field.prototype.refresh_mandatory=function(){if(this.in_filter)return;if(this.df.reqd){if(this.label_area)this.label_area.style.color="#d22";this.set_style_mandatory(1);}else{if(this.label_area)this.label_area.style.color="#222";this.set_style_mandatory(0);}
this.refresh_label_icon()
this.set_reqd=this.df.reqd;}
Field.prototype.refresh_display=function(){if(!this.current_status||this.current_status!=this.disp_status){if(this.disp_status=='Write'){if(this.make_input&&(!this.input)){this.make_input();if(this.onmake_input)this.onmake_input();}
if(this.show)this.show()
else{$ds(this.wrapper);}
if(this.input){$ds(this.input_area);$dh(this.disp_area);if(this.input.refresh)this.input.refresh();}else{$dh(this.input_area);$ds(this.disp_area);}}else if(this.disp_status=='Read'){if(this.show)this.show()
else{$ds(this.wrapper);}
$dh(this.input_area);$ds(this.disp_area);}else{if(this.hide)this.hide();else $dh(this.wrapper);}
this.current_status=this.disp_status;}}
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
var set_val=val;if(this.validate)set_val=this.validate(val);_f.set_value(this.doctype,this.docname,this.df.fieldname,set_val);this.value=val;}
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
function DataField(){}DataField.prototype=new Field();DataField.prototype.make_input=function(){var me=this;this.input=$a_input(this.input_area,this.df.fieldtype=='Password'?'password':'text');this.get_value=function(){var v=this.input.value;if(this.validate)
v=this.validate(v);return v;}
this.input.name=this.df.fieldname;$(this.input).change(function(){me.set_value(me.get_value?me.get_value():$(this.input).val());});this.set_value=function(val){if(!me.last_value)me.last_value='';if(me.validate){val=me.validate(val);me.input.value=val==undefined?'':val;}
me.set(val);if(me.format_input)
me.format_input();if(in_list(['Currency','Float','Int'],me.df.fieldtype)){if(flt(me.last_value)==flt(val)){me.last_value=val;return;}}
me.last_value=val;me.run_trigger();}
this.input.set_input=function(val){if(val==null)val='';me.input.value=val;if(me.format_input)me.format_input();}
if(this.df.options=='Suggest'){if(this.suggest_icon)$di(this.suggest_icon);$(me.input).autocomplete({source:function(request,response){wn.call({method:'webnotes.widgets.search.search_link',args:{'txt':request.term,'dt':me.df.options,'query':repl('SELECT DISTINCT `%(fieldname)s` FROM \
       `tab%(dt)s` WHERE `%(fieldname)s` LIKE "%s" LIMIT 50',{fieldname:me.df.fieldname,dt:me.df.parent})},callback:function(r){response(r.results);}});},select:function(event,ui){me.set(ui.item.value);}});}}
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
var datepicker_active=0;function DateField(){}DateField.prototype=new Field();DateField.prototype.make_input=function(){var me=this;this.user_fmt=sys_defaults.date_format;if(!this.user_fmt)this.user_fmt='dd-mm-yy';this.input=$a(this.input_area,'input');$(this.input).datepicker({dateFormat:me.user_fmt.replace('yyyy','yy'),altFormat:'yy-mm-dd',changeYear:true,beforeShow:function(input,inst){datepicker_active=1},onClose:function(dateText,inst){datepicker_active=0;if(_f.cur_grid_cell)
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
return v;};function LinkField(){}LinkField.prototype=new Field();LinkField.prototype.make_input=function(){var me=this;if(me.df.no_buttons){this.txt=$a(this.input_area,'input');this.input=this.txt;}else{makeinput_popup(this,'icon-search','icon-play','icon-plus');me.setup_buttons();me.onrefresh=function(){if(me.can_create&&cur_frm.doc.docstatus==0)
$(me.btn2).css('display','inline-block');else $dh(me.btn2);}}
me.txt.field_object=this;me.input.set_input=function(val){if(val==undefined)val='';me.txt.value=val;}
me.get_value=function(){return me.txt.value;}
$(me.txt).autocomplete({source:function(request,response){wn.call({method:'webnotes.widgets.search.search_link',args:{'txt':request.term,'dt':me.df.options,'query':me.get_custom_query()},callback:function(r){response(r.results);},});},select:function(event,ui){me.set_input_value(ui.item.value);}}).data('autocomplete')._renderItem=function(ul,item){return $('<li></li>').data('item.autocomplete',item).append(repl('<a>%(label)s<br><span style="font-size:10px">%(info)s</span></a>',item)).appendTo(ul);};$(this.txt).change(function(){var val=$(this).val();me.set_input_value_executed=false;if(!val){if(selector&&selector.display)
return;me.set_input_value('');}else{setTimeout(function(){if(!me.set_input_value_executed){me.set_input_value(val);}},1000);}})}
LinkField.prototype.get_custom_query=function(){this.set_get_query();if(this.get_query){if(cur_frm)
var doc=locals[cur_frm.doctype][cur_frm.docname];return this.get_query(doc,this.doctype,this.docname);}}
LinkField.prototype.setup_buttons=function(){var me=this;me.btn.onclick=function(){selector.set(me,me.df.options,me.df.label);selector.show(me.txt);}
if(me.btn1)me.btn1.onclick=function(){if(me.txt.value&&me.df.options){loaddoc(me.df.options,me.txt.value);}}
me.can_create=0;if((!me.not_in_form)&&in_list(profile.can_create,me.df.options)){me.can_create=1;me.btn2.onclick=function(){var on_save_callback=function(new_rec){if(new_rec){var d=_f.calling_doc_stack.pop();locals[d[0]][d[1]][me.df.fieldname]=new_rec;me.refresh();if(me.grid)me.grid.refresh();me.run_trigger();}}
_f.calling_doc_stack.push([me.doctype,me.docname]);new_doc(me.df.options,me.on_new,1,on_save_callback,me.doctype,me.docname,me.frm.not_in_container);}}else{$dh(me.btn2);$y($td(me.tab,0,2),{width:'0px'});}}
LinkField.prototype.set_input_value=function(val){var me=this;me.set_input_value_executed=true;var from_selector=false;if(selector&&selector.display)from_selector=true;me.refresh_label_icon();if(me.not_in_form){$(this.txt).val(val);return;}
if(cur_frm){if(val==locals[me.doctype][me.docname][me.df.fieldname]){me.run_trigger();return;}}
me.set(val);if(_f.cur_grid_cell)
_f.cur_grid_cell.grid.cell_deselect();if(locals[me.doctype][me.docname][me.df.fieldname]&&!val){me.run_trigger();return;}
if(val){me.validate_link(val,from_selector);}}
LinkField.prototype.validate_link=function(val,from_selector){var me=this;var fetch='';if(cur_frm.fetch_dict[me.df.fieldname])
fetch=cur_frm.fetch_dict[me.df.fieldname].columns.join(', ');$c('webnotes.widgets.form.utils.validate_link',{'value':val,'options':me.df.options,'fetch':fetch},function(r,rt){if(r.message=='Ok'){if($(me.txt).val()!=val){if((me.grid&&!from_selector)||(!me.grid)){$(me.txt).val(val);}}
if(r.fetch_values)
me.set_fetch_values(r.fetch_values);me.run_trigger();}else{var astr='';if(in_list(profile.can_create,me.df.options))astr=repl('<br><br><span class="link_type" onclick="newdoc(\'%(dt)s\')">Click here</span> to create a new %(dtl)s',{dt:me.df.options,dtl:get_doctype_label(me.df.options)})
msgprint(repl('error:<b>%(val)s</b> is not a valid %(dt)s.<br><br>You must first create a new %(dt)s <b>%(val)s</b> and then select its value. To find an existing %(dt)s, click on the magnifying glass next to the field.%(add)s',{val:me.txt.value,dt:get_doctype_label(me.df.options),add:astr}));me.txt.value='';me.set('');}});}
LinkField.prototype.set_fetch_values=function(fetch_values){var fl=cur_frm.fetch_dict[this.df.fieldname].fields;var changed_fields=[];for(var i=0;i<fl.length;i++){if(locals[this.doctype][this.docname][fl[i]]!=fetch_values[i]){locals[this.doctype][this.docname][fl[i]]=fetch_values[i];if(!this.grid){refresh_field(fl[i]);changed_fields.push(fl[i]);}}}
for(i=0;i<changed_fields.length;i++){if(cur_frm.fields_dict[changed_fields[i]])
cur_frm.fields_dict[changed_fields[i]].run_trigger();}
if(this.grid)this.grid.refresh();}
LinkField.prototype.set_get_query=function(){if(this.get_query)return;if(this.grid){var f=this.grid.get_field(this.df.fieldname);if(f.get_query)this.get_query=f.get_query;}}
LinkField.prototype.set_disp=function(val){var t=null;if(val)t="<a href=\'javascript:loaddoc(\""+this.df.options+"\", \""+val+"\")\'>"+val+"</a>";this.set_disp_html(t);}
function IntField(){}IntField.prototype=new DataField();IntField.prototype.validate=function(v){if(isNaN(parseInt(v)))return null;return cint(v);};IntField.prototype.format_input=function(){if(this.input.value==null)this.input.value='';}
function FloatField(){}FloatField.prototype=new DataField();FloatField.prototype.validate=function(v){var v=parseFloat(v);if(isNaN(v))
return null;return v;};FloatField.prototype.format_input=function(){if(this.input.value==null)this.input.value='';}
function CurrencyField(){}CurrencyField.prototype=new DataField();CurrencyField.prototype.format_input=function(){var v=fmt_money(this.input.value);if(this.not_in_form){if(!flt(this.input.value))v='';}
this.input.value=v;}
CurrencyField.prototype.validate=function(v){if(v==null||v=='')
return 0;return flt(v,2);}
CurrencyField.prototype.set_disp=function(val){var v=fmt_money(val);this.set_disp_html(v);}
CurrencyField.prototype.onmake_input=function(){if(!this.input)return;this.input.onfocus=function(){if(flt(this.value)==0)this.select();}}
function CheckField(){}CheckField.prototype=new Field();CheckField.prototype.validate=function(v){var v=parseInt(v);if(isNaN(v))return 0;return v;};CheckField.prototype.onmake=function(){this.checkimg=$a(this.disp_area,'div');var img=$a(this.checkimg,'img');img.src='images/lib/ui/tick.gif';$dh(this.checkimg);}
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
$a(this.widgets['Description'],'div','help small','',this.field.df.description);}
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
this.set_attach_options();me.options_list=me.df.options?me.df.options.split('\n'):[''];empty_select(this.input);if(me.in_filter&&me.options_list[0]!=''){me.options_list=add_lists([''],me.options_list);}
add_sel_options(this.input,me.options_list);}
this.onrefresh=function(){this.refresh_options();if(this.not_in_form){this.input.value='';return;}
if(_f.get_value)
var v=_f.get_value(this.doctype,this.docname,this.df.fieldname);else{if(this.options_list&&this.options_list.length)
var v=this.options_list[0];else
var v=null;}
this.input.set_input(v);}
this.input.set_input=function(v){if(!v){if(!me.input.multiple){if(me.docname){if(me.options_list&&me.options_list.length){me.set(me.options_list[0]);me.input.value=me.options_list[0];}else{me.input.value='';}}}}else{if(me.options_list){if(me.input.multiple){for(var i=0;i<me.input.options.length;i++){me.input.options[i].selected=0;if(me.input.options[i].value&&inList(typeof(v)=='string'?v.split(","):v,me.input.options[i].value))
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
function makeinput_popup(me,iconsrc,iconsrc1,iconsrc2){var icon_style={cursor:'pointer',width:'16px',verticalAlign:'middle',marginBottom:'-3px'};me.input=$a(me.input_area,'div');if(!me.not_in_form)
$y(me.input,{width:'80%'});me.input.set_width=function(w){$y(me.input,{width:(w-2)+'px'});}
var tab=$a(me.input,'table');me.tab=tab;$y(tab,{width:'100%',borderCollapse:'collapse',tableLayout:'fixed'});var c0=tab.insertRow(0).insertCell(0);var c1=tab.rows[0].insertCell(1);$y(c1,{width:'20px'});me.txt=$a($a($a(c0,'div','',{paddingRight:'8px'}),'div'),'input','',{width:'100%'});me.btn=$a(c1,'i',iconsrc,icon_style)
if(iconsrc1)
me.btn.setAttribute('title','Search');else
me.btn.setAttribute('title','Select Date');if(iconsrc1){var c2=tab.rows[0].insertCell(2);$y(c2,{width:'20px'});me.btn1=$a(c2,'i',iconsrc1,icon_style)
me.btn1.setAttribute('title','Open Link');}
if(iconsrc2){var c3=tab.rows[0].insertCell(3);$y(c3,{width:'20px'});me.btn2=$a(c3,'i',iconsrc2,icon_style)
me.btn2.setAttribute('title','Create New');$dh(me.btn2);}
if(me.df.colour)
me.txt.style.background='#'+me.df.colour.split(':')[1];me.txt.name=me.df.fieldname;me.setdisabled=function(tf){me.txt.disabled=tf;}}
var tmpid=0;_f.ButtonField=function(){};_f.ButtonField.prototype=new Field();_f.ButtonField.prototype.with_label=0;_f.ButtonField.prototype.init=function(){this.prev_button=null;if(!this.frm)return;if(cur_frm&&cur_frm.fields[cur_frm.fields.length-1]&&cur_frm.fields[cur_frm.fields.length-1].df.fieldtype=='Button'){this.make_body=function(){this.prev_button=cur_frm.fields[cur_frm.fields.length-1];if(!this.prev_button.prev_button){this.prev_button.button_area=$a(this.prev_button.input_area,'span');}
this.wrapper=this.prev_button.wrapper;this.input_area=this.prev_button.input_area;this.disp_area=this.prev_button.disp_area;this.button_area=$a(this.prev_button.input_area,'span');}}}
_f.ButtonField.prototype.make_input=function(){var me=this;if(!this.prev_button){$y(this.input_area,{marginTop:'4px',marginBottom:'4px'});}
if(!this.button_area)
this.button_area=$a(this.input_area,'span','',{marginRight:'4px'});this.input=$btn(this.button_area,me.df.label,null,{fontWeight:'bold'},null,1)
$(this.input).click(function(){if(me.not_in_form)return;if(cur_frm.cscript[me.df.fieldname]&&(!me.in_filter)){cur_frm.runclientscript(me.df.fieldname,me.doctype,me.docname);}else{cur_frm.runscript(me.df.options,me);}});}
_f.ButtonField.prototype.hide=function(){$dh(this.button_area);};_f.ButtonField.prototype.show=function(){$ds(this.button_area);};_f.ButtonField.prototype.set=function(v){};_f.ButtonField.prototype.set_disp=function(val){}
function make_field(docfield,doctype,parent,frm,in_grid,hide_label){switch(docfield.fieldtype.toLowerCase()){case'data':var f=new DataField();break;case'password':var f=new DataField();break;case'int':var f=new IntField();break;case'float':var f=new FloatField();break;case'currency':var f=new CurrencyField();break;case'read only':var f=new ReadOnlyField();break;case'link':var f=new LinkField();break;case'date':var f=new DateField();break;case'time':var f=new TimeField();break;case'html':var f=new HTMLField();break;case'check':var f=new CheckField();break;case'text':var f=new TextField();break;case'small text':var f=new TextField();break;case'select':var f=new SelectField();break;case'button':var f=new _f.ButtonField();break;case'code':var f=new _f.CodeField();break;case'text editor':var f=new _f.CodeField();break;case'table':var f=new _f.TableField();break;case'section break':var f=new _f.SectionBreak();break;case'column break':var f=new _f.ColumnBreak();break;case'image':var f=new _f.ImageField();break;}
f.parent=parent;f.doctype=doctype;f.df=docfield;f.perm=frm?frm.perm:[[1,1,1]];if(_f)
f.col_break_width=_f.cur_col_break_width;if(in_grid){f.in_grid=true;f.with_label=0;}
if(hide_label){f.with_label=0;}
if(frm){f.frm=frm;if(parent)
f.layout_cell=parent.parentNode;}
if(f.init)f.init();f.make_body();return f;}
/*
 *	lib/js/wn/ui/appframe.js
 */
wn.ui.AppFrame=Class.extend({init:function(parent,title){this.buttons={};this.$w=$('<div></div>').appendTo(parent);this.$titlebar=$('<div class="appframe-titlebar">\
   <span class="appframe-title"></span>\
   <span class="close">&times;</span>\
  </div>').appendTo(this.$w);this.$w.find('.close').click(function(){window.history.back();})
if(title)this.title(title);},title:function(txt){this.$titlebar.find('.appframe-title').html(txt);},add_button:function(label,click,icon){if(!this.$w.find('.appframe-toolbar').length)
this.$w.append('<div class="appframe-toolbar"></div>');args={label:label,icon:''};if(icon){args.icon='<i class="'+icon+'"></i>';}
this.buttons[label]=$(repl('<button class="btn btn-small">\
   %(icon)s %(label)s</button>',args)).click(click).appendTo(this.$w.find('.appframe-toolbar'));return this.buttons[label];},clear_buttons:function(){this.$w.find('.appframe-toolbar').empty();}});wn.ui.make_app_page=function(opts){if(opts.single_column){$(opts.parent).html('<div class="layout-wrapper layout-wrapper-appframe">\
   <div class="layout-appframe"></div>\
   <div class="layout-main"></div>\
  </div>');}else{$(opts.parent).html('<div class="layout-wrapper layout-wrapper-background">\
   <div class="layout-appframe"></div>\
   <div class="layout-main-section"></div>\
   <div class="layout-side-section"></div>\
   <div class="clear"></div>\
  </div>');}
opts.parent.appframe=new wn.ui.AppFrame($(opts.parent).find('.layout-appframe'));if(opts.title)opts.parent.appframe.title(opts.title);}
/*
 *	lib/js/wn/ui/dialog.js
 */
wn.widgets.FieldGroup=function(){this.first_button=false;this.make_fields=function(body,fl){if(!window.make_field){wn.require('css/fields.css');wn.require('js/fields.js');}
$y(this.body,{padding:'11px'});this.fields_dict={};for(var i=0;i<fl.length;i++){var df=fl[i];if(!df.fieldname&&df.label){df.fieldname=df.label.replace(/ /g,'_').toLowerCase();}
var div=$a(body,'div','',{margin:'6px 0px'})
f=make_field(df,null,div,null);f.not_in_form=1;this.fields_dict[df.fieldname]=f
f.refresh();if(df.fieldtype=='Button'&&!this.first_button){$(f.input).addClass('btn-info');this.first_button=true;}}}
this.get_values=function(){var ret={};var errors=[];for(var key in this.fields_dict){var f=this.fields_dict[key];var v=f.get_value?f.get_value():null;if(f.df.reqd&&!v)
errors.push(f.df.label+' is mandatory');if(v)ret[f.df.fieldname]=v;}
if(errors.length){msgprint('<b>Please check the following Errors</b>\n'+errors.join('\n'));return null;}
return ret;}
this.set_value=function(key,val){var f=this.fields_dict[key];if(f){f.set_input(val);f.refresh_mandatory();}}
this.set_values=function(dict){for(var key in dict){if(this.fields_dict[key]){this.set_value(key,dict[key]);}}}
this.clear=function(){for(key in this.fields_dict){var f=this.fields_dict[key];if(f){f.set_input(f.df['default']||'');}}}}
wn.widgets.Dialog=function(opts){this.opts=opts;this.display=false;this.make=function(opts){if(opts)
this.opts=opts;if(!this.opts.width)this.opts.width=480;if(!$('#dialog-container').length){$('<div id="dialog-container">').appendTo('body');}
this.wrapper=$('<div class="dialog_wrapper">').appendTo('#dialog-container').get(0);if(this.opts.width)
this.wrapper.style.width=this.opts.width+'px';this.make_head();this.body=$a(this.wrapper,'div','dialog_body');if(this.opts.fields)
this.make_fields(this.body,this.opts.fields);}
this.make_head=function(){var me=this;this.appframe=new wn.ui.AppFrame(this.wrapper);this.appframe.$titlebar.find('.close').unbind('click').click(function(){if(me.oncancel)me.oncancel();me.hide();});this.set_title(this.opts.title);}
this.set_title=function(t){this.appframe.$titlebar.find('.appframe-title').html(t||'');}
this.set_postion=function(){this.wrapper.style.left=(($(window).width()-cint(this.wrapper.style.width))/2)+'px';this.wrapper.style.top=($(window).scrollTop()+60)+'px';top_index++;$y(this.wrapper,{zIndex:top_index});}
this.show=function(){if(this.display)return;this.set_postion()
$ds(this.wrapper);freeze();this.display=true;cur_dialog=this;if(this.onshow)this.onshow();}
this.hide=function(){if(this.onhide)this.onhide();unfreeze();$dh(this.wrapper);this.display=false;cur_dialog=null;}
this.no_cancel=function(){this.appframe.$titlebar.find('.close').toggle(false);}
if(opts)this.make();}
wn.widgets.Dialog.prototype=new wn.widgets.FieldGroup();wn.provide('wn.ui');wn.ui.Dialog=wn.widgets.Dialog
$(document).bind('keydown',function(e){if(cur_dialog&&!cur_dialog.no_cancel_flag&&e.which==27){cur_dialog.hide();}});
/*
 *	lib/js/wn/ui/button.js
 */
wn.ui.Button=function(args){var me=this;$.extend(this,{make:function(){me.btn=wn.dom.add(args.parent,'button','btn btn-small '+(args.css_class||''));me.btn.args=args;me.loading_img=wn.dom.add(me.btn.args.parent,'img','',{margin:'0px 4px -2px 4px',display:'none'});me.loading_img.src='images/lib/ui/button-load.gif';me.btn.innerHTML=args.label;me.btn.user_onclick=args.onclick;$(me.btn).bind('click',function(){if(!this.disabled&&this.user_onclick)
this.user_onclick(this);})
me.btn.set_working=me.set_working;me.btn.done_working=me.done_working;if(me.btn.args.style)
wn.dom.css(me.btn,args.style);},set_working:function(){me.btn.disabled='disabled';$(me.loading_img).css('display','inline');},done_working:function(){me.btn.disabled=false;$(me.loading_img).toggle(false);}});this.make();}
/*
 *	lib/js/wn/ui/search.js
 */
wn.ui.Search=Class.extend({init:function(opts){$.extend(this,opts);var me=this;wn.model.with_doctype(this.doctype,function(r){me.make();me.dialog.show();me.list.$w.find('.list-filters input[type="text"]').focus();});},make:function(){var me=this;this.dialog=new wn.ui.Dialog({title:this.doctype+' Search',width:500});this.list=new wn.ui.Listing({parent:$(this.dialog.body),appframe:this.dialog.appframe,new_doctype:this.doctype,doctype:this.doctype,method:'webnotes.widgets.doclistview.get',show_filters:true,style:'compact',get_args:function(){if(me.query){me.page_length=50;return{query:me.query}}else{return{doctype:me.doctype,fields:['`tab'+me.doctype+'`.name'],filters:me.list.filter_list.get_filters(),docstatus:['0','1']}}},render_row:function(parent,data){$ln=$('<a style="cursor: pointer;" data-name="'+data.name+'">'
+data.name+'</a>').appendTo(parent).click(function(){var val=$(this).attr('data-name');me.dialog.hide();if(me.callback)
me.callback(val);else
wn.set_route('Form',me.doctype,val);});}});this.list.filter_list.add_filter('name','like');this.list.run();}})
/*
 *	lib/js/wn/ui/tree.js
 */
wn.ui.Tree=Class.extend({init:function(args){$.extend(this,args);this.nodes={};this.$w=$('<div class="tree">').appendTo(this.parent);this.rootnode=new wn.ui.TreeNode({tree:this,parent:this.$w,label:this.label,expandable:true});this.set_style();},set_style:function(){wn.dom.set_style("\
   .tree li { list-style: none; }\
   .tree ul { margin-top: 2px; }\
   .tree-link { cursor: pointer; }\
  ")}})
wn.ui.TreeNode=Class.extend({init:function(args){var me=this;$.extend(this,args);this.loaded=false;this.expanded=false;this.tree.nodes[this.label]=this;this.$a=$('<a class="tree-link">').click(function(){if(me.expandable&&me.tree.method&&!me.loaded){me.load()}else{me.selectnode();}
if(me.tree.click)me.tree.click(this);}).bind('reload',function(){me.reload();}).data('label',this.label).appendTo(this.parent);if(this.expandable){this.$a.append('<i class="icon-folder-close"></i> '+this.label);}else{this.$a.append('<i class="icon-file"></i> '+this.label);}
if(this.tree.onrender){this.tree.onrender(this);}},selectnode:function(){if(this.$ul){this.$ul.toggle();this.$a.find('i').removeClass();if(this.$ul.css('display').toLowerCase()=='block'){this.$a.find('i').addClass('icon-folder-open');}else{this.$a.find('i').addClass('icon-folder-close');}}
this.tree.$w.find('a.selected').removeClass('selected');this.$a.toggleClass('selected');this.expanded=!this.expanded;},reload:function(){if(this.expanded){this.$a.click();}
if(this.$ul){this.$ul.empty();}
this.load();},addnode:function(data){if(!this.$ul){this.$ul=$('<ul>').toggle(false).appendTo(this.parent);}
return new wn.ui.TreeNode({tree:this.tree,parent:$('<li>').appendTo(this.$ul),label:data.value,expandable:data.expandable,data:data});},load:function(){var me=this;args=$.extend(this.tree.args,{parent:this.label});$(me.$a).set_working();wn.call({method:this.tree.method,args:args,callback:function(r){$(me.$a).done_working();$.each(r.message,function(i,v){node=me.addnode(v);node.$a.data('node-data',v);});me.loaded=true;me.selectnode();}})}})
/*
 *	lib/js/wn/upload.js
 */
wn.upload={make:function(opts){var id=wn.dom.set_unique_id();$(opts.parent).append(repl('<iframe id="%(id)s" name="%(id)s" src="blank.html" \
    style="width:0px; height:0px; border:0px"></iframe>\
   <form method="POST" enctype="multipart/form-data" \
    action="%(action)s" target="%(id)s">\
    <input type="file" name="filedata" /><br><br>\
    <input type="submit" class="btn btn-small" value="Upload" />\
   </form>',{id:id,action:wn.request.url}));opts.args.cmd='uploadfile';opts.args._id=id;for(key in opts.args){if(opts.args[key]){$('<input type="hidden">').attr('name',key).attr('value',opts.args[key]).appendTo($(opts.parent).find('form'));}}
$('#'+id).get(0).callback=opts.callback},callback:function(id,file_id,args){$('#'+id).get(0).callback(file_id,args);}}
/*
 *	lib/js/wn/misc/about.js
 */
wn.provide('wn.ui.misc');wn.ui.misc.about=function(){if(!wn.ui.misc.about_dialog){var d=new wn.widgets.Dialog({title:'About wnframework'})
$(d.body).html(repl("<div style='padding: 20px'<p><b>Application Name:</b> %(name)s</p>\
  <p><b>Version:</b> %(version)s</p>\
  <p><b>License:</b> %(license)s</p>\
  <p><b>Source Code:</b> %(source)s</p>\
  <p><b>Publisher:</b> %(publisher)s</p>\
  <p><b>Copyright:</b> %(copyright)s</p></div>",wn.app));wn.ui.misc.about_dialog=d;}
wn.ui.misc.about_dialog.show();}
/*
 *	lib/js/wn/views/doclistview.js
 */
wn.provide('wn.views.doclistview');wn.provide('wn.doclistviews');wn.views.doclistview.show=function(doctype){var page_name=wn.get_route_str();if(wn.pages[page_name]){wn.container.change_to(wn.pages[page_name]);}else{var route=wn.get_route();if(route[1]){wn.model.with_doctype(route[1],function(r){if(r&&r['403']){return;}
new wn.views.DocListView(route[1]);});}}}
wn.views.DocListView=wn.ui.Listing.extend({init:function(doctype){this.doctype=doctype;this.label=get_doctype_label(doctype);this.label=(this.label.toLowerCase().substr(-4)=='list')?this.label:(this.label+' List');this.make_page();this.setup();},make_page:function(){var me=this;var page_name=wn.get_route_str();var page=wn.container.add_page(page_name);wn.container.change_to(page_name);this.$page=$(page);this.$page.html('<div class="layout-wrapper layout-wrapper-background">\
   <div class="appframe-area"></div>\
   <div class="layout-main-section">\
    <div class="wnlist-area"><div class="help">Loading...</div></div>\
   </div>\
   <div class="layout-side-section">\
    <div class="show-docstatus hide" style="margin-bottom: 19px">\
     <h4>Show</h4>\
     <div><input data-docstatus="0" type="checkbox" checked="checked" /> Drafts</div>\
     <div><input data-docstatus="1" type="checkbox" checked="checked" /> Submitted</div>\
     <div><input data-docstatus="2" type="checkbox" /> Cancelled</div>\
    </div>\
   </div>\
   <div style="clear: both"></div>\
  </div>');this.appframe=new wn.ui.AppFrame(this.$page.find('.appframe-area'));wn.views.breadcrumbs($('<span class="breadcrumb-area">').appendTo(this.appframe.$titlebar),locals.DocType[this.doctype].module,this.doctype);},setup:function(){var me=this;me.can_delete=wn.model.can_delete(me.doctype);me.meta=locals.DocType[me.doctype];me.$page.find('.wnlist-area').empty(),me.setup_docstatus_filter();me.setup_listview();me.init_list();me.init_stats();me.make_report_button();me.add_delete_option();},make_report_button:function(){var me=this;if(wn.boot.profile.can_get_report.indexOf(this.doctype)!=-1){this.appframe.add_button('Build Report',function(){wn.set_route('Report2',me.doctype);},'icon-th')}},setup_docstatus_filter:function(){var me=this;this.can_submit=$.map(locals.DocPerm,function(d){if(d.parent==me.meta.name&&d.submit)return 1
else return null;}).length;if(this.can_submit){this.$page.find('.show-docstatus').removeClass('hide');this.$page.find('.show-docstatus input').click(function(){me.run();})}},setup_listview:function(){if(this.meta.__listjs){eval(this.meta.__listjs);this.listview=new wn.doclistviews[this.doctype](this);}else{this.listview=new wn.views.ListView(this);}
this.listview.parent=this;this.wrapper=this.$page.find('.wnlist-area');this.page_length=20;this.allow_delete=true;},init_list:function(auto_run){var me=this;this.make({method:'webnotes.widgets.doclistview.get',get_args:this.get_args,parent:this.wrapper,start:0,page_length:this.page_length,show_filters:true,show_grid:true,new_doctype:this.doctype,allow_delete:this.allow_delete,no_result_message:this.make_no_result(),columns:this.listview.fields});$(this.wrapper).find('button[list_view_doc="'+me.doctype+'"]').click(function(){me.make_new_doc(me.doctype);});if((auto_run!==false)&&(auto_run!==0))this.run();},make_no_result:function(){var no_result_message=repl('<div class="well">\
  <p>No %(doctype_label)s found</p>\
  %(description)s\
  <hr>\
  <p><button class="btn btn-info btn-small" list_view_doc="%(doctype)s">\
   Make a new %(doctype_label)s</button>\
  </p></div>',{doctype_label:get_doctype_label(this.doctype),doctype:this.doctype,description:wn.markdown(locals.DocType[this.doctype].description||''),});return no_result_message;},render_row:function(row,data){data.doctype=this.doctype;this.listview.render(row,data,this);},get_query_fields:function(){return this.listview.fields;},get_args:function(){return{doctype:this.doctype,fields:this.get_query_fields(),filters:this.filter_list.get_filters(),docstatus:this.can_submit?$.map(this.$page.find('.show-docstatus :checked'),function(inp){return $(inp).attr('data-docstatus')}):[],order_by:this.listview.order_by||undefined,group_by:this.listview.group_by||undefined,}},add_delete_option:function(){var me=this;if(this.can_delete){this.add_button('Delete',function(){me.delete_items();},'icon-remove')}},delete_items:function(){var me=this;var dl=$.map(me.$page.find('.list-delete:checked'),function(e){return $(e).data('name');});if(!dl.length)
return;if(!confirm('This is PERMANENT action and you cannot undo. Continue?')){return;}
me.set_working(true);wn.call({method:'webnotes.widgets.doclistview.delete_items',args:{items:dl,doctype:me.doctype},callback:function(){me.set_working(false);me.refresh();}})},init_stats:function(){var me=this
wn.call({method:'webnotes.widgets.doclistview.get_stats',args:{stats:me.listview.stats,doctype:me.doctype},callback:function(r){$.each(me.listview.stats,function(i,v){me.render_stat(v,r.message[v]);});if(me.listview.stats.length){$('<button class="btn btn-small"><i class="refresh"></i> Refresh</button>').click(function(){me.reload_stats();}).appendTo($('<div class="stat-wrapper">').appendTo(me.$page.find('.layout-side-section')))}}});},render_stat:function(field,stat){var me=this;if(!stat||!stat.length){if(field=='_user_tags'){this.$page.find('.layout-side-section').append('<div class="stat-wrapper"><h4>Tags</h4>\
      <div class="help small"><i>No records tagged.</i><br><br> \
      To add a tag, open the document and click on \
      "Add Tag" on the sidebar</div></div>');}
return;}
var label=wn.meta.docfield_map[this.doctype][field]?wn.meta.docfield_map[this.doctype][field].label:field;if(label=='_user_tags')label='Tags';var $w=$('<div class="stat-wrapper">\
   <h4>'+label+'</h4>\
   <div class="stat-grid">\
   </div>\
  </div>');stat=stat.sort(function(a,b){return b[1]-a[1]});var sum=0;$.each(stat,function(i,v){sum=sum+v[1];})
$.each(stat,function(i,v){me.render_stat_item(i,v,sum,field).appendTo($w.find('.stat-grid'));});$w.appendTo(this.$page.find('.layout-side-section'));},render_stat_item:function(i,v,max,field){var me=this;var args={}
args.label=v[0];args.width=flt(v[1])/max*100;args.count=v[1];args.field=field;$item=$(repl('<div class="stat-item">\
   <div class="stat-bar" style="width: %(width)s%"></div>\
   <div class="stat-label">\
    <a href="#" data-label="%(label)s" data-field="%(field)s">\
     %(label)s</a> \
    (%(count)s)</div>\
  </div>',args));this.setup_stat_item_click($item);return $item;},reload_stats:function(){this.$page.find('.layout-side-section .stat-wrapper').remove();this.init_stats();},setup_stat_item_click:function($item){var me=this;$item.find('a').click(function(){var fieldname=$(this).attr('data-field');var label=$(this).attr('data-label');me.set_filter(fieldname,label);return false;});},set_filter:function(fieldname,label){var filter=this.filter_list.get_filter(fieldname);if(filter){var v=filter.field.get_value();if(v.indexOf(label)!=-1){return false;}else{if(fieldname=='_user_tags'){this.filter_list.add_filter(fieldname,'like','%'+label);}else{filter.set_values(fieldname,'in',v+', '+label);}}}else{if(fieldname=='_user_tags'){this.filter_list.add_filter(fieldname,'like','%'+label);}else{this.filter_list.add_filter(fieldname,'=',label);}}
this.run();}});wn.views.ListView=Class.extend({init:function(doclistview){this.doclistview=doclistview;this.doctype=doclistview.doctype;var t="`tab"+this.doctype+"`.";this.fields=[t+'name',t+'owner',t+'docstatus',t+'_user_tags',t+'modified'];this.stats=['_user_tags'];this.show_hide_check_column();},columns:[{width:'3%',content:'check'},{width:'4%',content:'avatar'},{width:'3%',content:'docstatus',css:{"text-align":"center"}},{width:'35%',content:'name'},{width:'40%',content:'tags',css:{'color':'#aaa'}},{width:'15%',content:'modified',css:{'text-align':'right','color':'#222'}}],render_column:function(data,parent,opts){var me=this;if(opts.css){$.each(opts.css,function(k,v){$(parent).css(k,v)});}
if(opts.content.indexOf&&opts.content.indexOf('+')!=-1){$.map(opts.content.split('+'),function(v){me.render_column(data,parent,{content:v});});return;}
if(typeof opts.content=='function'){opts.content(parent,data,me);}
else if(opts.content=='name'){$(parent).append(repl('<a href="#!Form/%(doctype)s/%(name)s">%(name)s</a>',data));}
else if(opts.content=='avatar'){$(parent).append(repl('<span class="avatar-small"><img src="%(avatar)s" \
    title="%(fullname)s"/></span>',data));}
else if(opts.content=='check'){$(parent).append('<input class="list-delete" type="checkbox">');$(parent).find('input').data('name',data.name);}
else if(opts.content=='docstatus'){$(parent).append(repl('<span class="docstatus"><i class="%(docstatus_icon)s" \
    title="%(docstatus_title)s"></i></span>',data));}
else if(opts.content=='tags'){this.add_user_tags(parent,data);}
else if(opts.content=='modified'){$(parent).append(data.when);}
else if(opts.type=='bar-graph'){this.render_bar_graph(parent,data,opts.content,opts.label);}
else if(opts.type=='link'&&opts.doctype){$(parent).append(repl('<a href="#!Form/'+opts.doctype+'/'
+data[opts.content]+'">'+data[opts.content]+'</a>',data));}
else if(opts.template){$(parent).append(repl(opts.template,data));}
else if(data[opts.content]){$(parent).append(' '+data[opts.content]);}},render:function(row,data){var me=this;this.prepare_data(data);rowhtml='';$.each(this.columns,function(i,v){rowhtml+=repl('<td style="width: %(width)s"></td>',v);});var tr=$(row).html('<table><tbody><tr>'+rowhtml+'</tr></tbody></table>').find('tr').get(0);$.each(this.columns,function(i,v){me.render_column(data,tr.cells[i],v);});},prepare_data:function(data){data.fullname=wn.user_info(data.owner).fullname;data.avatar=wn.user_info(data.owner).image;this.prepare_when(data,data.modified);if(data.docstatus==0||data.docstatus==null){data.docstatus_icon='icon-pencil';data.docstatus_title='Editable';}else if(data.docstatus==1){data.docstatus_icon='icon-lock';data.docstatus_title='Submitted';}else if(data.docstatus==2){data.docstatus_icon='icon-remove';data.docstatus_title='Cancelled';}
for(key in data){if(data[key]==null){data[key]='';}}},prepare_when:function(data,date_str){if(!date_str)date_str=data.modified;data.when=dateutil.str_to_user(date_str).split(' ')[0];var diff=dateutil.get_diff(dateutil.get_today(),date_str.split(' ')[0]);if(diff==0){data.when=dateutil.comment_when(date_str);}
if(diff==1){data.when='Yesterday'}
if(diff==2){data.when='2 days ago'}},add_user_tags:function(parent,data){var me=this;if(data._user_tags){if($(parent).html().length>0){$(parent).append('<br />');}
$.each(data._user_tags.split(','),function(i,t){if(t){$('<span class="label label-info" style="cursor: pointer; line-height: 200%">'
+strip(t)+'</span>').click(function(){me.doclistview.set_filter('_user_tags',$(this).text())}).appendTo(parent);}});}},show_hide_check_column:function(){if(!this.doclistview.can_delete){this.columns=$.map(this.columns,function(v,i){if(v.content!='check')return v});}},render_bar_graph:function(parent,data,field,label){var args={percent:data[field],fully_delivered:(data[field]>99?'bar-complete':''),label:label}
$(parent).append(repl('<span class="bar-outer" style="width: 30px; float: right" \
   title="%(percent)s% %(label)s">\
   <span class="bar-inner %(fully_delivered)s" \
    style="width: %(percent)s%;"></span>\
  </span>',args));},render_icon:function(parent,icon_class,label){var icon_html="<i class='%(icon_class)s' title='%(label)s'></i>";$(parent).append(repl(icon_html,{icon_class:icon_class,label:label||''}));}});wn.provide('wn.views.RecordListView');wn.views.RecordListView=wn.views.DocListView.extend({init:function(doctype,wrapper,ListView){this.doctype=doctype;this.wrapper=wrapper;this.listview=new ListView(this);this.listview.parent=this;this.setup();},setup:function(){var me=this;me.page_length=10;$(me.wrapper).empty();me.init_list();},get_args:function(){var args=this._super();$.each((this.default_filters||[]),function(i,f){args.filters.push(f);});args.docstatus=args.docstatus.concat((this.default_docstatus||[]));return args;},});
/*
 *	lib/js/wn/views/formview.js
 */
wn.provide('wn.views.formview');wn.views.formview={show:function(dt,dn){if(wn.model.new_names[dn])
dn=wn.model.new_names[dn];wn.model.with_doctype(dt,function(){wn.model.with_doc(dt,dn,function(dn,r){if(r&&r['403'])return;if(!(locals[dt]&&locals[dt][dn])){wn.container.change_to('404');return;}
if(!wn.views.formview[dt]){wn.views.formview[dt]=wn.container.add_page('Form - '+dt);wn.views.formview[dt].frm=new _f.Frm(dt,wn.views.formview[dt],true);}
wn.container.change_to('Form - '+dt);wn.views.formview[dt].frm.refresh(dn);});})},create:function(dt){var new_name=LocalDB.create(dt);wn.set_route('Form',dt,new_name);}}
/*
 *	lib/js/wn/views/reportview.js
 */
wn.views.reportview={show:function(dt,rep_name){wn.require('js/report-legacy.js');dt=get_label_doctype(dt);if(!_r.rb_con){_r.rb_con=new _r.ReportContainer();}
_r.rb_con.set_dt(dt,function(rb){if(rep_name){var route_changed=(rb.current_route!=wn.get_route_str())
rb.load_criteria(rep_name);if(rb.dt&&route_changed){rb.dt.run();}}
if(!rb.forbidden){wn.container.change_to('Report Builder');}});}}
wn.views.reportview2={show:function(dt){var page_name=wn.get_route_str();if(wn.pages[page_name]){wn.container.change_to(wn.pages[page_name]);}else{var route=wn.get_route();if(route[1]){new wn.views.ReportViewPage(route[1],route[2]);}else{wn.set_route('404');}}}}
wn.views.ReportViewPage=Class.extend({init:function(doctype,docname){this.doctype=doctype;this.docname=docname;this.page_name=wn.get_route_str();this.make_page();var me=this;wn.model.with_doctype(doctype,function(){me.make_report_view();if(docname){wn.model.with_doc('Report',docname,function(r){me.reportview.set_columns_and_filters(JSON.parse(locals['Report'][docname].json));me.reportview.run();});}else{me.reportview.run();}});},make_page:function(){this.page=wn.container.add_page(this.page_name);wn.ui.make_app_page({parent:this.page,single_column:true});wn.container.change_to(this.page_name);},make_report_view:function(){wn.views.breadcrumbs($('<span>').appendTo(this.page.appframe.$titlebar),locals.DocType[this.doctype].module);this.reportview=new wn.views.ReportView(this.doctype,this.docname,this.page)}})
wn.views.ReportView=wn.ui.Listing.extend({init:function(doctype,docname,page){var me=this;$(page).find('.layout-main').html('Loading Report...');this.import_slickgrid();$(page).find('.layout-main').empty();this.doctype=doctype;this.docname=docname;this.page=page;this.tab_name='`tab'+doctype+'`';this.setup();},import_slickgrid:function(){wn.require('js/lib/slickgrid/slick.grid.css');wn.require('js/lib/slickgrid/slick-default-theme.css');wn.require('js/lib/slickgrid/jquery.event.drag.min.js');wn.require('js/lib/slickgrid/slick.core.js');wn.require('js/lib/slickgrid/slick.grid.js');wn.dom.set_style('.slick-cell { font-size: 12px; }');},set_init_columns:function(){var columns=[['name'],['owner']];$.each(wn.meta.docfield_list[this.doctype],function(i,df){if(df.in_filter&&df.fieldname!='naming_series'&&df.fieldtype!='Table'){columns.push([df.fieldname]);}});this.columns=columns;},setup:function(){var me=this;this.make({title:'Report: '+(this.docname?(this.doctype+' - '+this.docname):this.doctype),appframe:this.page.appframe,method:'webnotes.widgets.doclistview.get',get_args:this.get_args,parent:$(this.page).find('.layout-main'),start:0,page_length:20,show_filters:true,new_doctype:this.doctype,allow_delete:true,});this.make_column_picker();this.make_sorter();this.make_export();this.set_init_columns();this.make_save();},set_columns_and_filters:function(opts){var me=this;if(opts.columns)this.columns=opts.columns;if(opts.filters)$.each(opts.filters,function(i,f){me.filter_list.add_filter(f[1],f[2],f[3]);});if(opts.sort_by)this.sort_by_select.val(opts.sort_by);if(opts.sort_order)this.sort_order_select.val(opts.sort_order);if(opts.sort_by_next)this.sort_by_next_select.val(opts.sort_by_next);if(opts.sort_order_next)this.sort_order_next_select.val(opts.sort_order_next);},get_args:function(){var me=this;return{doctype:this.doctype,fields:$.map(this.columns,function(v){return me.get_full_column_name(v)}),order_by:this.get_order_by(),filters:this.filter_list.get_filters(),docstatus:['0','1','2']}},get_order_by:function(){var order_by=this.get_selected_table_and_column(this.sort_by_select)
+' '+this.sort_order_select.val()
if(this.sort_by_next_select.val()){order_by+=', '+this.get_selected_table_and_column(this.sort_by_next_select)
+' '+this.sort_order_next_select.val()}
return order_by;},get_selected_table_and_column:function($select){return this.get_full_column_name([$select.val(),$select.find('option:selected').attr('table')])},get_full_column_name:function(v){return(v[1]?('`tab'+v[1]+'`'):this.tab_name)+'.'+v[0];},build_columns:function(){var me=this;return $.map(this.columns,function(c){var docfield=wn.meta.docfield_map[c[1]||me.doctype][c[0]];coldef={id:c[0],field:c[0],docfield:docfield,name:(docfield?docfield.label:toTitle(c[0])),width:(docfield?cint(docfield.width):120)||120}
if(c[0]=='name'){coldef.formatter=function(row,cell,value,columnDef,dataContext){return repl("<a href='#!Form/%(doctype)s/%(name)s'>%(name)s</a>",{doctype:me.doctype,name:value});}}else if(docfield&&docfield.fieldtype=='Link'){coldef.formatter=function(row,cell,value,columnDef,dataContext){if(value){return repl("<a href='#!Form/%(doctype)s/%(name)s'>%(name)s</a>",{doctype:columnDef.docfield.options,name:value});}else{return'';}}}
return coldef;});},render_list:function(){var me=this;var columns=[{id:'_idx',field:'_idx',name:'Sr.',width:40}].concat(this.build_columns());$.each(this.data,function(i,v){v._idx=i+1;});var options={enableCellNavigation:true,enableColumnReorder:false};var grid=new Slick.Grid(this.$w.find('.result-list').css('border','1px solid grey').css('height','500px').get(0),this.data,columns,options);},make_column_picker:function(){var me=this;this.column_picker=new wn.ui.ColumnPicker(this);this.page.appframe.add_button('Pick Columns',function(){me.column_picker.show(me.columns);},'icon-th-list');},make_sorter:function(){var me=this;this.sort_dialog=new wn.ui.Dialog({title:'Sorting Preferences'});$(this.sort_dialog.body).html('<p class="help">Sort By</p>\
   <div class="sort-column"></div>\
   <div><select class="sort-order" style="margin-top: 10px; width: 60%;">\
    <option value="asc">Ascending</option>\
    <option value="desc">Descending</option>\
   </select></div>\
   <hr><p class="help">Then By (optional)</p>\
   <div class="sort-column-1"></div>\
   <div><select class="sort-order-1" style="margin-top: 10px; width: 60%;">\
    <option value="asc">Ascending</option>\
    <option value="desc">Descending</option>\
   </select></div><hr>\
   <div><button class="btn btn-small btn-info">Update</div>');this.sort_by_select=new wn.ui.FieldSelect($(this.sort_dialog.body).find('.sort-column'),this.doctype).$select;this.sort_by_select.css('width','60%');this.sort_order_select=$(this.sort_dialog.body).find('.sort-order');this.sort_by_next_select=new wn.ui.FieldSelect($(this.sort_dialog.body).find('.sort-column-1'),this.doctype,null,true).$select;this.sort_by_next_select.css('width','60%');this.sort_order_next_select=$(this.sort_dialog.body).find('.sort-order-1');this.sort_by_select.val('modified');this.sort_order_select.val('desc');this.sort_by_next_select.val('');this.sort_order_next_select.val('desc');this.page.appframe.add_button('Sort By',function(){me.sort_dialog.show();},'icon-arrow-down');$(this.sort_dialog.body).find('.btn-info').click(function(){me.sort_dialog.hide();me.run();});},make_export:function(){var me=this;if(wn.user.is_report_manager()){this.page.appframe.add_button('Export',function(){var args=me.get_args();args.cmd='webnotes.widgets.doclistview.export_query'
open_url_post(wn.request.url,args);},'icon-download-alt');}},make_save:function(){var me=this;if(wn.user.is_report_manager()){this.page.appframe.add_button('Save',function(){if(me.docname){var name=me.docname}else{var name=prompt('Select Report Name');if(!name){return;}}
wn.call({method:'webnotes.widgets.doclistview.save_report',args:{name:name,doctype:me.doctype,json:JSON.stringify({filters:me.filter_list.get_filters(),columns:me.columns,sort_by:me.sort_by_select.val(),sort_order:me.sort_order_select.val(),sort_by_next:me.sort_by_next_select.val(),sort_order_next:me.sort_order_next_select.val()})},callback:function(r){if(r.exc)return;if(r.message!=me.docname)
wn.set_route('Report2',me.doctype,r.message);}});},'icon-upload');}}});wn.ui.ColumnPicker=Class.extend({init:function(list){this.list=list;this.doctype=list.doctype;this.selects={};},show:function(columns){wn.require('js/lib/jquery/jquery.ui.sortable.js');var me=this;if(!this.dialog){this.dialog=new wn.ui.Dialog({title:'Pick Columns',width:'400'});}
$(this.dialog.body).html('<div class="help">Drag to sort columns</div>\
   <div class="column-list"></div>\
   <div><button class="btn btn-small btn-add"><i class="icon-plus"></i>\
    Add Column</button></div>\
   <hr>\
   <div><button class="btn btn-small btn-info">Update</div>');$.each(columns,function(i,c){me.add_column(c);});$(this.dialog.body).find('.column-list').sortable();$(this.dialog.body).find('.btn-add').click(function(){me.add_column('name');});$(this.dialog.body).find('.btn-info').click(function(){me.dialog.hide();me.list.columns=[];$(me.dialog.body).find('select').each(function(){me.list.columns.push([$(this).val(),$(this).find('option:selected').attr('table')]);})
me.list.run();});this.dialog.show();},add_column:function(c){var w=$('<div style="padding: 5px 5px 5px 35px; background-color: #eee; width: 70%; \
   margin-bottom: 10px; border-radius: 3px; cursor: move;">\
   <a class="close" style="margin-top: 5px;">&times</a>\
   </div>').appendTo($(this.dialog.body).find('.column-list'));var fieldselect=new wn.ui.FieldSelect(w,this.doctype);fieldselect.$select.css('width','90%').val(c);w.find('.close').click(function(){$(this).parent().remove();});}});
/*
 *	lib/js/legacy/widgets/dialog.js
 */
var cur_dialog;var top_index=91;function Dialog(w,h,title,content){this.make({width:w,title:title});if(content)this.make_body(content);this.onshow='';this.oncancel='';this.no_cancel_flag=0;this.display=false;this.first_button=false;}
Dialog.prototype=new wn.widgets.Dialog()
Dialog.prototype.make_body=function(content){this.rows={};this.widgets={};for(var i in content)this.make_row(content[i]);}
Dialog.prototype.clear_inputs=function(d){for(var wid in this.widgets){var w=this.widgets[wid];var tn=w.tagName?w.tagName.toLowerCase():'';if(tn=='input'||tn=='textarea'){w.value='';}else if(tn=='select'){sel_val(w.options[0].value);}else if(w.txt){w.txt.value='';}else if(w.input){w.input.value='';}}}
Dialog.prototype.make_row=function(d){var me=this;this.rows[d[1]]=$a(this.body,'div','dialog_row');var row=this.rows[d[1]];if(d[0]!='HTML'){var t=make_table(row,1,2,'100%',['30%','70%']);row.tab=t;var c1=$td(t,0,0);var c2=$td(t,0,1);if(d[0]!='Check'&&d[0]!='Button')
$(c1).text(d[1]);}
if(d[0]=='HTML'){if(d[2])row.innerHTML=d[2];this.widgets[d[1]]=row;}
else if(d[0]=='Check'){var i=$a_input(c2,'checkbox','',{width:'20px'});c1.innerHTML=d[1];this.widgets[d[1]]=i;}
else if(d[0]=='Data'){c1.innerHTML=d[1];c2.style.overflow='auto';this.widgets[d[1]]=$a_input(c2,'text');if(d[2])$a(c2,'div','field_description').innerHTML=d[2];}
else if(d[0]=='Link'){c1.innerHTML=d[1];var f=make_field({fieldtype:'Link','label':d[1],'options':d[2]},'',c2,this,0,1);f.not_in_form=1;f.dialog=this;f.refresh();this.widgets[d[1]]=f.input;}
else if(d[0]=='Date'){c1.innerHTML=d[1];var f=make_field({fieldtype:'Date','label':d[1],'options':d[2]},'',c2,this,0,1);f.not_in_form=1;f.refresh();f.dialog=this;this.widgets[d[1]]=f.input;}
else if(d[0]=='Password'){c1.innerHTML=d[1];c2.style.overflow='auto';this.widgets[d[1]]=$a_input(c2,'password');if(d[3])$a(c2,'div','field_description').innerHTML=d[3];}
else if(d[0]=='Select'){c1.innerHTML=d[1];this.widgets[d[1]]=$a(c2,'select','',{width:'160px'})
if(d[2])$a(c2,'div','field_description').innerHTML=d[2];if(d[3])add_sel_options(this.widgets[d[1]],d[3],d[3][0]);}
else if(d[0]=='Text'){c1.innerHTML=d[1];c2.style.overflow='auto';this.widgets[d[1]]=$a(c2,'textarea');if(d[2])$a(c2,'div','field_description').innerHTML=d[2];}
else if(d[0]=='Button'){c2.style.height='32px';var b=$btn(c2,d[1],function(btn){if(btn._onclick)btn._onclick(me)},null,null,1);b.dialog=me;if(!this.first_button){$(b).addClass('btn-info');this.first_button=true;}
if(d[2]){b._onclick=d[2];}
this.widgets[d[1]]=b;}}
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
function LayoutRow(layout,parent){this.layout=layout;this.wrapper=$a(parent,'div','form-layout-row');this.main_head=$a(this.wrapper,'div');this.main_body=$a(this.wrapper,'div');if(layout.with_border){this.wrapper.style.border='1px solid #000';this.wrapper.style.borderBottom='0px';}
this.header=$a(this.main_body,'div','',{padding:(layout.with_border?'0px 8px':'0px')});this.body=$a(this.main_body,'div');this.table=$a(this.body,'table','',{width:'100%',borderCollapse:'collapse'});this.row=this.table.insertRow(0);this.mycells=[];}
LayoutRow.prototype.hide=function(){$dh(this.wrapper);}
LayoutRow.prototype.show=function(){$ds(this.wrapper);}
LayoutRow.prototype.addCell=function(wid){var lc=new LayoutCell(this.layout,this,wid);this.mycells[this.mycells.length]=lc;return lc;}
function LayoutCell(layout,layoutRow,width){if(width){var w=width+'';if(w.substr(w.length-2,2)!='px'){if(w.substr(w.length-1,1)!="%"){width=width+'%'};}}
this.width=width;this.layout=layout;var cidx=layoutRow.row.cells.length;this.cell=layoutRow.row.insertCell(cidx);this.cell.style.verticalAlign='top';this.set_width(layoutRow.row,width);var h=$a(this.cell,'div','',{padding:(layout.with_border?'0px 8px':'0px')});this.wrapper=$a(this.cell,'div','',{padding:(layout.with_border?'8px':'0px')});layout.cur_cell=this.wrapper;layout.cur_cell.header=h;}
LayoutCell.prototype.set_width=function(row,width){var w=100;var n_cells=row.cells.length;var cells_with_no_width=n_cells;if(width){$y(row.cells[n_cells-1],{width:cint(width)+'%'})}else{row.cells[n_cells-1].estimated_width=1;}
for(var i=0;i<n_cells;i++){if(!row.cells[i].estimated_width){w=w-cint(row.cells[i].style.width);cells_with_no_width--;}}
for(var i=0;i<n_cells;i++){if(row.cells[i].estimated_width)
$y(row.cells[i],{width:cint(w/cells_with_no_width)+'%'})}}
LayoutCell.prototype.show=function(){$ds(this.wrapper);}
LayoutCell.prototype.hide=function(){$dh(this.wrapper);}
/*
 *	lib/js/legacy/widgets/tabbedpage.js
 */
function TabbedPage(parent,only_labels){this.tabs={};this.items=this.tabs
this.cur_tab=null;this.label_wrapper=$a(parent,'div','box_label_wrapper',{marginTop:'16px'});this.label_body=$a(this.label_wrapper,'div','box_label_body');this.label_area=$a(this.label_body,'ul','box_tabs');if(!only_labels)this.body_area=$a(parent,'div','',{backgroundColor:'#FFF'});else this.body_area=null;this.add_item=function(label,onclick,no_body,with_heading){this.add_tab(label,onclick,no_body,with_heading);return this.items[label];}}
TabbedPage.prototype.add_tab=function(n,onshow,no_body,with_heading){var tab=$a(this.label_area,'li');tab.label=$a(tab,'a');tab.label.innerHTML=n;if(this.body_area&&!no_body){tab.tab_body=$a(this.body_area,'div');$dh(tab.tab_body);tab.body=tab.tab_body;}else{tab.tab_body=null;}
tab.onshow=onshow;var me=this;tab.collapse=function(){if(this.tab_body)$dh(this.tab_body);this.className='';}
tab.set_selected=function(){if(me.cur_tab)me.cur_tab.collapse();this.className='box_tab_selected';$(this).css('opacity',1);me.cur_tab=this;}
tab.expand=function(arg){this.set_selected();if(this.tab_body)$ds(this.tab_body);if(this.onshow)this.onshow(arg);}
tab.onmouseover=function(){if(me.cur_tab!=this)this.className='box_tab_mouseover';}
tab.onmouseout=function(){if(me.cur_tab!=this)this.className=''}
tab.hide=function(){this.collapse();$dh(this);}
tab.show=function(){$ds(this);}
tab.onclick=function(){this.expand();}
this.tabs[n]=tab;return tab;}
function TrayPage(parent,height,width,width_body){var me=this;if(!width)width=(100/8)+'%';this.body_style={margin:'4px 8px'}
this.cur_item=null;this.items={};this.tabs=this.items
this.tab=make_table($a(parent,'div'),1,2,'100%',[width,width_body]);$y($td(this.tab,0,0),{backgroundColor:this.tray_bg,width:width});this.body=$a($td(this.tab,0,1),'div');if(height){$y(this.body,{height:height,overflow:'auto'});}
this.add_item=function(label,onclick,no_body,with_heading){this.items[label]=new TrayItem(me,label,onclick,no_body,with_heading);return this.items[label];}}
function TrayItem(tray,label,onclick,no_body,with_heading){this.label=label;this.onclick=onclick;var me=this;this.ldiv=$a($td(tray.tab,0,0),'div');$item_normal(this.ldiv);if(!no_body){this.wrapper=$a(tray.body,'div','',tray.body_style);if(with_heading){this.header=$a(this.wrapper,'div','sectionHeading',{marginBottom:'16px',paddingBottom:'0px'});this.header.innerHTML=label;}
this.body=$a(this.wrapper,'div');this.tab_body=this.body;$dh(this.wrapper);}
$(this.ldiv).html(label).hover(function(){if(tray.cur_item.label!=this.label)$item_active(this);},function(){if(tray.cur_item.label!=this.label)$item_normal(this);}).click(function(){me.expand();})
this.ldiv.label=label;this.ldiv.setAttribute('title',label);this.ldiv.onmousedown=function(){$item_pressed(this);}
this.ldiv.onmouseup=function(){$item_selected(this);}
this.expand=function(){if(tray.cur_item)tray.cur_item.collapse();if(me.wrapper)$ds(me.wrapper);if(me.onclick)me.onclick(me.label);me.show_as_expanded();}
this.show_as_expanded=function(){$item_selected(me.ldiv);tray.cur_item=me;}
this.collapse=function(){if(me.wrapper)$dh(me.wrapper);$item_normal(me.ldiv);}
this.hide=function(){me.collapse();$dh(me.ldiv);}
this.show=function(){$ds(me.ldiv);}}
/*
 *	lib/js/legacy/webpage/page_header.js
 */
var def_ph_style={wrapper:{marginBottom:'16px',backgroundColor:'#EEE'},main_heading:{},sub_heading:{marginBottom:'8px',color:'#555',display:'none'},separator:{borderTop:'1px solid #ddd'},toolbar_area:{padding:'3px 0px',display:'none',borderBottom:'1px solid #ddd'}}
function PageHeader(parent,main_text,sub_text){this.wrapper=$a(parent,'div','page_header');this.close_btn=$a(this.wrapper,'a','close',{},'&times;');this.close_btn.onclick=function(){window.history.back();};this.breadcrumbs=$a(this.wrapper,'div','breadcrumbs-area');this.main_head=$a(this.wrapper,'h1','',def_ph_style.main_heading);this.sub_head=$a(this.wrapper,'h4','',def_ph_style.sub_heading);this.separator=$a(this.wrapper,'div','',def_ph_style.separator);this.toolbar_area=$a(this.wrapper,'div','',def_ph_style.toolbar_area);this.padding_area=$a(this.wrapper,'div','',{padding:'3px'});if(main_text)this.main_head.innerHTML=main_text;if(sub_text)this.sub_head.innerHTML=sub_text;this.buttons={};this.buttons2={};}
PageHeader.prototype.add_button=function(label,fn,bold,icon,green){var tb=this.toolbar_area;if(this.buttons[label])return;iconhtml=icon?('<i class="'+icon+'"></i> '):'';var $button=$('<button class="btn btn-small">'+iconhtml+label+'</button>').click(fn).appendTo(tb);if(green){$button.addClass('btn-info');$button.find('i').addClass('icon-white');}
if(bold)$button.css('font-weight','bold');this.buttons[label]=$button.get(0);$ds(this.toolbar_area);return this.buttons[label];}
PageHeader.prototype.clear_toolbar=function(){this.toolbar_area.innerHTML='';this.buttons={};}
PageHeader.prototype.make_buttonset=function(){$(this.toolbar_area).buttonset();}
/*
 *	lib/js/legacy/widgets/tags.js
 */
_tags={dialog:null,color_map:{},all_tags:[],colors:{'Default':'#add8e6'}}
TagList=function(parent,start_list,dt,dn,static,onclick){this.start_list=start_list?start_list:[];this.tag_list=[];this.dt=dt;this.onclick=onclick;this.dn=dn;this.static;this.parent=parent;this.make_body();}
TagList.prototype.make=function(parent){for(var i=0;i<this.start_list.length;i++){if(this.start_list[i])
new SingleTag({parent:this.body,label:this.start_list[i],dt:this.dt,dn:this.dn,fieldname:'_user_tags',static:this.static,taglist:this,onclick:this.onclick});}}
TagList.prototype.make_body=function(){var div=$a(this.parent,'span','',{margin:'3px 0px',padding:'3px 0px'});this.body=$a(div,'span','',{marginRight:'4px'});this.add_tag_area=$a(div,'span');this.make_add_tag();this.make();}
TagList.prototype.add_tag=function(label,static,fieldname,color){if(!label)return;if(in_list(this.tag_list,label))return;var tag=new SingleTag({parent:this.body,label:label,dt:this.dt,dn:this.dn,fieldname:fieldname,static:static,taglist:this,color:color,onclick:this.onclick});}
TagList.prototype.make_add_tag=function(){var me=this;this.add_tag_span=$a(this.add_tag_area,'span','',{color:'#888',textDecoration:'underline',cursor:'pointer',marginLeft:'4px',fontSize:'11px'});this.add_tag_span.innerHTML='Add tag';this.add_tag_span.onclick=function(){me.new_tag();}}
TagList.prototype.make_tag_dialog=function(){var me=this;var d=new wn.widgets.Dialog({title:'Add a tag',width:400,fields:[{fieldtype:'Link',fieldname:'tag',label:'Tag',options:'Tag',reqd:1,description:'Max chars (20)',no_buttons:1},{fieldtype:'Button',fieldname:'add',label:'Add'}]})
$(d.fields_dict.tag.input).attr('maxlength',20);d.fields_dict.add.input.onclick=function(){me.save_tag(d);}
return d;}
TagList.prototype.is_text_okay=function(val){if(!val){msgprint("Please type something");return;}
if(validate_spl_chars(val)){msgprint("Special charaters, commas etc not allowed in tags");return;}
return 1}
TagList.prototype.add_to_locals=function(tag){if(locals[this.dt]&&locals[this.dt][this.dn]){var doc=locals[this.dt][this.dn];if(!doc._user_tags){doc._user_tags=''}
var tl=doc._user_tags.split(',')
tl.push(tag)
doc._user_tags=tl.join(',');}}
TagList.prototype.remove_from_locals=function(tag){if(locals[this.dt]&&locals[this.dt][this.dn]){var doc=locals[this.dt][this.dn];var tl=doc._user_tags.split(',');var new_tl=[];for(var i=0;i<tl.length;i++){if(tl[i]!=tag)new_tl.push(tl[i]);}
doc._user_tags=new_tl.join(',');}}
TagList.prototype.save_tag=function(d){var val=d.get_values();if(val)val=val.tag;var me=this;if(!this.is_text_okay(val))return;var callback=function(r,rt){var d=me.dialog;d.fields_dict.add.input.done_working();d.fields_dict.tag.input.set_input('');d.hide();me.add_to_locals(val)
if(!r.message)return;me.add_tag(r.message,0,'_user_tags');}
me.dialog.fields_dict.add.input.set_working();$c('webnotes.widgets.tags.add_tag',{'dt':me.dt,'dn':me.dn,'tag':val,'color':'na'},callback);}
TagList.prototype.new_tag=function(){var me=this;if(!this.dialog){this.dialog=this.make_tag_dialog();}
this.dialog.show();}
TagList.prototype.refresh_tags=function(){}
function SingleTag(opts){$.extend(this,opts);if(!this.color)this.color='#add8e6';if(this.taglist&&!in_list(this.taglist.tag_list,this.label))
this.taglist.tag_list.push(this.label);this.make_body(this.parent);}
SingleTag.prototype.make_body=function(parent){var me=this;this.body=$a(parent,'span','',{padding:'2px 4px',backgroundColor:this.color,color:'#226',marginRight:'4px'});$br(this.body,'3px');if(this.onclick)$y(this.body,{cursor:'pointer'});$(this.body).hover(function(){$(this).css('opacity',0.6);},function(){$(this).css('opacity',1);});this.make_label();if(!this.static)this.make_remove_btn();_tags.all_tags.push(this);}
SingleTag.prototype.make_remove_btn=function(){var me=this;var span=$a(this.body,'span');span.innerHTML+=' |';var span=$a(this.body,'span','',{cursor:'pointer'});span.innerHTML=' x'
span.onclick=function(){me.remove(me);}}
SingleTag.prototype.make_label=function(){var me=this;this.label_span=$a(this.body,'span','social',null,this.label);this.label_span.onclick=function(){if(me.onclick)me.onclick(me);}}
SingleTag.prototype.remove_tag_body=function(){$dh(this.body);var nl=[];for(var i in this.tag_list)
if(this.tag_list[i]!=this.label)
nl.push(this.tag_list[i]);if(this.taglist)
this.taglist.tag_list=nl;}
SingleTag.prototype.remove=function(){var me=this;var callback=function(r,rt){me.remove_tag_body()
me.taglist.remove_from_locals(me.label);}
$c('webnotes.widgets.tags.remove_tag',{'dt':me.dt,'dn':me.dn,'tag':me.label},callback)
$bg(me.body,'#DDD');}
wn.widgets.TagCloud=function(parent,doctype,onclick){var me=this;this.make=function(r,rt){parent.innerHTML='';if(r.message&&r.message.length){me.tab=make_table(parent,r.message.length,2,'100%',['40px',null],{padding:'5px 3px 5px 0px'})
$y($td(me.tab,0,0),{textAlign:'right'});for(var i=0;i<r.message.length;i++){new wn.widgets.TagCloud.Tag({parent:$td(me.tab,i,1),label:r.message[i][0],onclick:onclick,fieldname:r.message[i][2]},$td(me.tab,i,0),r.message[i])}}else{me.set_no_tags();}
me.refresh=$ln($a(parent,'div'),'refresh',function(){me.refresh.set_working();me.render(1);},{fontSize:'11px',margin:'3px 0px',color:'#888'},1);}
this.set_no_tags=function(){$a(parent,'div','social comment',{fontSize:'11px',margin:'3px 0px'},'<i>No tags yet!, please start tagging</i>');}
this.render=function(refresh){$c('webnotes.widgets.tags.get_top_tags',{doctype:doctype,refresh:(refresh?1:0)},this.make);}
this.render();}
wn.widgets.TagCloud.Tag=function(args,count_cell,det){$(count_cell).css('text-align','right').html(det[1]+' x');args.static=1;this.tag=new SingleTag(args)}
/*
 *	lib/js/legacy/widgets/export_query.js
 */
var export_dialog;function export_query(query,callback){if(!export_dialog){var d=new Dialog(400,300,"Export...");d.make_body([['Data','Max rows','Blank to export all rows'],['Button','Go'],]);d.widgets['Go'].onclick=function(){export_dialog.hide();n=export_dialog.widgets['Max rows'].value;if(cint(n))
export_dialog.query+=' LIMIT 0,'+cint(n);callback(export_dialog.query);}
d.onshow=function(){this.widgets['Max rows'].value='500';}
export_dialog=d;}
export_dialog.query=query;export_dialog.show();}
function export_csv(q,report_name,sc_id,is_simple,filter_values,colnames){var args={}
args.cmd='webnotes.widgets.query_builder.runquery_csv';if(is_simple)
args.simple_query=q;else
args.query=q;args.sc_id=sc_id?sc_id:'';args.filter_values=filter_values?filter_values:'';if(colnames)
args.colnames=colnames.join(',');args.report_name=report_name?report_name:'';open_url_post(wn.request.url,args);}
/*
 *	lib/js/legacy/webpage/search.js
 */
search_fields={};function setlinkvalue(name){selector.input.set_input_value(name);selector.hide();}
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
d.onhide=function(){}
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
var pending_req=0;var fcount=0;var dialog_back;function set_loading(){pending_req++;$('#spinner').css('visibility','visible');$('body').css('cursor','progress');}
function hide_loading(){pending_req--;if(!pending_req){$('body').css('cursor','default');$('#spinner').css('visibility','hidden');}}
function freeze(){if(!dialog_back){dialog_back=$a($i('body_div'),'div','dialog_back');$(dialog_back).css('opacity',0.6);}
$ds(dialog_back);fcount++;}
function unfreeze(){if(!fcount)return;fcount--;if(!fcount){$dh(dialog_back);}}
/*
 *	lib/js/legacy/webpage/loaders.js
 */
function loadreport(dt,rep_name,onload){if(rep_name)
wn.set_route('Report',dt,rep_name);else
wn.set_route('Report',dt);}
function loaddoc(doctype,name,onload){wn.model.with_doctype(doctype,function(){if(locals.DocType[doctype].in_dialog){_f.edit_record(doctype,name);}else{wn.set_route('Form',doctype,name);}})}
var load_doc=loaddoc;function new_doc(doctype,onload,in_dialog,on_save_callback,cdt,cdn,cnic){doctype=get_label_doctype(doctype);wn.model.with_doctype(doctype,function(){if(locals.DocType[doctype].in_dialog){var new_name=LocalDB.create(doctype);_f.edit_record(doctype,new_name);}else{wn.views.formview.create(doctype);}})}
var newdoc=new_doc;var pscript={};function loadpage(page_name,call_back,no_history){wn.set_route(page_name);}
function loaddocbrowser(dt){wn.set_route('List',dt);}
/*
 *	lib/js/legacy/wn/page_layout.js
 */
wn.PageLayout=function(args){$.extend(this,args)
this.wrapper=$a(this.parent,'div','layout-wrapper layout-wrapper-background');this.head=$a(this.wrapper,'div');this.main=$a(this.wrapper,'div','layout-main-section');this.sidebar_area=$a(this.wrapper,'div','layout-side-section');$a(this.wrapper,'div','',{clear:'both'});this.body=$a(this.main,'div');this.footer=$a(this.main,'div');if(this.heading){this.page_head=new PageHeader(this.head,this.heading);}}
/*
 *	lib/js/legacy/wn/widgets/page_sidebar.js
 */
wn.widgets.PageSidebar=function(parent,opts){this.opts=opts
this.sections={}
this.wrapper=$a(parent,'div','psidebar')
this.refresh=function(){this.wrapper.innerHTML=''
if(this.opts.title)
this.make_head();for(var i=0;i<this.opts.sections.length;i++){var section=this.opts.sections[i];if((section.display&&section.display())||!section.display){this.sections[section.title]=new wn.widgets.PageSidebarSection(this,section);}}
if(this.opts.onrefresh){this.opts.onrefresh(this)}}
this.make_head=function(){this.head=$a(this.wrapper,'div','head','',this.opts.title);}
this.refresh();}
wn.widgets.PageSidebarSection=function(sidebar,opts){this.items=[];this.sidebar=sidebar;this.wrapper=$a(sidebar.wrapper,'div','section');this.head=$a(this.wrapper,'div','section-head','',opts.title);this.body=$a(this.wrapper,'div','section-body');$br(this.wrapper,'5px');this.opts=opts;this.make_items=function(){for(var i=0;i<this.opts.items.length;i++){var item=this.opts.items[i];if((item.display&&item.display())||!item.display){var div=$a(this.body,'div','section-item small');this.make_one_item(item,div);}}}
this.make_one_item=function(item,div){if(item.type.toLowerCase()=='link')
this.items[item.label]=new wn.widgets.PageSidebarLink(this,item,div);else if(item.type.toLowerCase()=='button')
this.items[item.label]=new wn.widgets.PageSidebarButton(this,this.opts.items[i],div);else if(item.type.toLowerCase()=='html')
this.items[item.label]=new wn.widgets.PageSidebarHTML(this,this.opts.items[i],div);}
this.add_icon=function(parent,icon){var img=$a(parent,'i',icon,{marginRight:'7px',marginBottom:'-3px'});}
this.refresh=function(){this.body.innerHTML='';if(this.opts.render){this.opts.render(this.body);}
else
this.make_items();}
this.refresh();}
wn.widgets.PageSidebarLink=function(section,opts,wrapper){this.wrapper=wrapper;this.section=section;this.opts=opts;var me=this;if(opts.icon){section.add_icon(this.wrapper,opts.icon);}
this.ln=$a(this.wrapper,'span','link_type section-link small',opts.style,opts.label);this.ln.onclick=function(){me.opts.onclick(me)};}
wn.widgets.PageSidebarButton=function(section,opts,wrapper){this.wrapper=wrapper;this.section=section;this.opts=opts;var me=this;this.btn=$btn(this.wrapper,opts.label,opts.onclick,opts.style,opts.color);}
wn.widgets.PageSidebarHTML=function(section,opts,wrapper){wrapper.innerHTML=opts.content}
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
var locals={'DocType':{}};var LocalDB={};var READ=0;var WRITE=1;var CREATE=2;var SUBMIT=3;var CANCEL=4;var AMEND=5;LocalDB.getchildren=function(child_dt,parent,parentfield,parenttype){var l=[];for(var key in locals[child_dt]){var d=locals[child_dt][key];if((d.parent==parent)&&(d.parentfield==parentfield)){if(parenttype){if(d.parenttype==parenttype)l.push(d);}else{l.push(d);}}}
l.sort(function(a,b){return(cint(a.idx)-cint(b.idx))});return l;}
LocalDB.add=function(dt,dn){if(!locals[dt])locals[dt]={};if(locals[dt][dn])delete locals[dt][dn];locals[dt][dn]={'name':dn,'doctype':dt,'docstatus':0};return locals[dt][dn];}
LocalDB.delete_doc=function(dt,dn){var doc=get_local(dt,dn);for(var ndt in locals){if(locals[ndt]){for(var ndn in locals[ndt]){var doc=locals[ndt][ndn];if(doc&&doc.parenttype==dt&&(doc.parent==dn||doc.__oldparent==dn)){delete locals[ndt][ndn];}}}}
delete locals[dt][dn];}
function get_local(dt,dn){return locals[dt]?locals[dt][dn]:null;}
LocalDB.sync=function(list){if(list._kl)list=expand_doclist(list);if(list){LocalDB.clear_locals(list[0].doctype,list[0].name);}
for(var i=0;i<list.length;i++){var d=list[i];if(!d.name)
d.name=LocalDB.get_localname(d.doctype);LocalDB.add(d.doctype,d.name);locals[d.doctype][d.name]=d;if(d.doctype=='DocField')wn.meta.add_field(d);if(d.localname){wn.model.new_names[d.localname]=d.name;$(document).trigger('rename',[d.doctype,d.localname,d.name]);delete locals[d.doctype][d.localname];}}}
LocalDB.clear_locals=function(dt,dn){var doclist=make_doclist(dt,dn,1);$.each(doclist,function(i,v){v&&delete locals[v.doctype][v.name];});}
local_name_idx={};LocalDB.get_localname=function(doctype){if(!local_name_idx[doctype])local_name_idx[doctype]=1;var n='New '+get_doctype_label(doctype)+' '+local_name_idx[doctype];local_name_idx[doctype]++;return n;}
LocalDB.set_default_values=function(doc){var doctype=doc.doctype;var docfields=wn.meta.docfield_list[doctype];if(!docfields){return;}
var fields_to_refresh=[];for(var fid=0;fid<docfields.length;fid++){var f=docfields[fid];if(!in_list(no_value_fields,f.fieldtype)&&doc[f.fieldname]==null){var v=LocalDB.get_default_value(f.fieldname,f.fieldtype,f['default']);if(v){doc[f.fieldname]=v;fields_to_refresh.push(f.fieldname);}}}
return fields_to_refresh;}
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
LocalDB.delete_record=function(dt,dn){delete locals[dt][dn];}
LocalDB.get_default_value=function(fn,ft,df){if(df=='_Login'||df=='__user')
return user;else if(df=='_Full Name')
return user_fullname;else if(ft=='Date'&&(df=='Today'||df=='__today')){return get_today();}
else if(df)
return df;else if(user_defaults[fn])
return user_defaults[fn][0];else if(sys_defaults[fn])
return sys_defaults[fn];}
LocalDB.add_child=function(doc,childtype,parentfield){var n=LocalDB.create(childtype);var d=locals[childtype][n];d.parent=doc.name;d.parentfield=parentfield;d.parenttype=doc.doctype;return d;}
LocalDB.no_copy_list=['amended_from','amendment_date','cancel_reason'];LocalDB.copy=function(dt,dn,from_amend){var newdoc=LocalDB.create(dt);for(var key in locals[dt][dn]){var df=get_field(dt,key);if(key!=='name'&&key.substr(0,2)!='__'&&!(df&&((!from_amend&&cint(df.no_copy)==1)||in_list(LocalDB.no_copy_list,df.fieldname)))){locals[dt][newdoc][key]=locals[dt][dn][key];}}
return locals[dt][newdoc];}
function make_doclist(dt,dn){if(!locals[dt]){return[];}
var dl=[];dl[0]=locals[dt][dn];for(var ndt in locals){if(locals[ndt]){for(var ndn in locals[ndt]){var doc=locals[ndt][ndn];if(doc&&doc.parenttype==dt&&doc.parent==dn){dl.push(doc)}}}}
return dl;}
var Meta={};var local_dt={};Meta.make_local_dt=function(dt,dn){var dl=make_doclist('DocType',dt);if(!local_dt[dt])local_dt[dt]={};if(!local_dt[dt][dn])local_dt[dt][dn]={};for(var i=0;i<dl.length;i++){var d=dl[i];if(d.doctype=='DocField'){var key=d.fieldname?d.fieldname:d.label;local_dt[dt][dn][key]=copy_dict(d);}}}
Meta.get_field=function(dt,fn,dn){if(dn&&local_dt[dt]&&local_dt[dt][dn]){return local_dt[dt][dn][fn];}else{if(wn.meta.docfield_map[dt])var d=wn.meta.docfield_map[dt][fn];if(d)return d;}
return{};}
Meta.set_field_property=function(fn,key,val,doc){if(!doc&&(cur_frm.doc))doc=cur_frm.doc;try{local_dt[doc.doctype][doc.name][fn][key]=val;refresh_field(fn);}catch(e){alert("Client Script Error: Unknown values for "+doc.name+','+fn+'.'+key+'='+val);}}
function get_doctype_label(dt){return dt}
function get_label_doctype(label){return label}
var getchildren=LocalDB.getchildren;var get_field=Meta.get_field;var createLocal=LocalDB.create;
/*
 *	lib/js/legacy/model/doclist.js
 */
function compress_doclist(list){var kl={};var vl=[];var flx={};for(var i=0;i<list.length;i++){var o=list[i];var fl=[];if(!kl[o.doctype]){var tfl=['doctype','name','docstatus','owner','parent','parentfield','parenttype','idx','creation','modified','modified_by','__islocal','__newname','__modified','_user_tags'];var fl=[].concat(tfl);for(key in wn.meta.docfield_map[o.doctype]){if(!in_list(fl,key)&&!in_list(no_value_fields,wn.meta.docfield_map[o.doctype][key].fieldtype)&&!wn.meta.docfield_map[o.doctype][key].no_column){fl[fl.length]=key;tfl[tfl.length]=key}}
flx[o.doctype]=fl;kl[o.doctype]=tfl}
var nl=[];var fl=flx[o.doctype];for(var j=0;j<fl.length;j++){var v=o[fl[j]];nl.push(v);}
vl.push(nl);}
return JSON.stringify({'_vl':vl,'_kl':kl});}
function expand_doclist(docs){var l=[];for(var i=0;i<docs._vl.length;i++)
l[l.length]=zip(docs._kl[docs._vl[i][0]],docs._vl[i]);return l;}
function zip(k,v){var obj={};for(var i=0;i<k.length;i++){obj[k[i]]=v[i];}
return obj;}
function save_doclist(dt,dn,save_action,onsave,onerr){var doc=locals[dt][dn];var doctype=locals['DocType'][dt];var tmplist=[];var doclist=make_doclist(dt,dn,1);var all_reqd_ok=true;if(save_action!='Cancel'){for(var n in doclist){var reqd_ok=check_required(doclist[n].doctype,doclist[n].name,doclist[0].doctype);if(doclist[n].docstatus+''!='2'&&all_reqd_ok)
all_reqd_ok=reqd_ok;}}
if(!all_reqd_ok){onerr()
return;}
var _save=function(){$c('webnotes.widgets.form.save.savedocs',{'docs':compress_doclist(doclist),'docname':dn,'action':save_action,'user':user},function(r,rtxt){if(f){f.savingflag=false;}
if(r.saved){if(onsave)onsave(r);}else{if(onerr)onerr(r);}},function(){if(f){f.savingflag=false;}},0,(f?'Saving...':''));}
if(doc.__islocal&&(doctype&&doctype.autoname&&doctype.autoname.toLowerCase()=='prompt')){var newname=prompt('Enter the name of the new '+dt,'');if(newname){doc.__newname=strip(newname);_save();}else{msgprint('Not Saved');onerr();}}else{_save();}}
function check_required(dt,dn,parent_dt){var doc=locals[dt][dn];if(doc.docstatus>1)return true;var fl=wn.meta.docfield_list[dt];if(!fl)return true;var all_clear=true;var errfld=[];for(var i=0;i<fl.length;i++){var key=fl[i].fieldname;var v=doc[key];if(fl[i].reqd&&is_null(v)&&fl[i].fieldname){errfld[errfld.length]=fl[i].label;if(cur_frm){var f=cur_frm.fields_dict[fl[i].fieldname];if(f){if(f.set_as_error)f.set_as_error(1);if(!cur_frm.error_in_section&&f.parent_section){cur_frm.error_in_section=1;}}}
if(all_clear)all_clear=false;}}
if(errfld.length)msgprint('<b>Mandatory fields required in '+
(doc.parenttype?(wn.meta.docfield_map[doc.parenttype][doc.parentfield].label+' (Table)'):get_doctype_label(doc.doctype))+':</b>\n'+errfld.join('\n'));return all_clear;}
/*
 *	lib/js/wn/ui/toolbar.min.js
 */

/*
 *	lib/js/wn/ui/toolbar/selector_dialog.js
 */
wn.provide('wn.ui.toolbar');wn.ui.toolbar.SelectorDialog=Class.extend({init:function(opts){this.opts=opts;try{this.make_dialog();}catch(e){console.log(e);}
this.bind_events();},make_dialog:function(){this.dialog=new wn.widgets.Dialog({title:this.opts.title,width:300,fields:[{fieldtype:'Select',fieldname:'doctype',options:'Select...',label:'Select Type'},{fieldtype:'Button',label:'Go',fieldname:'go'}]});},bind_events:function(){var me=this;$(this.dialog.fields_dict.go.input).click(function(){if(!me.dialog.display)return;me.dialog.hide();me.opts.execute(me.dialog.fields_dict.doctype.get_value());});$(this.dialog.fields_dict.doctype.input).change(function(){me.dialog.fields_dict.go.input.click();}).keypress(function(ev){if(ev.which==13){me.dialog.fields_dict.go.input.click();}});},show:function(){this.dialog.show();this.dialog.fields_dict.doctype.input.focus();return false;},set_values:function(lst){for(var i=0;i<lst.length;i++)
lst[i]=get_doctype_label(lst[i]);var sel=this.dialog.fields_dict.doctype.input;$(sel).empty();add_sel_options(sel,lst.sort());}})
/*
 *	lib/js/wn/ui/toolbar/new.js
 */
wn.ui.toolbar.NewDialog=wn.ui.toolbar.SelectorDialog.extend({init:function(){this._super({title:"New Record",execute:function(val){new_doc(val);},});this.set_values(profile.can_create.join(',').split(','));}});
/*
 *	lib/js/wn/ui/toolbar/search.js
 */
wn.ui.toolbar.Search=wn.ui.toolbar.SelectorDialog.extend({init:function(){this._super({title:"Search",execute:function(val){new wn.ui.Search({doctype:val});},});this.set_values(wn.boot.profile.can_search.join(',').split(','));makeselector();}});
/*
 *	lib/js/wn/ui/toolbar/report.js
 */
wn.ui.toolbar.Report=wn.ui.toolbar.SelectorDialog.extend({init:function(){this._super({title:"Start Report For",execute:function(val){wn.set_route('Report2',val);},});this.set_values(profile.can_get_report.join(',').split(','));}});
/*
 *	lib/js/wn/ui/toolbar/recent.js
 */
wn.ui.toolbar.RecentDocs=Class.extend({init:function(){$('.navbar .nav:first').append('<li class="dropdown">\
   <a class="dropdown-toggle" data-toggle="dropdown" href="#" \
    onclick="return false;">Recent<b class="caret"></b></a>\
   <ul class="dropdown-menu" id="toolbar-recent"></ul>\
  </li>');this.setup();this.bind_events();},bind_events:function(){var me=this;$(document).bind('rename',function(event,dt,old_name,new_name){me.rename_notify(dt,old_name,new_name)});},rename_notify:function(dt,old,name){this.remove(dt,old);this.add(dt,name,1);},add:function(dt,dn,on_top){if(this.istable(dt))return;this.remove(dt,dn);var html=repl('<li data-docref="%(dt)s/%(dn)s">\
   <a href="#Form/%(dt)s/%(dn)s">\
    %(dn)s <span style="font-size: 10px">(%(dt)s)</span>\
   </a></li>',{dt:dt,dn:dn});if(on_top){$('#toolbar-recent').prepend(html);}else{$('#toolbar-recent').append(html);}},istable:function(dt){return locals.DocType[dt]&&locals.DocType[dt].istable||false;},remove:function(dt,dn){$(repl('#toolbar-recent li[data-docref="%(dt)s/%(dn)s"]',{dt:dt,dn:dn})).remove();},setup:function(){var rlist=JSON.parse(profile.recent||"[]");var m=rlist.length;if(m>15)m=15;for(var i=0;i<m;i++){var rd=rlist[i]
if(rd[1]){var dt=rd[0];var dn=rd[1];this.add(dt,dn,0);}}}});
/*
 *	lib/js/wn/ui/toolbar/toolbar.js
 */
wn.ui.toolbar.Toolbar=Class.extend({init:function(){this.make();this.make_home();this.make_document();wn.ui.toolbar.recent=new wn.ui.toolbar.RecentDocs();this.make_tools();this.set_user_name();this.make_logout();$('.dropdown-toggle').dropdown();$(document).trigger('toolbar_setup');},make:function(){$('header').append('<div class="navbar navbar-fixed-top">\
   <div class="navbar-inner">\
   <div class="container">\
    <a class="brand"></a>\
    <ul class="nav">\
    </ul>\
    <img src="images/lib/ui/spinner.gif" id="spinner"/>\
    <ul class="nav pull-right">\
     <li class="dropdown">\
      <a class="dropdown-toggle" data-toggle="dropdown" href="#" \
       onclick="return false;" id="toolbar-user-link"></a>\
      <ul class="dropdown-menu" id="toolbar-user">\
      </ul>\
     </li>\
    </ul>\
   </div>\
   </div>\
   </div>');},make_home:function(){$('.navbar .brand').attr('href',"#");},make_document:function(){wn.ui.toolbar.new_dialog=new wn.ui.toolbar.NewDialog();wn.ui.toolbar.search=new wn.ui.toolbar.Search();wn.ui.toolbar.report=new wn.ui.toolbar.Report();$('.navbar .nav:first').append('<li class="dropdown">\
   <a class="dropdown-toggle" href="#"  data-toggle="dropdown"\
    onclick="return false;">Document<b class="caret"></b></a>\
   <ul class="dropdown-menu" id="toolbar-document">\
    <li><a href="#" onclick="return wn.ui.toolbar.new_dialog.show();">\
     <i class="icon-plus"></i> New</a></li>\
    <li><a href="#" onclick="return wn.ui.toolbar.search.show();">\
     <i class="icon-search"></i> Search</a></li>\
    <li><a href="#" onclick="return wn.ui.toolbar.report.show();">\
     <i class="icon-list"></i> Report</a></li>\
   </ul>\
  </li>');},make_tools:function(){$('.navbar .nav:first').append('<li class="dropdown">\
   <a class="dropdown-toggle" data-toggle="dropdown" href="#" \
    onclick="return false;">Tools<b class="caret"></b></a>\
   <ul class="dropdown-menu" id="toolbar-tools">\
    <li><a href="#" onclick="return wn.ui.toolbar.clear_cache();">Clear Cache & Refresh</a></li>\
    <li><a href="#" onclick="return wn.ui.toolbar.show_about();">About</a></li>\
   </ul>\
  </li>');if(has_common(user_roles,['Administrator','System Manager'])){$('#toolbar-tools').append('<li><a href="#" \
    onclick="return wn.ui.toolbar.download_backup();">\
    Download Backup</a></li>');}},set_user_name:function(){var fn=user_fullname;if(fn.length>15)fn=fn.substr(0,12)+'...';$('#toolbar-user-link').html(fn+'<b class="caret"></b>');},make_logout:function(){$('#toolbar-user').append('<li><a href="#" onclick="return wn.app.logout();">Logout</a></li>');}});wn.ui.toolbar.clear_cache=function(){localStorage&&localStorage.clear();$c('webnotes.session_cache.clear',{},function(r,rt){if(!r.exc){show_alert(r.message);location.reload();}});return false;}
wn.ui.toolbar.download_backup=function(){$c('webnotes.utils.backups.get_backup',{},function(r,rt){});return false;}
wn.ui.toolbar.show_about=function(){try{wn.ui.misc.about();}catch(e){console.log(e);}
return false;}

/*
 *	lib/js/wn/views/breadcrumbs.js
 */
wn.provide('wn.views');wn.views.breadcrumbs=function(parent,module,doctype,name){$(parent).empty();var $bspan=$(parent);if(name){$bspan.append('<span class="appframe-title">'+name+'</span>');}else if(doctype){$bspan.append('<span class="appframe-title">'+doctype+' List </span>');}else if(module){$bspan.append('<span class="appframe-title">'+module+'</span>');}
if(name&&doctype&&(!locals['DocType'][doctype].issingle)){$bspan.append(repl('<span> in <a href="#!List/%(doctype)s">%(doctype)s List</a></span>',{doctype:doctype}))};if(doctype&&module&&wn.modules&&wn.modules[module]){$bspan.append(repl('<span> in <a href="#!%(module_page)s">%(module)s</a></span>',{module:module,module_page:wn.modules[module]}))}}
/*
 *	lib/js/legacy/widgets/form/fields.js
 */
var no_value_fields=['Section Break','Column Break','HTML','Table','FlexTable','Button','Image'];var codeid=0;var code_editors={};function Field(){this.with_label=1;}
Field.prototype.make_body=function(){var ischk=(this.df.fieldtype=='Check'?1:0);if(this.parent)
this.wrapper=$a(this.parent,(this.with_label?'div':'span'));else
this.wrapper=document.createElement((this.with_label?'div':'span'));this.label_area=$a(this.wrapper,'div','',{margin:'0px 0px 2px 0px'});if(ischk&&!this.in_grid){this.input_area=$a(this.label_area,'span','',{marginRight:'4px'});this.disp_area=$a(this.label_area,'span','',{marginRight:'4px'});}
if(this.with_label){this.label_span=$a(this.label_area,'span','small')
this.label_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 4px'});$dh(this.label_icon);this.label_icon.src='images/lib/icons/error.gif';this.label_icon.title='Mandatory value needs to be entered';this.suggest_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 0px'});$dh(this.suggest_icon);this.suggest_icon.src='images/lib/icons/bullet_arrow_down.png';this.suggest_icon.title='With suggestions';}else{this.label_span=$a(this.label_area,'span','',{marginRight:'4px'})
$dh(this.label_area);}
if(!this.input_area){this.input_area=$a(this.wrapper,(this.with_label?'div':'span'));this.disp_area=$a(this.wrapper,(this.with_label?'div':'span'));}
if(this.in_grid){if(this.label_area)$dh(this.label_area);}else{this.input_area.className='input_area';$y(this.wrapper,{marginBottom:'9px'});this.set_description();}
if(this.onmake)this.onmake();}
Field.prototype.set_max_width=function(){var no_max=['Code','Text Editor','Text','Table','HTML']
if(this.wrapper&&this.layout_cell&&this.layout_cell.parentNode.cells&&this.layout_cell.parentNode.cells.length==1&&!in_list(no_max,this.df.fieldtype)){$y(this.wrapper,{paddingRight:'50%'});}}
Field.prototype.set_label=function(){if(this.with_label&&this.label_area&&this.label!=this.df.label){this.label_span.innerHTML=this.df.label;this.label=this.df.label;}}
Field.prototype.set_description=function(){if(this.df.description){var p=in_list(['Text Editor','Code','Check'],this.df.fieldtype)?this.label_area:this.wrapper;this.desc_area=$a(p,'div','help small','',this.df.description)
if(in_list(['Text Editor','Code'],this.df.fieldtype))
$(this.desc_area).addClass('help small');}}
Field.prototype.get_status=function(){if(this.in_filter)this.not_in_form=this.in_filter;if(this.not_in_form){return'Write';}
if(!this.df.permlevel)this.df.permlevel=0;var p=this.perm[this.df.permlevel];var ret;if(cur_frm.editable&&p&&p[WRITE])ret='Write';else if(p&&p[READ])ret='Read';else ret='None';if(this.df.fieldtype=='Binary')
ret='None';if(cint(this.df.hidden))
ret='None';if(ret=='Write'&&cint(cur_frm.doc.docstatus)>0)ret='Read';var a_o_s=cint(this.df.allow_on_submit);if(a_o_s&&(this.in_grid||(this.frm&&this.frm.not_in_container))){a_o_s=null;if(this.in_grid)a_o_s=this.grid.field.df.allow_on_submit;if(this.frm&&this.frm.not_in_container){a_o_s=cur_grid.field.df.allow_on_submit;}}
if(cur_frm.editable&&a_o_s&&cint(cur_frm.doc.docstatus)>0&&!this.df.hidden){tmp_perm=get_perm(cur_frm.doctype,cur_frm.docname,1);if(tmp_perm[this.df.permlevel]&&tmp_perm[this.df.permlevel][WRITE])ret='Write';}
return ret;}
Field.prototype.set_style_mandatory=function(add){if(add){$(this.txt?this.txt:this.input).addClass('input-mandatory');if(this.disp_area)$(this.disp_area).addClass('input-mandatory');}else{$(this.txt?this.txt:this.input).removeClass('input-mandatory');if(this.disp_area)$(this.disp_area).removeClass('input-mandatory');}}
Field.prototype.refresh_mandatory=function(){if(this.in_filter)return;if(this.df.reqd){if(this.label_area)this.label_area.style.color="#d22";this.set_style_mandatory(1);}else{if(this.label_area)this.label_area.style.color="#222";this.set_style_mandatory(0);}
this.refresh_label_icon()
this.set_reqd=this.df.reqd;}
Field.prototype.refresh_display=function(){if(!this.current_status||this.current_status!=this.disp_status){if(this.disp_status=='Write'){if(this.make_input&&(!this.input)){this.make_input();if(this.onmake_input)this.onmake_input();}
if(this.show)this.show()
else{$ds(this.wrapper);}
if(this.input){$ds(this.input_area);$dh(this.disp_area);if(this.input.refresh)this.input.refresh();}else{$dh(this.input_area);$ds(this.disp_area);}}else if(this.disp_status=='Read'){if(this.show)this.show()
else{$ds(this.wrapper);}
$dh(this.input_area);$ds(this.disp_area);}else{if(this.hide)this.hide();else $dh(this.wrapper);}
this.current_status=this.disp_status;}}
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
var set_val=val;if(this.validate)set_val=this.validate(val);_f.set_value(this.doctype,this.docname,this.df.fieldname,set_val);this.value=val;}
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
function DataField(){}DataField.prototype=new Field();DataField.prototype.make_input=function(){var me=this;this.input=$a_input(this.input_area,this.df.fieldtype=='Password'?'password':'text');this.get_value=function(){var v=this.input.value;if(this.validate)
v=this.validate(v);return v;}
this.input.name=this.df.fieldname;$(this.input).change(function(){me.set_value(me.get_value?me.get_value():$(this.input).val());});this.set_value=function(val){if(!me.last_value)me.last_value='';if(me.validate){val=me.validate(val);me.input.value=val==undefined?'':val;}
me.set(val);if(me.format_input)
me.format_input();if(in_list(['Currency','Float','Int'],me.df.fieldtype)){if(flt(me.last_value)==flt(val)){me.last_value=val;return;}}
me.last_value=val;me.run_trigger();}
this.input.set_input=function(val){if(val==null)val='';me.input.value=val;if(me.format_input)me.format_input();}
if(this.df.options=='Suggest'){if(this.suggest_icon)$di(this.suggest_icon);$(me.input).autocomplete({source:function(request,response){wn.call({method:'webnotes.widgets.search.search_link',args:{'txt':request.term,'dt':me.df.options,'query':repl('SELECT DISTINCT `%(fieldname)s` FROM \
       `tab%(dt)s` WHERE `%(fieldname)s` LIKE "%s" LIMIT 50',{fieldname:me.df.fieldname,dt:me.df.parent})},callback:function(r){response(r.results);}});},select:function(event,ui){me.set(ui.item.value);}});}}
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
var datepicker_active=0;function DateField(){}DateField.prototype=new Field();DateField.prototype.make_input=function(){var me=this;this.user_fmt=sys_defaults.date_format;if(!this.user_fmt)this.user_fmt='dd-mm-yy';this.input=$a(this.input_area,'input');$(this.input).datepicker({dateFormat:me.user_fmt.replace('yyyy','yy'),altFormat:'yy-mm-dd',changeYear:true,beforeShow:function(input,inst){datepicker_active=1},onClose:function(dateText,inst){datepicker_active=0;if(_f.cur_grid_cell)
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
return v;};function LinkField(){}LinkField.prototype=new Field();LinkField.prototype.make_input=function(){var me=this;if(me.df.no_buttons){this.txt=$a(this.input_area,'input');this.input=this.txt;}else{makeinput_popup(this,'icon-search','icon-play','icon-plus');me.setup_buttons();me.onrefresh=function(){if(me.can_create&&cur_frm.doc.docstatus==0)
$(me.btn2).css('display','inline-block');else $dh(me.btn2);}}
me.txt.field_object=this;me.input.set_input=function(val){if(val==undefined)val='';me.txt.value=val;}
me.get_value=function(){return me.txt.value;}
$(me.txt).autocomplete({source:function(request,response){wn.call({method:'webnotes.widgets.search.search_link',args:{'txt':request.term,'dt':me.df.options,'query':me.get_custom_query()},callback:function(r){response(r.results);},});},select:function(event,ui){me.set_input_value(ui.item.value);}}).data('autocomplete')._renderItem=function(ul,item){return $('<li></li>').data('item.autocomplete',item).append(repl('<a>%(label)s<br><span style="font-size:10px">%(info)s</span></a>',item)).appendTo(ul);};$(this.txt).change(function(){var val=$(this).val();me.set_input_value_executed=false;if(!val){if(selector&&selector.display)
return;me.set_input_value('');}else{setTimeout(function(){if(!me.set_input_value_executed){me.set_input_value(val);}},1000);}})}
LinkField.prototype.get_custom_query=function(){this.set_get_query();if(this.get_query){if(cur_frm)
var doc=locals[cur_frm.doctype][cur_frm.docname];return this.get_query(doc,this.doctype,this.docname);}}
LinkField.prototype.setup_buttons=function(){var me=this;me.btn.onclick=function(){selector.set(me,me.df.options,me.df.label);selector.show(me.txt);}
if(me.btn1)me.btn1.onclick=function(){if(me.txt.value&&me.df.options){loaddoc(me.df.options,me.txt.value);}}
me.can_create=0;if((!me.not_in_form)&&in_list(profile.can_create,me.df.options)){me.can_create=1;me.btn2.onclick=function(){var on_save_callback=function(new_rec){if(new_rec){var d=_f.calling_doc_stack.pop();locals[d[0]][d[1]][me.df.fieldname]=new_rec;me.refresh();if(me.grid)me.grid.refresh();me.run_trigger();}}
_f.calling_doc_stack.push([me.doctype,me.docname]);new_doc(me.df.options,me.on_new,1,on_save_callback,me.doctype,me.docname,me.frm.not_in_container);}}else{$dh(me.btn2);$y($td(me.tab,0,2),{width:'0px'});}}
LinkField.prototype.set_input_value=function(val){var me=this;me.set_input_value_executed=true;var from_selector=false;if(selector&&selector.display)from_selector=true;me.refresh_label_icon();if(me.not_in_form){$(this.txt).val(val);return;}
if(cur_frm){if(val==locals[me.doctype][me.docname][me.df.fieldname]){me.run_trigger();return;}}
me.set(val);if(_f.cur_grid_cell)
_f.cur_grid_cell.grid.cell_deselect();if(locals[me.doctype][me.docname][me.df.fieldname]&&!val){me.run_trigger();return;}
if(val){me.validate_link(val,from_selector);}}
LinkField.prototype.validate_link=function(val,from_selector){var me=this;var fetch='';if(cur_frm.fetch_dict[me.df.fieldname])
fetch=cur_frm.fetch_dict[me.df.fieldname].columns.join(', ');$c('webnotes.widgets.form.utils.validate_link',{'value':val,'options':me.df.options,'fetch':fetch},function(r,rt){if(r.message=='Ok'){if($(me.txt).val()!=val){if((me.grid&&!from_selector)||(!me.grid)){$(me.txt).val(val);}}
if(r.fetch_values)
me.set_fetch_values(r.fetch_values);me.run_trigger();}else{var astr='';if(in_list(profile.can_create,me.df.options))astr=repl('<br><br><span class="link_type" onclick="newdoc(\'%(dt)s\')">Click here</span> to create a new %(dtl)s',{dt:me.df.options,dtl:get_doctype_label(me.df.options)})
msgprint(repl('error:<b>%(val)s</b> is not a valid %(dt)s.<br><br>You must first create a new %(dt)s <b>%(val)s</b> and then select its value. To find an existing %(dt)s, click on the magnifying glass next to the field.%(add)s',{val:me.txt.value,dt:get_doctype_label(me.df.options),add:astr}));me.txt.value='';me.set('');}});}
LinkField.prototype.set_fetch_values=function(fetch_values){var fl=cur_frm.fetch_dict[this.df.fieldname].fields;var changed_fields=[];for(var i=0;i<fl.length;i++){if(locals[this.doctype][this.docname][fl[i]]!=fetch_values[i]){locals[this.doctype][this.docname][fl[i]]=fetch_values[i];if(!this.grid){refresh_field(fl[i]);changed_fields.push(fl[i]);}}}
for(i=0;i<changed_fields.length;i++){if(cur_frm.fields_dict[changed_fields[i]])
cur_frm.fields_dict[changed_fields[i]].run_trigger();}
if(this.grid)this.grid.refresh();}
LinkField.prototype.set_get_query=function(){if(this.get_query)return;if(this.grid){var f=this.grid.get_field(this.df.fieldname);if(f.get_query)this.get_query=f.get_query;}}
LinkField.prototype.set_disp=function(val){var t=null;if(val)t="<a href=\'javascript:loaddoc(\""+this.df.options+"\", \""+val+"\")\'>"+val+"</a>";this.set_disp_html(t);}
function IntField(){}IntField.prototype=new DataField();IntField.prototype.validate=function(v){if(isNaN(parseInt(v)))return null;return cint(v);};IntField.prototype.format_input=function(){if(this.input.value==null)this.input.value='';}
function FloatField(){}FloatField.prototype=new DataField();FloatField.prototype.validate=function(v){var v=parseFloat(v);if(isNaN(v))
return null;return v;};FloatField.prototype.format_input=function(){if(this.input.value==null)this.input.value='';}
function CurrencyField(){}CurrencyField.prototype=new DataField();CurrencyField.prototype.format_input=function(){var v=fmt_money(this.input.value);if(this.not_in_form){if(!flt(this.input.value))v='';}
this.input.value=v;}
CurrencyField.prototype.validate=function(v){if(v==null||v=='')
return 0;return flt(v,2);}
CurrencyField.prototype.set_disp=function(val){var v=fmt_money(val);this.set_disp_html(v);}
CurrencyField.prototype.onmake_input=function(){if(!this.input)return;this.input.onfocus=function(){if(flt(this.value)==0)this.select();}}
function CheckField(){}CheckField.prototype=new Field();CheckField.prototype.validate=function(v){var v=parseInt(v);if(isNaN(v))return 0;return v;};CheckField.prototype.onmake=function(){this.checkimg=$a(this.disp_area,'div');var img=$a(this.checkimg,'img');img.src='images/lib/ui/tick.gif';$dh(this.checkimg);}
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
$a(this.widgets['Description'],'div','help small','',this.field.df.description);}
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
this.set_attach_options();me.options_list=me.df.options?me.df.options.split('\n'):[''];empty_select(this.input);if(me.in_filter&&me.options_list[0]!=''){me.options_list=add_lists([''],me.options_list);}
add_sel_options(this.input,me.options_list);}
this.onrefresh=function(){this.refresh_options();if(this.not_in_form){this.input.value='';return;}
if(_f.get_value)
var v=_f.get_value(this.doctype,this.docname,this.df.fieldname);else{if(this.options_list&&this.options_list.length)
var v=this.options_list[0];else
var v=null;}
this.input.set_input(v);}
this.input.set_input=function(v){if(!v){if(!me.input.multiple){if(me.docname){if(me.options_list&&me.options_list.length){me.set(me.options_list[0]);me.input.value=me.options_list[0];}else{me.input.value='';}}}}else{if(me.options_list){if(me.input.multiple){for(var i=0;i<me.input.options.length;i++){me.input.options[i].selected=0;if(me.input.options[i].value&&inList(typeof(v)=='string'?v.split(","):v,me.input.options[i].value))
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
function makeinput_popup(me,iconsrc,iconsrc1,iconsrc2){var icon_style={cursor:'pointer',width:'16px',verticalAlign:'middle',marginBottom:'-3px'};me.input=$a(me.input_area,'div');if(!me.not_in_form)
$y(me.input,{width:'80%'});me.input.set_width=function(w){$y(me.input,{width:(w-2)+'px'});}
var tab=$a(me.input,'table');me.tab=tab;$y(tab,{width:'100%',borderCollapse:'collapse',tableLayout:'fixed'});var c0=tab.insertRow(0).insertCell(0);var c1=tab.rows[0].insertCell(1);$y(c1,{width:'20px'});me.txt=$a($a($a(c0,'div','',{paddingRight:'8px'}),'div'),'input','',{width:'100%'});me.btn=$a(c1,'i',iconsrc,icon_style)
if(iconsrc1)
me.btn.setAttribute('title','Search');else
me.btn.setAttribute('title','Select Date');if(iconsrc1){var c2=tab.rows[0].insertCell(2);$y(c2,{width:'20px'});me.btn1=$a(c2,'i',iconsrc1,icon_style)
me.btn1.setAttribute('title','Open Link');}
if(iconsrc2){var c3=tab.rows[0].insertCell(3);$y(c3,{width:'20px'});me.btn2=$a(c3,'i',iconsrc2,icon_style)
me.btn2.setAttribute('title','Create New');$dh(me.btn2);}
if(me.df.colour)
me.txt.style.background='#'+me.df.colour.split(':')[1];me.txt.name=me.df.fieldname;me.setdisabled=function(tf){me.txt.disabled=tf;}}
var tmpid=0;_f.ButtonField=function(){};_f.ButtonField.prototype=new Field();_f.ButtonField.prototype.with_label=0;_f.ButtonField.prototype.init=function(){this.prev_button=null;if(!this.frm)return;if(cur_frm&&cur_frm.fields[cur_frm.fields.length-1]&&cur_frm.fields[cur_frm.fields.length-1].df.fieldtype=='Button'){this.make_body=function(){this.prev_button=cur_frm.fields[cur_frm.fields.length-1];if(!this.prev_button.prev_button){this.prev_button.button_area=$a(this.prev_button.input_area,'span');}
this.wrapper=this.prev_button.wrapper;this.input_area=this.prev_button.input_area;this.disp_area=this.prev_button.disp_area;this.button_area=$a(this.prev_button.input_area,'span');}}}
_f.ButtonField.prototype.make_input=function(){var me=this;if(!this.prev_button){$y(this.input_area,{marginTop:'4px',marginBottom:'4px'});}
if(!this.button_area)
this.button_area=$a(this.input_area,'span','',{marginRight:'4px'});this.input=$btn(this.button_area,me.df.label,null,{fontWeight:'bold'},null,1)
$(this.input).click(function(){if(me.not_in_form)return;if(cur_frm.cscript[me.df.fieldname]&&(!me.in_filter)){cur_frm.runclientscript(me.df.fieldname,me.doctype,me.docname);}else{cur_frm.runscript(me.df.options,me);}});}
_f.ButtonField.prototype.hide=function(){$dh(this.button_area);};_f.ButtonField.prototype.show=function(){$ds(this.button_area);};_f.ButtonField.prototype.set=function(v){};_f.ButtonField.prototype.set_disp=function(val){}
function make_field(docfield,doctype,parent,frm,in_grid,hide_label){switch(docfield.fieldtype.toLowerCase()){case'data':var f=new DataField();break;case'password':var f=new DataField();break;case'int':var f=new IntField();break;case'float':var f=new FloatField();break;case'currency':var f=new CurrencyField();break;case'read only':var f=new ReadOnlyField();break;case'link':var f=new LinkField();break;case'date':var f=new DateField();break;case'time':var f=new TimeField();break;case'html':var f=new HTMLField();break;case'check':var f=new CheckField();break;case'text':var f=new TextField();break;case'small text':var f=new TextField();break;case'select':var f=new SelectField();break;case'button':var f=new _f.ButtonField();break;case'code':var f=new _f.CodeField();break;case'text editor':var f=new _f.CodeField();break;case'table':var f=new _f.TableField();break;case'section break':var f=new _f.SectionBreak();break;case'column break':var f=new _f.ColumnBreak();break;case'image':var f=new _f.ImageField();break;}
f.parent=parent;f.doctype=doctype;f.df=docfield;f.perm=frm?frm.perm:[[1,1,1]];if(_f)
f.col_break_width=_f.cur_col_break_width;if(in_grid){f.in_grid=true;f.with_label=0;}
if(hide_label){f.with_label=0;}
if(frm){f.frm=frm;if(parent)
f.layout_cell=parent.parentNode;}
if(f.init)f.init();f.make_body();return f;}
/*
 *	lib/js/legacy/widgets/form/form_dialog.js
 */
_f.frm_dialog=null;_f.calling_doc_stack=[];_f.temp_access={};_f.FrmDialog=function(){var me=this;this.last_displayed=null;var d=new Dialog(640,null,'Edit Row');this.body=$a(d.body,'div','dialog_frm');d.done_btn_area=$a(d.body,'div','',{margin:'8px'});me.on_complete=function(){if(me.table_form){me.dialog.hide();}else{var callback=function(r){var dn=cur_frm.docname;if(!r.exc){me.dialog.hide();}
if(me.on_save_callback)
me.on_save_callback(dn);}
cur_frm.save('Save',callback);}}
d.onshow=function(){d.done_btn_area.innerHTML='';d.done_btn=$btn(d.done_btn_area,'Save',null,null,'green');d.done_btn.onclick=function(){me.on_complete()};if(me.table_form){d.set_title("Editing Row #"+(_f.cur_grid_ridx+1));d.done_btn.innerHTML='Done Editing';}else{d.set_title(cur_frm.doctype==cur_frm.doctype?(cur_frm.doctype):(cur_frm.doctype+': '+cur_frm.docname));d.done_btn.innerHTML='Save';}}
d.onhide=function(){if(_f.cur_grid){_f.cur_grid.refresh_row(_f.cur_grid_ridx,me.dn);}
if(wn.container.page.frm){cur_frm=wn.container.page.frm;}
if(me.cur_frm.cscript.hide_dialog){me.cur_frm.cscript.hide_dialog();}
$(me.cur_frm.page_layout.wrapper).toggle(false);}
this.dialog=d;}
_f.edit_record=function(dt,dn){if(!_f.frm_dialog){_f.frm_dialog=new _f.FrmDialog();}
var d=_f.frm_dialog;wn.model.with_doctype(dt,function(){wn.model.with_doc(dt,dn,function(dn){if(!_f.frms[dt]){_f.frms[dt]=new _f.Frm(dt,d.body);}
var f=_f.frms[dt];if(f.meta.istable){f.parent_doctype=cur_frm.doctype;f.parent_docname=cur_frm.docname;}
d.cur_frm=f;d.dn=dn;d.table_form=f.meta.istable;f.refresh(dn);$(f.page_layout.wrapper).removeClass('layout-wrapper').removeClass('layout-wrapper-background').toggle(true);d.dialog.show();})})}
/*
 *	lib/js/legacy/widgets/form/form_header.js
 */
_f.FrmHeader=Class.extend({init:function(parent,frm){this.appframe=new wn.ui.AppFrame(parent)
this.appframe.$titlebar.append('</span>\
    <span class="breadcrumb-area"></span>');this.$w=this.appframe.$w;},refresh:function(){wn.views.breadcrumbs($(this.$w.find('.breadcrumb-area')),cur_frm.meta.module,cur_frm.meta.name,cur_frm.docname);this.refresh_labels();this.refresh_toolbar();},refresh_labels:function(){var labinfo={0:['Saved','label-success'],1:['Submitted','label-info'],2:['Cancelled','label-important']}[cint(cur_frm.doc.docstatus)];if(labinfo[0]=='Saved'&&cur_frm.meta.is_submittable){labinfo[0]='Saved, to Submit';}
if(cur_frm.doc.__unsaved||cur_frm.doc.__islocal){labinfo[0]='Not Saved';labinfo[1]='label-warning'}
this.set_label(labinfo);if(cur_frm.doc.__unsaved&&cint(cur_frm.doc.docstatus)==1&&this.appframe.buttons['Update']){this.appframe.buttons['Update'].toggle(true);}},set_label:function(labinfo){this.$w.find('.label').remove();$(repl('<span class="label %(lab_class)s">\
   %(lab_status)s</span>',{lab_status:labinfo[0],lab_class:labinfo[1]})).insertBefore(this.$w.find('.breadcrumb-area'))},refresh_toolbar:function(){this.appframe.clear_buttons();var p=cur_frm.get_doc_perms();if(cur_frm.meta.read_only_onload&&!cur_frm.doc.__islocal){if(!cur_frm.editable)
this.appframe.add_button('Edit',function(){cur_frm.edit_doc();},'icon-pencil');else
this.appframe.add_button('Print View',function(){cur_frm.is_editable[cur_frm.docname]=0;cur_frm.refresh();},'icon-print');}
var docstatus=cint(cur_frm.doc.docstatus);if(docstatus==0&&p[WRITE]){this.appframe.add_button('Save',function(){cur_frm.save('Save');},'');this.appframe.buttons['Save'].addClass('btn-info');}
if(docstatus==0&&p[SUBMIT]&&(!cur_frm.doc.__islocal))
this.appframe.add_button('Submit',function(){cur_frm.savesubmit();},'icon-lock');if(docstatus==1&&p[SUBMIT]){this.appframe.add_button('Update',function(){cur_frm.saveupdate();},'');if(!cur_frm.doc.__unsaved)this.appframe.buttons['Update'].toggle(false);}
if(docstatus==1&&p[CANCEL])
this.appframe.add_button('Cancel',function(){cur_frm.savecancel()},'icon-remove');if(docstatus==2&&p[AMEND])
this.appframe.add_button('Amend',function(){cur_frm.amend_doc()},'icon-pencil');},show:function(){},hide:function(){},hide_close:function(){this.$w.find('.close').toggle(false);}})
/*
 *	lib/js/legacy/widgets/form/form.js
 */
wn.provide('_f');_f.frms={};_f.Frm=function(doctype,parent,in_form){this.docname='';this.doctype=doctype;this.display=0;var me=this;this.is_editable={};this.opendocs={};this.sections=[];this.grids=[];this.cscript={};this.pformat={};this.fetch_dict={};this.parent=parent;this.tinymce_id_list=[];this.setup_meta(doctype);this.in_form=in_form?true:false;var me=this;$(document).bind('rename',function(event,dt,old_name,new_name){if(dt==me.doctype)
me.rename_notify(dt,old_name,new_name)});}
_f.Frm.prototype.check_doctype_conflict=function(docname){var me=this;if(this.doctype=='DocType'&&docname=='DocType'){msgprint('Allowing DocType, DocType. Be careful!')}else if(this.doctype=='DocType'){if(wn.views.formview[docname]||wn.pages['List/'+docname]){msgprint("Cannot open DocType when its instance is open")
throw'doctype open conflict'}}else{if(wn.views.formview.DocType&&wn.views.formview.DocType.frm.opendocs[this.doctype]){msgprint("Cannot open instance when its DocType is open")
throw'doctype open conflict'}}}
_f.Frm.prototype.setup=function(){var me=this;this.fields=[];this.fields_dict={};this.wrapper=this.parent;this.setup_print_layout();this.saved_wrapper=$a(this.wrapper,'div');this.setup_std_layout();this.setup_client_script();this.setup_done=true;}
_f.Frm.prototype.setup_print_layout=function(){this.print_wrapper=$a(this.wrapper,'div');this.print_head=$a(this.print_wrapper,'div');this.print_body=$a(this.print_wrapper,'div','layout_wrapper',{padding:'23px',minHeight:'800px'});var t=make_table(this.print_head,1,2,'100%',[],{padding:'6px'});this.view_btn_wrapper=$a($td(t,0,0),'span','green_buttons');this.view_btn=$btn(this.view_btn_wrapper,'View Details',function(){cur_frm.edit_doc()},{marginRight:'4px'},'green');this.print_btn=$btn($td(t,0,0),'Print',function(){cur_frm.print_doc()});$y($td(t,0,1),{textAlign:'right'});this.print_close_btn=$btn($td(t,0,1),'Close',function(){window.history.back();});}
_f.Frm.prototype.onhide=function(){if(_f.cur_grid_cell)_f.cur_grid_cell.grid.cell_deselect();}
_f.Frm.prototype.setup_std_layout=function(){this.page_layout=new wn.PageLayout({parent:this.wrapper,main_width:(this.meta.in_dialog&&!this.in_form)?'100%':'75%',sidebar_width:(this.meta.in_dialog&&!this.in_form)?'0%':'25%'})
this.meta.section_style='Simple';this.layout=new Layout(this.page_layout.body,'100%');if(this.meta.in_dialog&&!this.in_form){$(this.page_layout.wrapper).removeClass('layout-wrapper-background');$(this.page_layout.main).removeClass('layout-main-section');$(this.page_layout.sidebar_area).toggle(false);}else{this.setup_sidebar();}
this.setup_footer();if(!(this.meta.istable||user=='Guest'||(this.meta.in_dialog&&!this.in_form)))
this.frm_head=new _f.FrmHeader(this.page_layout.head,this);if(this.meta.colour)
this.layout.wrapper.style.backgroundColor='#'+this.meta.colour.split(':')[1];this.setup_fields_std();}
_f.Frm.prototype.setup_print=function(){var l=[]
this.default_format='Standard';for(var key in locals['Print Format']){if(locals['Print Format'][key].doc_type==this.meta.name){l.push(locals['Print Format'][key].name);}}
if(this.meta.default_print_format)
this.default_format=this.meta.default_print_format;l.push('Standard');this.print_sel=$a(null,'select','',{width:'160px'});add_sel_options(this.print_sel,l);this.print_sel.value=this.default_format;}
_f.Frm.prototype.print_doc=function(){if(this.doc.docstatus==2){msgprint("Cannot Print Cancelled Documents.");return;}
_p.show_dialog();}
_f.Frm.prototype.email_doc=function(){if(!_e.dialog)_e.make();_e.dialog.widgets['To'].value='';if(cur_frm.doc&&cur_frm.doc.contact_email){_e.dialog.widgets['To'].value=cur_frm.doc.contact_email;}
sel=this.print_sel;var c=$td(_e.dialog.rows['Format'].tab,0,1);if(c.cur_sel){c.removeChild(c.cur_sel);c.cur_sel=null;}
c.appendChild(this.print_sel);c.cur_sel=this.print_sel;_e.dialog.widgets['Send With Attachments'].checked=0;if(cur_frm.doc.file_list){$ds(_e.dialog.rows['Send With Attachments']);}else{$dh(_e.dialog.rows['Send With Attachments']);}
_e.dialog.widgets['Subject'].value=get_doctype_label(this.meta.name)+': '+this.docname;_e.dialog.show();}
_f.Frm.prototype.rename_notify=function(dt,old,name){if(this.meta.in_dialog&&!this.in_form)
return;if(this.docname==old)
this.docname=name;else
return;this.is_editable[name]=this.is_editable[old];delete this.is_editable[old];if(this&&this.opendocs[old]){local_dt[dt][name]=local_dt[dt][old];local_dt[dt][old]=null;}
delete this.opendocs[old];this.opendocs[name]=true;wn.re_route[window.location.hash]='#Form/'+encodeURIComponent(this.doctype)+'/'+encodeURIComponent(name);wn.set_route('Form',this.doctype,name);}
_f.Frm.prototype.setup_meta=function(doctype){this.meta=get_local('DocType',this.doctype);this.perm=get_perm(this.doctype);if(this.meta.istable){this.meta.in_dialog=1}
this.setup_print();}
_f.Frm.prototype.setup_sidebar=function(){this.sidebar=new wn.widgets.form.sidebar.Sidebar(this);}
_f.Frm.prototype.setup_footer=function(){var me=this;var f=this.page_layout.footer;f.save_area=$a(this.page_layout.footer,'div','',{display:'none',marginTop:'11px'});f.help_area=$a(this.page_layout.footer,'div');var b=$btn(f.save_area,'Save',function(){cur_frm.save('Save');},{marginLeft:'0px'},'green');f.show_save=function(){$ds(me.page_layout.footer.save_area);}
f.hide_save=function(){$dh(me.page_layout.footer.save_area);}}
_f.Frm.prototype.setup_fields_std=function(){var fl=wn.meta.docfield_list[this.doctype];fl.sort(function(a,b){return a.idx-b.idx});if(fl[0]&&fl[0].fieldtype!="Section Break"||get_url_arg('embed')){this.layout.addrow();if(fl[0].fieldtype!="Column Break"){var c=this.layout.addcell();$y(c.wrapper,{padding:'8px'});}}
var sec;for(var i=0;i<fl.length;i++){var f=fl[i];if(f.fieldtype=='Section Break'&&fl[i+1]&&fl[i+1].fieldtype=='Section Break')
continue;var fn=f.fieldname?f.fieldname:f.label;var fld=make_field(f,this.doctype,this.layout.cur_cell,this);this.fields[this.fields.length]=fld;this.fields_dict[fn]=fld;if(sec&&['Section Break','Column Break'].indexOf(f.fieldtype)==-1){fld.parent_section=sec;sec.fields.push(fld);}
if(f.fieldtype=='Section Break'){sec=fld;this.sections.push(fld);}
if((f.fieldtype=='Section Break')&&(fl[i+1])&&(fl[i+1].fieldtype!='Column Break')&&!f.hidden){var c=this.layout.addcell();$y(c.wrapper,{padding:'8px'});}}}
_f.Frm.prototype.add_custom_button=function(label,fn,icon){this.frm_head.appframe.add_button(label,fn,icon);}
_f.Frm.prototype.clear_custom_buttons=function(){this.frm_head.refresh_toolbar()}
_f.Frm.prototype.add_fetch=function(link_field,src_field,tar_field){if(!this.fetch_dict[link_field]){this.fetch_dict[link_field]={'columns':[],'fields':[]}}
this.fetch_dict[link_field].columns.push(src_field);this.fetch_dict[link_field].fields.push(tar_field);}
_f.Frm.prototype.setup_client_script=function(){if(this.meta.client_script_core||this.meta.client_script||this.meta.__js){this.runclientscript('setup',this.doctype,this.docname);}}
_f.Frm.prototype.refresh_print_layout=function(){$ds(this.print_wrapper);$dh(this.page_layout.wrapper);var me=this;var print_callback=function(print_html){me.print_body.innerHTML=print_html;}
if(cur_frm.doc.select_print_heading)
cur_frm.set_print_heading(cur_frm.doc.select_print_heading)
if(user!='Guest'){$di(this.view_btn_wrapper);if(cur_frm.doc.__archived){$dh(this.view_btn_wrapper);}}else{$dh(this.view_btn_wrapper);$dh(this.print_close_btn);}
_p.build(this.default_format,print_callback,null,1);}
_f.Frm.prototype.show_the_frm=function(){if(this.meta.in_dialog&&!this.parent.dialog.display){if(!this.meta.istable)
this.parent.table_form=false;this.parent.dialog.show();}}
_f.Frm.prototype.set_print_heading=function(txt){this.pformat[cur_frm.docname]=txt;}
_f.Frm.prototype.defocus_rest=function(){if(_f.cur_grid_cell)_f.cur_grid_cell.grid.cell_deselect();}
_f.Frm.prototype.get_doc_perms=function(){var p=[0,0,0,0,0,0];for(var i=0;i<this.perm.length;i++){if(this.perm[i]){if(this.perm[i][READ])p[READ]=1;if(this.perm[i][WRITE])p[WRITE]=1;if(this.perm[i][SUBMIT])p[SUBMIT]=1;if(this.perm[i][CANCEL])p[CANCEL]=1;if(this.perm[i][AMEND])p[AMEND]=1;}}
return p;}
_f.Frm.prototype.refresh_header=function(){if(!this.meta.in_dialog||this.in_form){set_title(this.meta.issingle?this.doctype:this.docname);}
if(this.frm_head)this.frm_head.refresh();if(wn.ui.toolbar.recent)
wn.ui.toolbar.recent.add(this.doctype,this.docname,1);}
_f.Frm.prototype.check_doc_perm=function(){var dt=this.parent_doctype?this.parent_doctype:this.doctype;var dn=this.parent_docname?this.parent_docname:this.docname;this.perm=get_perm(dt,dn);this.orig_perm=get_perm(dt,dn,1);if(!this.perm[0][READ]){if(user=='Guest'){if(_f.temp_access[dt]&&_f.temp_access[dt][dn]){this.perm=[[1,0,0]]
return 1;}}
window.history.back();return 0;}
return 1}
_f.Frm.prototype.refresh=function(docname){if(docname){if(this.docname!=docname&&(!this.meta.in_dialog||this.in_form)&&!this.meta.istable)scroll(0,0);this.docname=docname;}
if(!this.meta.istable){cur_frm=this;this.parent.cur_frm=this;}
if(this.docname){if(!this.check_doc_perm())return;if(!this.opendocs[this.docname]){this.check_doctype_conflict(this.docname);}
if(!this.setup_done)this.setup();this.runclientscript('set_perm',this.doctype,this.docname);this.doc=get_local(this.doctype,this.docname);cur_frm.cscript.is_onload=false;if(!this.opendocs[this.docname]){cur_frm.cscript.is_onload=true;this.setnewdoc(this.docname);}
if(this.doc.__islocal)
this.is_editable[this.docname]=1;this.editable=this.is_editable[this.docname];if(!this.doc.__archived&&(this.editable||(!this.editable&&this.meta.istable))){if(this.print_wrapper){$dh(this.print_wrapper);$ds(this.page_layout.wrapper);}
if(!this.meta.istable){this.refresh_header();this.sidebar&&this.sidebar.refresh();}
this.runclientscript('refresh');$(document).trigger('form_refresh');this.refresh_fields();this.refresh_dependency();this.refresh_footer();if(this.layout)this.layout.show();if(cur_frm.cscript.is_onload){this.runclientscript('onload_post_render',this.doctype,this.docname);}
if(this.doc.docstatus==0){$(this.wrapper).find('.form-layout-row :input:first').focus();}}else{this.refresh_header();if(this.print_wrapper){this.refresh_print_layout();}
this.runclientscript('edit_status_changed');}
$(cur_frm.wrapper).trigger('render_complete');}}
_f.Frm.prototype.refresh_footer=function(){var f=this.page_layout.footer;if(f.save_area){if(get_url_arg('embed')||(this.editable&&(!this.meta.in_dialog||this.in_form)&&this.doc.docstatus==0&&!this.meta.istable&&this.get_doc_perms()[WRITE])){f.show_save();}else{f.hide_save();}}}
_f.Frm.prototype.refresh_fields=function(){for(var i=0;i<this.fields.length;i++){var f=this.fields[i];f.perm=this.perm;f.docname=this.docname;var fn=f.df.fieldname||f.df.label;if(fn)
f.df=get_field(this.doctype,fn,this.docname);if(f.df.fieldtype!='Section Break'&&f.refresh){f.refresh();}}
$.each(this.sections,function(i,f){f.refresh(true);})
this.cleanup_refresh(this);}
_f.Frm.prototype.cleanup_refresh=function(){var me=this;if(me.fields_dict['amended_from']){if(me.doc.amended_from){unhide_field('amended_from');unhide_field('amendment_date');}else{hide_field('amended_from');hide_field('amendment_date');}}
if(me.fields_dict['trash_reason']){if(me.doc.trash_reason&&me.doc.docstatus==2){unhide_field('trash_reason');}else{hide_field('trash_reason');}}
if(me.meta.autoname&&me.meta.autoname.substr(0,6)=='field:'&&!me.doc.__islocal){var fn=me.meta.autoname.substr(6);set_field_permlevel(fn,1);}}
_f.Frm.prototype.refresh_dependency=function(){var me=this;var doc=locals[this.doctype][this.docname];var has_dep=false;for(fkey in me.fields){var f=me.fields[fkey];f.dependencies_clear=true;if(f.df.depends_on){has_dep=true;}}
if(!has_dep)return;for(var i=me.fields.length-1;i>=0;i--){var f=me.fields[i];f.guardian_has_value=true;if(f.df.depends_on){var v=doc[f.df.depends_on];if(f.df.depends_on.substr(0,5)=='eval:'){f.guardian_has_value=eval(f.df.depends_on.substr(5));}else if(f.df.depends_on.substr(0,3)=='fn:'){f.guardian_has_value=me.runclientscript(f.df.depends_on.substr(3),me.doctype,me.docname);}else{if(v||(v==0&&!v.substr)){}else{f.guardian_has_value=false;}}
if(f.guardian_has_value){f.df.hidden=0;f.refresh()}else{f.df.hidden=1;f.refresh()}}}}
_f.Frm.prototype.setnewdoc=function(docname){if(this.opendocs[docname]){this.docname=docname;return;}
Meta.make_local_dt(this.doctype,docname);this.docname=docname;var me=this;var viewname=docname;if(this.meta.issingle)viewname=this.doctype;this.runclientscript('onload',this.doctype,this.docname);this.is_editable[docname]=1;if(this.meta.read_only_onload)this.is_editable[docname]=0;this.opendocs[docname]=true;}
_f.Frm.prototype.edit_doc=function(){this.is_editable[this.docname]=true;this.refresh();}
_f.Frm.prototype.show_doc=function(dn){this.refresh(dn);}
var validated;_f.Frm.prototype.save=function(save_action,call_back){if(!save_action)save_action='Save';var me=this;if(this.savingflag){msgprint("Document is currently saving....");return;}
if(save_action=='Submit'){locals[this.doctype][this.docname].submitted_on=dateutil.full_str();locals[this.doctype][this.docname].submitted_by=user;}
if(save_action=='Trash'){var reason=prompt('Reason for trash (mandatory)','');if(!strip(reason)){msgprint('Reason is mandatory, not trashed');return;}
locals[this.doctype][this.docname].trash_reason=reason;}
if(save_action=='Cancel'){var reason=prompt('Reason for cancellation (mandatory)','');if(!strip(reason)){msgprint('Reason is mandatory, not cancelled');return;}
locals[this.doctype][this.docname].cancel_reason=reason;locals[this.doctype][this.docname].cancelled_on=dateutil.full_str();locals[this.doctype][this.docname].cancelled_by=user;}else if(save_action=='Update'){}else{validated=true;if(this.cscript.validate)
this.runclientscript('validate',this.doctype,this.docname);if(!validated){this.savingflag=false;return'Error';}}
var ret_fn=function(r){me.savingflag=false;if(user=='Guest'&&!r.exc){$dh(me.page_layout.wrapper);$ds(me.saved_wrapper);me.saved_wrapper.innerHTML='<div style="padding: 150px 16px; text-align: center; font-size: 14px;">'
+(cur_frm.message_after_save?cur_frm.message_after_save:'Your information has been sent. Thank you!')
+'</div>';return;}
if(!me.meta.istable){me.refresh(r.docname);}
if(call_back){call_back(r);}}
var me=this;var ret_fn_err=function(r){var doc=locals[me.doctype][me.docname];me.savingflag=false;ret_fn(r);}
this.savingflag=true;if(this.docname&&validated){scroll(0,0);return this.savedoc(save_action,ret_fn,ret_fn_err);}}
_f.Frm.prototype.runscript=function(scriptname,callingfield,onrefresh){var me=this;if(this.docname){var doclist=compress_doclist(make_doclist(this.doctype,this.docname));if(callingfield)
$(callingfield.input).set_working();$c('runserverobj',{'docs':doclist,'method':scriptname},function(r,rtxt){if(onrefresh)
onrefresh(r,rtxt);me.refresh_fields();me.refresh_dependency();if(callingfield)
$(callingfield.input).done_working();});}}
_f.Frm.prototype.runclientscript=function(caller,cdt,cdn){var _dt=this.parent_doctype?this.parent_doctype:this.doctype;var _dn=this.parent_docname?this.parent_docname:this.docname;var doc=get_local(_dt,_dn);if(!cdt)cdt=this.doctype;if(!cdn)cdn=this.docname;var ret=null;try{if(this.cscript[caller])
ret=this.cscript[caller](doc,cdt,cdn);if(this.cscript['custom_'+caller])
ret+=this.cscript['custom_'+caller](doc,cdt,cdn);}catch(e){console.log(e);}
if(caller&&caller.toLowerCase()=='setup'){var doctype=get_local('DocType',this.doctype);var cs=doctype.__js||(doctype.client_script_core+doctype.client_script);if(cs){try{var tmp=eval(cs);}catch(e){console.log(e);}}
if(doctype.__css)set_style(doctype.__css)
if(doctype.client_string){this.cstring={};var elist=doctype.client_string.split('---');for(var i=1;i<elist.length;i=i+2){this.cstring[strip(elist[i])]=elist[i+1];}}}
return ret;}
_f.Frm.prototype.copy_doc=function(onload,from_amend){if(!this.perm[0][CREATE]){msgprint('You are not allowed to create '+this.meta.name);return;}
var dn=this.docname;var newdoc=LocalDB.copy(this.doctype,dn,from_amend);if(this.meta.allow_attach&&newdoc.file_list&&!from_amend)
newdoc.file_list=null;var dl=make_doclist(this.doctype,dn);var tf_dict={};for(var d in dl){d1=dl[d];if(!tf_dict[d1.parentfield]){tf_dict[d1.parentfield]=get_field(d1.parenttype,d1.parentfield);}
if(d1.parent==dn&&cint(tf_dict[d1.parentfield].no_copy)!=1){var ch=LocalDB.copy(d1.doctype,d1.name,from_amend);ch.parent=newdoc.name;ch.docstatus=0;ch.owner=user;ch.creation='';ch.modified_by=user;ch.modified='';}}
newdoc.__islocal=1;newdoc.docstatus=0;newdoc.owner=user;newdoc.creation='';newdoc.modified_by=user;newdoc.modified='';if(onload)onload(newdoc);loaddoc(newdoc.doctype,newdoc.name);}
_f.Frm.prototype.reload_doc=function(){this.check_doctype_conflict(this.docname);var me=this;var ret_fn=function(r,rtxt){me.runclientscript('setup',me.doctype,me.docname);me.refresh();}
if(me.doc.__islocal){$c('webnotes.widgets.form.load.getdoctype',{'doctype':me.doctype},ret_fn,null,null,'Refreshing '+me.doctype+'...');}else{$c('webnotes.widgets.form.load.getdoc',{'name':me.docname,'doctype':me.doctype,'getdoctype':1,'user':user},ret_fn,null,null,'Refreshing '+me.docname+'...');}}
_f.Frm.prototype.savedoc=function(save_action,onsave,onerr){this.error_in_section=0;save_doclist(this.doctype,this.docname,save_action,onsave,onerr);}
_f.Frm.prototype.saveupdate=function(){this.save('Update');}
_f.Frm.prototype.savesubmit=function(){var answer=confirm("Permanently Submit "+this.docname+"?");var me=this;if(answer){this.save('Submit',function(r){if(!r.exc&&me.cscript.on_submit){me.runclientscript('on_submit',me.doctype,me.docname);}});}}
_f.Frm.prototype.savecancel=function(){var answer=confirm("Permanently Cancel "+this.docname+"?");if(answer)this.save('Cancel');}
_f.Frm.prototype.savetrash=function(){var me=this;var answer=confirm("Permanently Delete "+this.docname+"? This action cannot be reversed");if(answer){$c('webnotes.model.delete_doc',{dt:this.doctype,dn:this.docname},function(r,rt){if(r.message=='okay'){LocalDB.delete_doc(me.doctype,me.docname);if(wn.ui.toolbar.recent)wn.ui.toolbar.recent.remove(me.doctype,me.docname);window.history.back();}})}}
_f.Frm.prototype.amend_doc=function(){if(!this.fields_dict['amended_from']){alert('"amended_from" field must be present to do an amendment.');return;}
var me=this;var fn=function(newdoc){newdoc.amended_from=me.docname;if(me.fields_dict&&me.fields_dict['amendment_date'])
newdoc.amendment_date=dateutil.obj_to_str(new Date());}
this.copy_doc(fn,1);}
_f.get_value=function(dt,dn,fn){if(locals[dt]&&locals[dt][dn])
return locals[dt][dn][fn];}
_f.set_value=function(dt,dn,fn,v){var d=locals[dt][dn];if(!d){console.log('_f.set_value - '+fn+': "'+dt+','+dn+'" not found');return;}
var changed=d[fn]!=v;if(changed&&(d[fn]==null||v==null)&&(cstr(d[fn])==cstr(v)))changed=0;if(changed){var prev_unsaved=d.__unsaved
d[fn]=v;d.__unsaved=1;if(d.parent&&d.parenttype){var doc=locals[d.parenttype][d.parent];doc.__unsaved=1;var frm=wn.views.formview[d.parenttype].frm;}else{var doc=locals[d.doctype][d.name]
doc.__unsaved=1;var frm=wn.views.formview[d.doctype]&&wn.views.formview[d.doctype].frm;}
if(frm&&frm==cur_frm&&frm.frm_head&&!prev_unsaved){frm.frm_head.refresh_labels();}}}
_f.Frm.prototype.show_comments=function(){if(!cur_frm.comments){cur_frm.comments=new Dialog(540,400,'Comments');cur_frm.comments.comment_body=$a(cur_frm.comments.body,'div','dialog_frm');$y(cur_frm.comments.body,{backgroundColor:'#EEE'});cur_frm.comments.list=new CommentList(cur_frm.comments.comment_body);}
cur_frm.comments.list.dt=cur_frm.doctype;cur_frm.comments.list.dn=cur_frm.docname;cur_frm.comments.show();cur_frm.comments.list.run();}
/*
 *	lib/js/legacy/widgets/form/form_fields.js
 */
_f.ColumnBreak=function(){this.set_input=function(){};}
_f.ColumnBreak.prototype.make_body=function(){if((!this.perm[this.df.permlevel])||(!this.perm[this.df.permlevel][READ])){return;}
this.cell=this.frm.layout.addcell(this.df.width);$y(this.cell.wrapper,{padding:'8px'});_f.cur_col_break_width=this.df.width;var fn=this.df.fieldname?this.df.fieldname:this.df.label;if(this.df&&this.df.label){this.label=$a(this.cell.wrapper,'div','','',this.df.label);}}
_f.ColumnBreak.prototype.refresh=function(layout){if(!this.cell)return;if(this.set_hidden!=this.df.hidden){if(this.df.hidden)
this.cell.hide();else
this.cell.show();this.set_hidden=this.df.hidden;}}
_f.SectionBreak=function(){this.fields=[];this.set_input=function(){};this.make_row=function(){this.row=this.df.label?this.frm.layout.addrow():this.frm.layout.addsubrow();}}
_f.SectionBreak.prototype.make_body=function(){var me=this;if((!this.perm[this.df.permlevel])||(!this.perm[this.df.permlevel][READ])){return;}
this.make_row();if(this.df.label){if(!this.df.description)
this.df.description='';$(this.row.main_head).html(repl('<div class="form-section-head">\
    <h3 class="head">%(label)s</h3>\
    <div class="help small" \
     style="margin-top: 4px; margin-bottom: 8px;">%(description)s</div>\
   </div>',this.df));}else{$(this.wrapper).html('<div class="form-section-head"></div>');}
this.section_collapse=function(){$(me.row.main_head).find('.head').html('<i class="icon-chevron-right"></i> \
    <a href="#" onclick="return false;">Show "'+me.df.label+'"</a>');$(me.row.main_body).toggle(false);}
this.section_expand=function(no_animation){$(me.row.main_head).find('.head').html('<h3><i class="icon-chevron-down" style="vertical-align: middle; margin-bottom: 2px"></i> '
+me.df.label+'</h3>');if(no_animation)
$(me.row.main_body).toggle(true);else
$(me.row.main_body).slideDown();}}
_f.SectionBreak.prototype.has_data=function(){var me=this;for(var i in me.fields){var f=me.fields[i];var v=f.get_value?f.get_value():null;defaultval=f.df['default']||sys_defaults[f.fieldname]||user_defaults[f.fieldname];if(v&&v!=defaultval){return true;}
if(f.df.reqd&&!v){return true;}
if(f.df.fieldtype=='Table'){if(f.grid.get_children().length||f.df.reqd){return true;}}}
return false;}
_f.SectionBreak.prototype.refresh=function(from_form){if(this.df.hidden){if(this.row)this.row.hide();}else{if(this.row)this.row.show();}}
_f.ImageField=function(){this.images={};}
_f.ImageField.prototype=new Field();_f.ImageField.prototype.onmake=function(){this.no_img=$a(this.wrapper,'div','no_img');this.no_img.innerHTML="No Image";$dh(this.no_img);}
_f.ImageField.prototype.get_image_src=function(doc){if(doc.file_list){file=doc.file_list.split(',');extn=file[0].split('.');extn=extn[extn.length-1].toLowerCase();var img_extn_list=['gif','jpg','bmp','jpeg','jp2','cgm','ief','jpm','jpx','png','tiff','jpe','tif'];if(in_list(img_extn_list,extn)){var src=wn.request.url+"?cmd=downloadfile&file_id="+file[1];}}else{var src="";}
return src;}
_f.ImageField.prototype.onrefresh=function(){var me=this;if(!this.images[this.docname])this.images[this.docname]=$a(this.wrapper,'img');else $di(this.images[this.docname]);var img=this.images[this.docname]
for(var dn in this.images)if(dn!=this.docname)$dh(this.images[dn]);var doc=locals[this.frm.doctype][this.frm.docname];if(!this.df.options)var src=this.get_image_src(doc);else var src=wn.request.url+'?cmd=get_file&fname='+this.df.options+"&__account="+account_id+(__sid150?("&sid150="+__sid150):'');if(src){$dh(this.no_img);if(img.getAttribute('src')!=src)img.setAttribute('src',src);canvas=this.wrapper;canvas.img=this.images[this.docname];canvas.style.overflow="auto";$w(canvas,"100%");if(!this.col_break_width)this.col_break_width='100%';var allow_width=cint(1000*(cint(this.col_break_width)-10)/100);if((!img.naturalWidth)||cint(img.naturalWidth)>allow_width)
$w(img,allow_width+'px');}else{$ds(this.no_img);}}
_f.ImageField.prototype.set_disp=function(val){}
_f.ImageField.prototype.set=function(val){}
_f.TableField=function(){};_f.TableField.prototype=new Field();_f.TableField.prototype.with_label=0;_f.TableField.prototype.make_body=function(){if(this.perm[this.df.permlevel]&&this.perm[this.df.permlevel][READ]){if(this.df.description){this.desc_area=$a(this.parent,'div','help small','',this.df.description)}
this.grid=new _f.FormGrid(this);if(this.frm)this.frm.grids[this.frm.grids.length]=this;this.grid.make_buttons();}}
_f.TableField.prototype.refresh=function(){if(!this.grid)return;var st=this.get_status();if(!this.df['default'])
this.df['default']='';this.grid.can_add_rows=false;this.grid.can_edit=false
if(st=='Write'){if(cur_frm.editable&&this.perm[this.df.permlevel]&&this.perm[this.df.permlevel][WRITE]){this.grid.can_edit=true;if(this.df['default'].toLowerCase()!='no toolbar')
this.grid.can_add_rows=true;}
if(cur_frm.editable&&cur_frm.doc.docstatus>0){if(this.df.allow_on_submit&&cur_frm.doc.docstatus==1){this.grid.can_edit=true;if(this.df['default'].toLowerCase()=='no toolbar'){this.grid.can_add_rows=false;}else{this.grid.can_add_rows=true;}}else{this.grid.can_add_rows=false;this.grid.can_edit=false;}}
if(this.df['default'].toLowerCase()=='no add rows'){this.grid.can_add_rows=false;}}
if(st=='Write'){this.grid.show();}else if(st=='Read'){this.grid.show();}else{this.grid.hide();}
this.grid.refresh();}
_f.TableField.prototype.set=function(v){};_f.TableField.prototype.set_input=function(v){};_f.CodeField=function(){};_f.CodeField.prototype=new Field();_f.CodeField.prototype.make_input=function(){var me=this;this.label_span.innerHTML=this.df.label;if(this.df.fieldtype=='Text Editor'){this.input=$a(this.input_area,'text_area','',{fontSize:'12px'});this.myid=wn.dom.set_unique_id(this.input);$(me.input).tinymce({script_url:'js/lib/tiny_mce_33/tiny_mce.js',theme:"advanced",plugins:"style,inlinepopups,table,advimage",extended_valid_elements:"div[id|dir|class|align|style]",width:'100%',height:'360px',theme_advanced_buttons1:"bold,italic,underline,strikethrough,hr,|,justifyleft,justifycenter,justifyright,|,formatselect,fontselect,fontsizeselect,|,image",theme_advanced_buttons2:"bullist,numlist,|,outdent,indent,|,undo,redo,|,link,unlink,code,|,forecolor,backcolor,|,tablecontrols",theme_advanced_buttons3:"",theme_advanced_toolbar_location:"top",theme_advanced_toolbar_align:"left",content_css:"js/lib/tiny_mce_33/custom_content.css?q=1",oninit:function(){me.init_editor();}});this.input.set_input=function(v){if(me.editor){me.editor.setContent(v);}else{$(me.input).val(v);}}
this.input.onchange=function(){me.set(me.editor.getContent());me.run_trigger();}
this.get_value=function(){return me.editor.getContent();}}else{wn.require('js/lib/ace/ace.js');$(this.input_area).css('border','1px solid #aaa');this.pre=$a(this.input_area,'pre','',{position:'relative',height:'400px',width:'100%'});this.input={};this.myid=wn.dom.set_unique_id(this.pre);this.editor=ace.edit(this.myid);if(me.df.options=='Markdown'||me.df.options=='HTML'){wn.require('js/lib/ace/mode-html.js');var HTMLMode=require("ace/mode/html").Mode;me.editor.getSession().setMode(new HTMLMode());}
else if(me.df.options=='Javascript'){wn.require('js/lib/ace/mode-javascript.js');var JavascriptMode=require("ace/mode/javascript").Mode;me.editor.getSession().setMode(new JavascriptMode());}
else if(me.df.options=='Python'){wn.require('js/lib/ace/mode-python.js');var PythonMode=require("ace/mode/python").Mode;me.editor.getSession().setMode(new PythonMode());}
this.input.set_input=function(v){me.setting_value=true;me.editor.getSession().setValue(v);me.setting_value=false;}
this.get_value=function(){return me.editor.getSession().getValue();}
$(cur_frm.wrapper).bind('render_complete',function(){me.editor.resize();me.editor.getSession().on('change',function(){if(me.setting_value)return;var val=me.get_value();if(locals[cur_frm.doctype][cur_frm.docname][me.df.fieldname]!=val){me.set(me.get_value());me.run_trigger();}})});}}
_f.CodeField.prototype.init_editor=function(){var me=this;this.editor=tinymce.get(this.myid);this.editor.onKeyUp.add(function(ed,e){me.set(ed.getContent());});this.editor.onPaste.add(function(ed,e){me.set(ed.getContent());});this.editor.onSetContent.add(function(ed,e){me.set(ed.getContent());});var c=locals[cur_frm.doctype][cur_frm.docname][this.df.fieldname];if(cur_frm&&c){this.editor.setContent(c);}}
_f.CodeField.prototype.set_disp=function(val){$y(this.disp_area,{width:'90%'})
if(this.df.fieldtype=='Text Editor'){this.disp_area.innerHTML=val;}else{this.disp_area.innerHTML='<textarea class="code_text" readonly=1>'+val+'</textarea>';}}
/*
 *	lib/js/legacy/widgets/form/grid.js
 */
_f.cur_grid_cell=null;_f.Grid=function(parent){}
_f.Grid.prototype.init=function(parent,row_height){var me=this;this.col_idx_by_name={}
this.alt_row_bg='#F2F2FF';this.row_height=row_height;if(!row_height)this.row_height='26px';this.make_ui(parent);this.insert_column('','','Int','Sr','50px','',[1,0,0]);if(this.oninit)this.oninit();$(this.wrapper).bind('keydown',function(e){me.notify_keypress(e,e.which);})
$(cur_frm.wrapper).bind('render_complete',function(){me.set_ht();});}
_f.Grid.prototype.make_ui=function(parent){var ht=make_table($a(parent,'div'),1,2,'100%',['60%','40%']);this.main_title=$td(ht,0,0);this.main_title.className='columnHeading';$td(ht,0,1).style.textAlign='right';this.tbar_div=$a($td(ht,0,1),'div','grid_tbarlinks');this.tbar_tab=make_table(this.tbar_div,1,4,'100%',['25%','25%','25%','25%']);this.wrapper=$a(parent,'div','grid_wrapper');this.head_wrapper=$a(this.wrapper,'div','grid_head_wrapper');this.head_tab=$a(this.head_wrapper,'table','grid_head_table');this.head_row=this.head_tab.insertRow(0);this.tab_wrapper=$a(this.wrapper,'div','grid_tab_wrapper');this.tab=$a(this.tab_wrapper,'table','grid_table');var me=this;this.wrapper.onscroll=function(){me.head_wrapper.style.top=me.wrapper.scrollTop+'px';}}
_f.Grid.prototype.show=function(){if(this.can_edit&&this.field.df['default'].toLowerCase()!='no toolbar'){$ds(this.tbar_div);if(this.can_add_rows){$td(this.tbar_tab,0,0).style.display='table-cell';$td(this.tbar_tab,0,1).style.display='table-cell';}else{$td(this.tbar_tab,0,0).style.display='none';$td(this.tbar_tab,0,1).style.display='none';}}else{$dh(this.tbar_div);}
$ds(this.wrapper);}
_f.Grid.prototype.hide=function(){$dh(this.wrapper);$dh(this.tbar_div);}
_f.Grid.prototype.insert_column=function(doctype,fieldname,fieldtype,label,width,options,perm,reqd){var idx=this.head_row.cells.length;if(!width)width='100px';if((width+'').slice(-2)!='px'){width=width+'px';}
var col=this.head_row.insertCell(idx);col.doctype=doctype;col.fieldname=fieldname;col.fieldtype=fieldtype;col.innerHTML='<div data-grid-fieldname = "'+doctype+'-'+fieldname+'">'+label+'</div>';col.label=label;if(reqd)
col.childNodes[0].style.color="#D22";col.style.width=width;col.options=options;col.perm=perm;this.col_idx_by_name[fieldname]=idx;}
_f.Grid.prototype.reset_table_width=function(){var w=0;$.each(this.head_row.cells,function(i,cell){if((cell.style.display||'').toLowerCase()!='none')
w+=cint(cell.style.width);})
this.head_tab.style.width=w+'px';this.tab.style.width=w+'px';}
_f.Grid.prototype.set_column_disp=function(fieldname,show){var cidx=this.col_idx_by_name[fieldname];if(!cidx){msgprint('Trying to hide unknown column: '+fieldname);return;}
var disp=show?'table-cell':'none';this.head_row.cells[cidx].style.display=disp;for(var i=0,len=this.tab.rows.length;i<len;i++){var cell=this.tab.rows[i].cells[cidx];cell.style.display=disp;}
this.reset_table_width();}
_f.Grid.prototype.append_row=function(idx,docname){if(!idx)idx=this.tab.rows.length;var row=this.tab.insertRow(idx);row.docname=docname;if(idx%2)var odd=true;else var odd=false;var me=this;for(var i=0;i<this.head_row.cells.length;i++){var cell=row.insertCell(i);var hc=this.head_row.cells[i];cell.style.width=hc.style.width;cell.style.display=hc.style.display;cell.row=row;cell.grid=this;cell.className='grid_cell';cell.div=$a(cell,'div','grid_cell_div');if(this.row_height){cell.div.style.height=this.row_height;}
cell.div.cell=cell;cell.div.onclick=function(e){me.cell_select(this.cell);}
if(odd){$bg(cell,this.alt_row_bg);cell.is_odd=1;cell.div.style.border='2px solid '+this.alt_row_bg;}else $bg(cell,'#FFF');if(!hc.fieldname)cell.div.style.cursor='default';}
this.set_ht();return row;}
_f.Grid.prototype.refresh_cell=function(docname,fieldname){for(var r=0;r<this.tab.rows.length;r++){if(this.tab.rows[r].docname==docname){for(var c=0;c<this.head_row.cells.length;c++){var hc=this.head_row.cells[c];if(hc.fieldname==fieldname){this.set_cell_value(this.tab.rows[r].cells[c]);}}}}}
_f.cur_grid;_f.cur_grid_ridx;_f.Grid.prototype.set_cell_value=function(cell){if(cell.row.is_newrow)return;var hc=this.head_row.cells[cell.cellIndex];if(hc.fieldname&&locals[hc.doctype][cell.row.docname]){var v=locals[hc.doctype][cell.row.docname][hc.fieldname];}else{var v=(cell.row.rowIndex+1);}
if(v==null){v='';}
var me=this;if(cell.cellIndex){var ft=hc.fieldtype;if(ft=='Link'&&cur_frm.doc.docstatus<1)ft='Data';$s(cell.div,v,ft,hc.options);}else{cell.div.style.padding='2px';cell.div.style.textAlign='left';cell.innerHTML='';var t=make_table(cell,1,3,'60px',['20px','20px','20px'],{verticalAlign:'middle',padding:'2px'});$y($td(t,0,0),{paddingLeft:'4px'});$td(t,0,0).innerHTML=cell.row.rowIndex+1;if(cur_frm.editable&&this.can_edit){var ed=$a($td(t,0,1),'i','icon-edit',{cursor:'pointer'});ed.cell=cell;ed.title='Edit Row';ed.onclick=function(){_f.cur_grid=me;_f.cur_grid_ridx=this.cell.row.rowIndex;_f.edit_record(me.doctype,this.cell.row.docname,1);}}else{cell.div.innerHTML=(cell.row.rowIndex+1);cell.div.style.cursor='default';cell.div.onclick=function(){}}}}
$(document).bind('click',function(e){var me=this;var is_target_toolbar=function(){return $(e.target).parents('.grid_tbarlinks').length;}
var is_target_input=function(){if(e.target.tagName.toLowerCase()=='option')return true;return $(e.target).parents().get().indexOf(_f.cur_grid_cell)!=-1;}
if(_f.cur_grid_cell&&!is_target_input()&&!is_target_toolbar()){if(!(text_dialog&&text_dialog.display)&&!datepicker_active&&!(selector&&selector.display)){setTimeout('_f.cur_grid_cell.grid.cell_deselect()',500);return false;}}});_f.Grid.prototype.cell_deselect=function(){if(_f.cur_grid_cell){var c=_f.cur_grid_cell;c.grid.remove_template(c);c.div.className='grid_cell_div';if(c.is_odd)c.div.style.border='2px solid '+c.grid.alt_row_bg;else c.div.style.border='2px solid #FFF';_f.cur_grid_cell=null;}}
_f.Grid.prototype.cell_select=function(cell,ri,ci){if(_f.cur_grid_cell==cell&&cell.hc)return;if(ri!=null&&ci!=null)
cell=this.tab.rows[ri].cells[ci];var hc=this.head_row.cells[cell.cellIndex];if(!hc.template){this.make_template(hc);}
hc.template.perm=this.field?this.field.perm:hc.perm;if(hc.fieldname&&hc.template.get_status()=='Write'){this.cell_deselect();cell.div.style.border='2px solid #88F';_f.cur_grid_cell=cell;this.add_template(cell);}}
_f.Grid.prototype.add_template=function(cell){if(!cell.row.docname&&this.add_newrow){this.add_newrow();this.cell_select(cell);}else{var hc=this.head_row.cells[cell.cellIndex];cell.div.innerHTML='';cell.div.appendChild(hc.template.wrapper);hc.template.activate(cell.row.docname);hc.template.activated=1;cell.hc=hc;if(hc.template.input&&hc.template.input.set_width){hc.template.input.set_width($(cell).width());}}}
_f.Grid.prototype.get_field=function(fieldname){for(var i=0;i<this.head_row.cells.length;i++){var hc=this.head_row.cells[i];if(hc.fieldname==fieldname){if(!hc.template){this.make_template(hc);}
return hc.template;}}
return{}}
_f.grid_date_cell='';_f.grid_refresh_date=function(){_f.grid_date_cell.grid.set_cell_value(_f.grid_date_cell);}
_f.grid_refresh_field=function(temp,input){if($(input).val()!=_f.get_value(temp.doctype,temp.docname,temp.df.fieldname))
$(input).trigger('change');}
_f.Grid.prototype.remove_template=function(cell){var hc=this.head_row.cells[cell.cellIndex];if(!hc.template)return;if(!hc.template.activated)return;if(hc.template&&hc.template.wrapper.parentNode)
cell.div.removeChild(hc.template.wrapper);this.set_cell_value(cell);hc.template.activated=0;}
_f.Grid.prototype.notify_keypress=function(e,keycode){if(keycode>=37&&keycode<=40&&e.shiftKey){if(text_dialog&&text_dialog.display){return;}}else
return;if(!_f.cur_grid_cell)return;if(_f.cur_grid_cell.grid!=this)return;var ri=_f.cur_grid_cell.row.rowIndex;var ci=_f.cur_grid_cell.cellIndex;switch(keycode){case 38:if(ri>0){this.cell_select('',ri-1,ci);}break;case 40:if(ri<(this.tab.rows.length-1)){this.cell_select('',ri+1,ci);}break;case 39:if(ci<(this.head_row.cells.length-1)){this.cell_select('',ri,ci+1);}break;case 37:if(ci>1){this.cell_select('',ri,ci-1);}break;}}
_f.Grid.prototype.make_template=function(hc){hc.template=make_field(get_field(hc.doctype,hc.fieldname),hc.doctype,'',this.field.frm,true);hc.template.grid=this;}
_f.Grid.prototype.append_rows=function(n){for(var i=0;i<n;i++)this.append_row();}
_f.Grid.prototype.truncate_rows=function(n){for(var i=0;i<n;i++)this.tab.deleteRow(this.tab.rows.length-1);}
_f.Grid.prototype.set_data=function(data){this.cell_deselect();this.reset_table_width();if(data.length>this.tab.rows.length)
this.append_rows(data.length-this.tab.rows.length);if(data.length<this.tab.rows.length)
this.truncate_rows(this.tab.rows.length-data.length);for(var ridx=0;ridx<data.length;ridx++){this.refresh_row(ridx,data[ridx]);}
if(this.can_add_rows&&this.make_newrow){this.make_newrow();}
if(this.wrapper.onscroll)this.wrapper.onscroll();}
_f.Grid.prototype.set_ht=function(){var max_ht=cint(0.37*screen.width);var ht=$(this.tab).height()+$(this.head_tab).height()+30;if(ht<100)
ht=100;if(ht>max_ht)ht=max_ht;ht+=4;$y(this.wrapper,{height:ht+'px'});}
_f.Grid.prototype.refresh_row=function(ridx,docname){var row=this.tab.rows[ridx];row.docname=docname;row.is_newrow=false;for(var cidx=0;cidx<row.cells.length;cidx++){this.set_cell_value(row.cells[cidx]);}}
/*
 *	lib/js/legacy/widgets/form/form_grid.js
 */
_f.FormGrid=function(field){this.field=field;this.doctype=field.df.options;if(!this.doctype){show_alert('No Options for table '+field.df.label);}
this.col_break_width=cint(this.field.col_break_width);if(!this.col_break_width)this.col_break_width=100;$y(field.parent,{marginTop:'8px'});this.init(field.parent,field.df.width);this.setup();}
_f.FormGrid.prototype=new _f.Grid();_f.FormGrid.prototype.setup=function(){this.make_columns();}
_f.FormGrid.prototype.make_tbar_link=function(parent,label,fn,icon){var div=$a(parent,'div','',{cursor:'pointer'});var t=make_table(div,1,2,'90%',['20px',null]);var img=$a($td(t,0,0),'i',icon);$y($td(t,0,0),{textAlign:'right'});var l=$a($td(t,0,1),'span','link_type',{color:'#333'});l.style.fontSize='11px';l.innerHTML=label;div.onclick=fn;div.show=function(){$ds(this);}
div.hide=function(){$dh(this);}
$td(t,0,0).isactive=1;$td(t,0,1).isactive=1;l.isactive=1;div.isactive=1;img.isactive=1;return div;}
_f.FormGrid.prototype.make_buttons=function(){var me=this;this.tbar_btns={};this.tbar_btns['Del']=this.make_tbar_link($td(this.tbar_tab,0,0),'Del',function(){me.delete_row();},'icon-remove-sign');this.tbar_btns['Ins']=this.make_tbar_link($td(this.tbar_tab,0,1),'Ins',function(){me.insert_row();},'icon-plus');this.tbar_btns['Up']=this.make_tbar_link($td(this.tbar_tab,0,2),'Up',function(){me.move_row(true);},'icon-arrow-up');this.tbar_btns['Dn']=this.make_tbar_link($td(this.tbar_tab,0,3),'Dn',function(){me.move_row(false);},'icon-arrow-down');for(var i in this.btns)
this.btns[i].isactive=true;}
_f.FormGrid.prototype.make_columns=function(){var gl=wn.meta.docfield_list[this.field.df.options];if(!gl){alert('Table details not found "'+this.field.df.options+'"');}
gl.sort(function(a,b){return a.idx-b.idx});var p=this.field.perm;for(var i=0;i<gl.length;i++){if(p[this.field.df.permlevel]&&p[this.field.df.permlevel][READ]){this.insert_column(this.field.df.options,gl[i].fieldname,gl[i].fieldtype,gl[i].label,gl[i].width,gl[i].options,this.field.perm,gl[i].reqd);if(gl[i].hidden){this.set_column_disp(gl[i].fieldname,false);}}}}
_f.FormGrid.prototype.set_column_label=function(fieldname,label){for(var i=0;i<this.head_row.cells.length;i++){var c=this.head_row.cells[i];if(c.fieldname==fieldname){c.innerHTML='<div class="grid_head_div">'+label+'</div>';c.cur_label=label;break;}}}
_f.FormGrid.prototype.get_children=function(){return getchildren(this.doctype,this.field.frm.docname,this.field.df.fieldname,this.field.frm.doctype);}
_f.FormGrid.prototype.refresh=function(){var docset=this.get_children();var data=[];for(var i=0;i<docset.length;i++){locals[this.doctype][docset[i].name].idx=i+1;data[data.length]=docset[i].name;}
this.set_data(data);if(_f.frm_dialog&&_f.frm_dialog.dialog.display&&_f.frm_dialog.cur_frm){_f.frm_dialog.cur_frm.refresh();}}
_f.FormGrid.prototype.set_unsaved=function(){locals[cur_frm.doctype][cur_frm.docname].__unsaved=1;cur_frm.frm_head&&cur_frm.frm_head.refresh_labels();}
_f.FormGrid.prototype.insert_row=function(){var d=this.new_row_doc();var ci=_f.cur_grid_cell.cellIndex;var row_idx=_f.cur_grid_cell.row.rowIndex;d.idx=row_idx+1;for(var ri=row_idx;ri<this.tab.rows.length;ri++){var r=this.tab.rows[ri];if(r.docname)
locals[this.doctype][r.docname].idx++;}
this.refresh();this.cell_select('',row_idx,ci);this.set_unsaved();}
_f.FormGrid.prototype.new_row_doc=function(){var n=LocalDB.create(this.doctype);var d=locals[this.doctype][n];d.parent=this.field.frm.docname;d.parentfield=this.field.df.fieldname;d.parenttype=this.field.frm.doctype;return d;}
_f.FormGrid.prototype.add_newrow=function(){var r=this.tab.rows[this.tab.rows.length-1];if(!r.is_newrow)
show_alert('fn: add_newrow: Adding a row which is not flagged as new');var d=this.new_row_doc();d.idx=r.rowIndex+1;r.docname=d.name;r.is_newrow=false;this.set_cell_value(r.cells[0]);this.make_newrow();this.refresh_row(r.rowIndex,d.name);if(this.onrowadd)this.onrowadd(cur_frm.doc,d.doctype,d.name);return d.name;}
_f.FormGrid.prototype.make_newrow=function(from_add_btn){if(!this.can_add_rows)
return;if(this.tab.rows.length){var r=this.tab.rows[this.tab.rows.length-1];if(r.is_newrow)
return;}
var r=this.append_row();r.cells[0].div.innerHTML='<b style="font-size: 18px;">*</b>';r.is_newrow=true;}
_f.FormGrid.prototype.check_selected=function(){if(!_f.cur_grid_cell){show_alert('Select a cell first');return false;}
if(_f.cur_grid_cell.grid!=this){show_alert('Select a cell first');return false;}
return true;}
_f.FormGrid.prototype.delete_row=function(dt,dn){if(dt&&dn){LocalDB.delete_record(dt,dn);this.refresh();}else{if(!this.check_selected())return;var r=_f.cur_grid_cell.row;if(r.is_newrow)return;var ci=_f.cur_grid_cell.cellIndex;var ri=_f.cur_grid_cell.row.rowIndex;LocalDB.delete_record(this.doctype,r.docname);this.refresh();if(ri<(this.tab.rows.length-2))
this.cell_select(null,ri,ci);else _f.cur_grid_cell=null;}
this.set_unsaved();}
_f.FormGrid.prototype.move_row=function(up){if(!this.check_selected())return;var r=_f.cur_grid_cell.row;if(r.is_newrow)return;if(up&&r.rowIndex>0){var swap_row=this.tab.rows[r.rowIndex-1];}else if(!up){var len=this.tab.rows.length;if(this.tab.rows[len-1].is_newrow)
len=len-1;if(r.rowIndex<(len-1))
var swap_row=this.tab.rows[r.rowIndex+1];}
if(swap_row){var cidx=_f.cur_grid_cell.cellIndex;this.cell_deselect();var aidx=locals[this.doctype][r.docname].idx;locals[this.doctype][r.docname].idx=locals[this.doctype][swap_row.docname].idx;locals[this.doctype][swap_row.docname].idx=aidx;var adocname=swap_row.docname;this.refresh_row(swap_row.rowIndex,r.docname);this.refresh_row(r.rowIndex,adocname);this.cell_select(this.tab.rows[swap_row.rowIndex].cells[cidx]);this.set_unsaved();}}
/*
 *	lib/js/legacy/widgets/form/print_format.js
 */
_p.def_print_style_body="html, body, div, span, td { font-family: Arial, Helvetica; font-size: 12px; }"+"\npre { margin:0; padding:0;}"
_p.def_print_style_other="\n.simpletable, .noborder { border-collapse: collapse; margin-bottom: 10px;}"
+"\n.simpletable td {border: 1pt solid #000; vertical-align: top; padding: 2px; }"
+"\n.noborder td { vertical-align: top; }"
_p.go=function(html){var d=document.createElement('div')
d.innerHTML=html
$(d).printElement();}
_p.preview=function(html){var w=window.open('');if(!w)return;w.document.write(html)
w.document.close();}
$.extend(_p,{show_dialog:function(){if(!_p.dialog){_p.make_dialog();}
_p.dialog.show();},make_dialog:function(){var d=new Dialog(360,140,'Print Formats',[['HTML','Select'],['Check','No Letterhead'],['HTML','Buttons']]);$btn(d.widgets.Buttons,'Print',function(){_p.build(sel_val(cur_frm.print_sel),_p.go,d.widgets['No Letterhead'].checked);},{cssFloat:'right',marginBottom:'16px',marginLeft:'7px'},'green');$btn(d.widgets.Buttons,'Preview',function(){_p.build(sel_val(cur_frm.print_sel),_p.preview,d.widgets['No Letterhead'].checked);},{cssFloat:'right',marginBottom:'16px'},'');d.onshow=function(){var c=_p.dialog.widgets['Select'];if(c.cur_sel&&c.cur_sel.parentNode==c){c.removeChild(c.cur_sel);}
c.appendChild(cur_frm.print_sel);c.cur_sel=cur_frm.print_sel;}
_p.dialog=d;},formats:{},build:function(fmtname,onload,no_letterhead,only_body){args={fmtname:fmtname,onload:onload,no_letterhead:no_letterhead,only_body:only_body};if(!cur_frm){alert('No Document Selected');return;}
var doc=locals[cur_frm.doctype][cur_frm.docname];if(args.fmtname=='Standard'){args.onload(_p.render({body:_p.print_std(args.no_letterhead),style:_p.print_style,doc:doc,title:doc.name,no_letterhead:args.no_letterhead,only_body:args.only_body}));}else{if(!_p.formats[args.fmtname]){var build_args=args;$c(command='webnotes.widgets.form.print_format.get',args={'name':build_args.fmtname},fn=function(r,rt){_p.formats[build_args.fmtname]=r.message;build_args.onload(_p.render({body:_p.formats[build_args.fmtname],style:'',doc:doc,title:doc.name,no_letterhead:build_args.no_letterhead,only_body:build_args.only_body}));});}else{args.onload(_p.render({body:_p.formats[args.fmtname],style:'',doc:doc,title:doc.name,no_letterhead:args.no_letterhead,only_body:args.only_body}));}}},render:function(args){var container=document.createElement('div');var stat='';stat+=_p.show_draft(args);stat+=_p.show_archived(args);stat+=_p.show_cancelled(args);container.innerHTML=args.body;_p.show_letterhead(container,args);_p.run_embedded_js(container,args.doc);var style=_p.consolidate_css(container,args);_p.render_header_on_break(container,args);return _p.render_final(style,stat,container,args);},head_banner_format:function(){return"\
   <div style = '\
     text-align: center; \
     padding: 8px; \
     background-color: #CCC;'> \
    <div style = '\
      font-size: 20px; \
      font-weight: bold;'>\
     {{HEAD}}\
    </div>\
    {{DESCRIPTION}}\
   </div>"},show_draft:function(args){var is_doctype_submittable=0;var plist=locals['DocPerm'];for(var perm in plist){var p=plist[perm];if((p.parent==args.doc.doctype)&&(p.submit==1)){is_doctype_submittable=1;break;}}
if(args.doc&&cint(args.doc.docstatus)==0&&is_doctype_submittable){draft=_p.head_banner_format();draft=draft.replace("{{HEAD}}","DRAFT");draft=draft.replace("{{DESCRIPTION}}","This box will go away after the document is submitted.");return draft;}else{return"";}},show_archived:function(args){if(args.doc&&args.doc.__archived){archived=_p.head_banner_format();archived=archived.replace("{{HEAD}}","ARCHIVED");archived=archived.replace("{{DESCRIPTION}}","You must restore this document to make it editable.");return archived;}else{return"";}},show_cancelled:function(args){if(args.doc&&args.doc.docstatus==2){cancelled=_p.head_banner_format();cancelled=cancelled.replace("{{HEAD}}","CANCELLED");cancelled=cancelled.replace("{{DESCRIPTION}}","You must amend this document to make it editable.");return cancelled;}else{return"";}},consolidate_css:function(container,args){var body_style='';var style_list=container.getElementsByTagName('style');while(style_list&&style_list.length>0){for(i in style_list){if(style_list[i]&&style_list[i].innerHTML){body_style+=style_list[i].innerHTML;var parent=style_list[i].parentNode;if(parent){parent.removeChild(style_list[i]);}else{container.removeChild(style_list[i]);}}}
style_list=container.getElementsByTagName('style');}
style_concat=(args.only_body?'':_p.def_print_style_body)
+_p.def_print_style_other+args.style+body_style;return style_concat;},run_embedded_js:function(container,doc){var jslist=container.getElementsByTagName('script');while(jslist&&jslist.length>0){for(i in jslist){if(jslist[i]&&jslist[i].innerHTML){var code=jslist[i].innerHTML;var parent=jslist[i].parentNode;var span=$a(parent,'span');parent.replaceChild(span,jslist[i]);var val=code?eval(code):'';if(!val||typeof(val)=='object'){val='';}
span.innerHTML=val;}}
jslist=container.getElementsByTagName('script');}},show_letterhead:function(container,args){if(!(args.no_letterhead||args.only_body)){container.innerHTML='<div>'+_p.get_letter_head()+'</div>'
+container.innerHTML;}},render_header_on_break:function(container,args){var page_set=container.getElementsByClassName('page-settings');if(page_set.length){for(var i=0;i<page_set.length;i++){var tmp='';tmp+=_p.show_draft(args);tmp+=_p.show_archived(args);_p.show_letterhead(page_set[i],args);page_set[i].innerHTML=tmp+page_set[i].innerHTML;}}},render_final:function(style,stat,container,args){var header='<div class="page-settings">\n';var footer='\n</div>';if(!args.only_body){header='<!DOCTYPE html>\n\
     <html>\
      <head>\
       <title>'+args.title+'</title>\
       <style>'+style+'</style>\
      </head>\
      <body>\n'+header;footer=footer+'\n</body>\n\
     </html>';}
var finished=header
+stat
+container.innerHTML.replace(/<div/g,'\n<div').replace(/<td/g,'\n<td')
+footer;return finished;},get_letter_head:function(){var cp=wn.control_panel;var lh='';if(cur_frm.doc.letter_head){lh=cstr(wn.boot.letter_heads[cur_frm.doc.letter_head]);}else if(cp.letter_head){lh=cp.letter_head;}
return lh;},print_style:"\
  .datalabelcell { \
   padding: 2px 0px; \
   width: 38%; \
   vertical-align: top; \
   } \
  .datainputcell { \
   padding: 2px 0px; \
   width: 62%; \
   text-align: left; \
   }\
  .sectionHeading { \
   font-size: 16px; \
   font-weight: bold; \
   margin: 8px 0px; \
   } \
  .columnHeading { \
   font-size: 14px; \
   font-weight: bold; \
   margin: 8px 0px; \
   }",print_std:function(no_letterhead){var docname=cur_frm.docname;var doctype=cur_frm.doctype;var data=getchildren('DocField',doctype,'fields','DocType');var layout=_p.add_layout(doctype);this.pf_list=[layout];var me=this;me.layout=layout;$.extend(this,{build_head:function(data,doctype,docname){var h1_style={fontSize:'22px',marginBottom:'8px'}
var h1=$a(me.layout.cur_row.header,'h1','',h1_style);if(cur_frm.pformat[docname]){h1.innerHTML=cur_frm.pformat[docname];}else{var val=null;for(var i=0;i<data.length;i++){if(data[i].fieldname==='select_print_heading'){val=_f.get_value(doctype,docname,data[i].fieldname);break;}}
h1.innerHTML=val?val:get_doctype_label(doctype);}
var h2_style={fontSize:'16px',color:'#888',marginBottom:'8px',paddingBottom:'8px',borderBottom:(me.layout.with_border?'0px':'1px solid #000')}
var h2=$a(me.layout.cur_row.header,'div','',h2_style);h2.innerHTML=docname;},build_data:function(data,doctype,docname){if(data[0]&&data[0].fieldtype!="Section Break"){me.layout.addrow();if(data[0].fieldtype!="Column Break"){me.layout.addcell();}}
$.extend(this,{generate_custom_html:function(field,doctype,docname){var container=$a(me.layout.cur_cell,'div');container.innerHTML=cur_frm.pformat[field.fieldname](locals[doctype][docname]);},render_normal:function(field,data,i){switch(field.fieldtype){case'Section Break':me.layout.addrow();if(data[i+1]&&data[i+1].fieldtype!='Column Break'){me.layout.addcell();}
break;case'Column Break':me.layout.addcell(field.width,field.label);break;case'Table':var table=print_table(doctype,docname,field.fieldname,field.options,null,null,null,null);me.layout=_p.print_std_add_table(table,me.layout,me.pf_list,doctype,no_letterhead);break;case'HTML':var div=$a(me.layout.cur_cell,'div');div.innerHTML=field.options;break;case'Code':var div=$a(me.layout.cur_cell,'div');var val=_f.get_value(doctype,docname,field.fieldname);div.innerHTML='<div>'+field.label+': </div><pre style="font-family: Courier, Fixed;">'+(val?val:'')+'</pre>';break;case'Text Editor':var div=$a(me.layout.cur_cell,'div');var val=_f.get_value(doctype,docname,field.fieldname);div.innerHTML=val?val:'';break;default:_p.print_std_add_field(doctype,docname,field,me.layout);break;}}});for(var i=0;i<data.length;i++){var fieldname=data[i].fieldname?data[i].fieldname:data[i].label;var field=fieldname?get_field(doctype,fieldname,docname):data[i];if(!field.print_hide){if(cur_frm.pformat[field.fieldname]){this.generate_custom_html(field,doctype,docname);}else{this.render_normal(field,data,i);}}}
me.layout.close_borders();},build_html:function(){var html='';for(var i=0;i<me.pf_list.length;i++){if(me.pf_list[i].wrapper){html+=me.pf_list[i].wrapper.innerHTML;}else if(me.pf_list[i].innerHTML){html+=me.pf_list[i].innerHTML;}else{html+=me.pf_list[i];}}
this.pf_list=[];return html;}});this.build_head(data,doctype,docname);this.build_data(data,doctype,docname);var html=this.build_html();return html;},add_layout:function(doctype){var layout=new Layout();layout.addrow();if(locals['DocType'][doctype].print_outline=='Yes'){layout.with_border=1}
return layout;},print_std_add_table:function(t,layout,pf_list,dt,no_letterhead){if(t.appendChild){layout.cur_cell.appendChild(t);}else{page_break='\n\
    <div style = "page-break-after: always;" \
    class = "page_break"></div><div class="page-settings"></div>';for(var i=0;i<t.length-1;i++){layout.cur_cell.appendChild(t[i]);layout.close_borders();pf_list.push(page_break);layout=_p.add_layout(dt,no_letterhead);pf_list.push(layout);layout.addrow();layout.addcell();var div=$a(layout.cur_cell,'div');div.innerHTML='Continued from previous page...';div.style.padding='4px';}
layout.cur_cell.appendChild(t[t.length-1]);}
return layout;},print_std_add_field:function(dt,dn,f,layout){var val=_f.get_value(dt,dn,f.fieldname);if(f.fieldtype!='Button'){if(val||in_list(['Float','Int','Currency'],f.fieldtype)){row=_p.field_tab(layout.cur_cell);row.cells[0].innerHTML=f.label?f.label:f.fieldname;$s(row.cells[1],val,f.fieldtype);if(f.fieldtype=='Currency'){$y(row.cells[1],{textAlign:'left'});}}}},field_tab:function(layout_cell){var tab=$a(layout_cell,'table','',{width:'100%'});var row=tab.insertRow(0);_p.row=row;row.insertCell(0);row.insertCell(1);row.cells[0].className='datalabelcell';row.cells[1].className='datainputcell';return row;}});print_table=function(dt,dn,fieldname,tabletype,cols,head_labels,widths,condition,cssClass,modifier,hide_empty){var me=this;$.extend(this,{flist:(function(){var f_list=[];var fl=wn.meta.docfield_list[tabletype];if(fl){for(var i=0;i<fl.length;i++){f_list.push(copy_dict(fl[i]));}}
return f_list;})(),data:function(){var children=getchildren(tabletype,dn,fieldname,dt);var data=[]
for(var i=0;i<children.length;i++){data.push(copy_dict(children[i]));}
return data;}(),cell_style:{border:'1px solid #000',padding:'2px',verticalAlign:'top'},head_cell_style:{border:'1px solid #000',padding:'2px',verticalAlign:'top',backgroundColor:'#ddd',fontWeight:'bold'},table_style:{width:'100%',borderCollapse:'collapse',marginBottom:'10px'},remove_empty_cols:function(flist){var non_empty_cols=[]
for(var i=0;i<me.data.length;i++){for(var c=0;c<flist.length;c++){if(flist[c].print_hide||!inList(['',null],me.data[i][flist[c].fieldname])){if(!inList(non_empty_cols,flist[c])){non_empty_cols.push(flist[c]);}}}}
for(var c=0;c<flist.length;c++){if(!inList(non_empty_cols,flist[c])){flist.splice(c,1);c=c-1;}}},prepare_col_heads:function(flist){var new_flist=[];if(!cols||(cols&&cols.length&&hide_empty)){me.remove_empty_cols(flist);}
if(cols&&cols.length){if(cols[0]=='SR'){new_flist.push('SR')}
for(var i=0;i<cols.length;i++){for(var j=0;j<flist.length;j++){if(flist[j].fieldname==cols[i]){new_flist.push(flist[j]);break;}}}}else{new_flist.push('SR');for(var i=0;i<flist.length;i++){if(!flist[i].print_hide){new_flist.push(flist[i]);}}}
me.flist=new_flist;},make_print_table:function(flist){var wrapper=document.createElement('div');var table=$a(wrapper,'table','',me.table_style);table.wrapper=wrapper;table.insertRow(0);var col_start=0;if(flist[0]=='SR'){var cell=table.rows[0].insertCell(0);cell.innerHTML=head_labels?head_labels[0]:'<b>SR</b>';$y(cell,{width:'30px'});$y(cell,me.head_cell_style);col_start++;}
for(var c=col_start;c<flist.length;c++){var cell=table.rows[0].insertCell(c);$y(cell,me.head_cell_style);cell.innerHTML=head_labels?head_labels[c]:flist[c].label;if(flist[c].width){$y(cell,{width:flist[c].width});}
if(widths){$y(cell,{width:widths[c]});}
if(in_list(['Currency','Float'],flist[c].fieldtype)){$y(cell,{textAlign:'right'});}}
return table;},populate_table:function(table,data){for(var r=0;r<data.length;r++){if((!condition)||(condition(data[r]))){if(data[r].page_break){table=me.make_print_table(me.flist);me.table_list.push(table.wrapper);}
var row=table.insertRow(table.rows.length);if(me.flist[0]=='SR'){var cell=row.insertCell(0);cell.innerHTML=r+1;$y(cell,me.cell_style);}
for(var c=me.flist.indexOf('SR')+1;c<me.flist.length;c++){var cell=row.insertCell(c);$y(cell,me.cell_style);if(modifier&&me.flist[c].fieldname in modifier){data[r][me.flist[c].fieldname]=modifier[me.flist[c].fieldname](data[r]);}
$s(cell,data[r][me.flist[c].fieldname],me.flist[c].fieldtype);if(in_list(['Currency','Float'],me.flist[c].fieldtype)){cell.style.textAlign='right';}}}}}});if(!this.data.length){return document.createElement('div');}
this.prepare_col_heads(this.flist);var table=me.make_print_table(this.flist);this.table_list=[table.wrapper];this.populate_table(table,this.data);return(me.table_list.length>1)?me.table_list:me.table_list[0];}
/*
 *	lib/js/legacy/widgets/form/email.js
 */
_e.email_as_field='email_id';_e.email_as_dt='Contact';_e.email_as_in='email_id,contact_name';sendmail=function(emailto,emailfrom,cc,subject,message,fmt,with_attachments){var fn=function(html){$c('webnotes.utils.email_lib.send_form',{'sendto':emailto,'sendfrom':emailfrom?emailfrom:'','cc':cc?cc:'','subject':subject,'message':replace_newlines(message),'body':html,'full_domain':wn.urllib.get_base_url(),'with_attachments':with_attachments?1:0,'dt':cur_frm.doctype,'dn':cur_frm.docname,'customer':cur_frm.doc.customer||'','supplier':cur_frm.doc.supplier||''},function(r,rtxt){});}
_p.build(fmt,fn);}
_e.make=function(){var d=new Dialog(440,440,"Send Email");var email_go=function(){var emailfrom=d.widgets['From'].value;var emailto=d.widgets['To'].value;if(!emailfrom)
emailfrom=user_email;emailto=emailto.replace(/ /g,"");var email_list=emailto.split(/[,|;]/);var valid=1;for(var i=0;i<email_list.length;i++){if(!email_list[i]){email_list.splice(i,1);}else if(!validate_email(email_list[i])){msgprint('error:'+email_list[i]+' is not a valid email id');valid=0;}}
emailto=email_list.join(",");if(emailfrom&&!validate_email(emailfrom)){msgprint('error:'+emailfrom+' is not a valid email id. To change the default please click on Profile on the top right of the screen and change it.');return;}
if(!valid)return;var cc=emailfrom;if(!emailfrom){emailfrom=wn.control_panel.auto_email_id;cc='';}
sendmail(emailto,emailfrom,emailfrom,d.widgets['Subject'].value,d.widgets['Message'].value,sel_val(cur_frm.print_sel),d.widgets['Send With Attachments'].checked);_e.dialog.hide();}
d.onhide=function(){}
d.make_body([['Data','To','Example: abc@hotmail.com, xyz@yahoo.com'],['Select','Format'],['Data','Subject'],['Data','From','Optional'],['Check','Send With Attachments','Will send all attached documents (if any)'],['Text','Message'],['Button','Send',email_go]]);d.widgets['From'].value=(user_email?user_email:'');$td(d.rows['Format'].tab,0,1).cur_sel=d.widgets['Format'];function split(val){return val.split(/,\s*/);}
function extractLast(term){return split(term).pop();}
$(d.widgets['To']).bind("keydown",function(event){if(event.keyCode===$.ui.keyCode.TAB&&$(this).data("autocomplete").menu.active){event.preventDefault();}}).autocomplete({source:function(request,response){wn.call({method:'webnotes.utils.email_lib.get_contact_list',args:{'select':_e.email_as_field,'from':_e.email_as_dt,'where':_e.email_as_in,'txt':extractLast(request.term).value||'%'},callback:function(r){response($.ui.autocomplete.filter(r.cl||[],extractLast(request.term)));}});},focus:function(){return false;},select:function(event,ui){var terms=split(this.value);terms.pop();terms.push(ui.item.value);terms.push("");this.value=terms.join(", ");return false;}});_e.dialog=d;}
/*
 *	lib/js/legacy/widgets/form/clientscriptAPI.js
 */
$c_get_values=function(args,doc,dt,dn,user_callback){var call_back=function(r,rt){if(!r.message)return;if(user_callback)user_callback(r.message);var fl=args.fields.split(',');for(var i in fl){locals[dt][dn][fl[i]]=r.message[fl[i]];if(args.table_field)
refresh_field(fl[i],dn,args.table_field);else
refresh_field(fl[i]);}}
$c('webnotes.widgets.form.utils.get_fields',args,call_back);}
get_server_fields=function(method,arg,table_field,doc,dt,dn,allow_edit,call_back){if(!allow_edit)freeze('Fetching Data...');$c('runserverobj',args={'method':method,'docs':compress_doclist(make_doclist(doc.doctype,doc.name)),'arg':arg},function(r,rt){if(r.message){var d=locals[dt][dn];var field_dict=r.message;for(var key in field_dict){d[key]=field_dict[key];if(table_field)refresh_field(key,d.name,table_field);else refresh_field(key);}}
if(call_back){doc=locals[doc.doctype][doc.name];call_back(doc,dt,dn);}
if(!allow_edit)unfreeze();});}
set_multiple=function(dt,dn,dict,table_field){var d=locals[dt][dn];for(var key in dict){d[key]=dict[key];if(table_field)refresh_field(key,d.name,table_field);else refresh_field(key);}}
refresh_many=function(flist,dn,table_field){for(var i in flist){if(table_field)refresh_field(flist[i],dn,table_field);else refresh_field(flist[i]);}}
set_field_tip=function(n,txt){var df=get_field(cur_frm.doctype,n,cur_frm.docname);if(df)df.description=txt;if(cur_frm&&cur_frm.fields_dict){if(cur_frm.fields_dict[n])
cur_frm.fields_dict[n].comment_area.innerHTML=replace_newlines(txt);else
errprint('[set_field_tip] Unable to set field tip: '+n);}}
refresh_field=function(n,docname,table_field){if(typeof n==typeof[])refresh_many(n,docname,table_field);if(table_field){if(_f.frm_dialog&&_f.frm_dialog.display){if(_f.frm_dialog.cur_frm.fields_dict[n]&&_f.frm_dialog.cur_frm.fields_dict[n].refresh)
_f.frm_dialog.cur_frm.fields_dict[n].refresh();}else{var g=_f.cur_grid_cell;if(g)var hc=g.grid.head_row.cells[g.cellIndex];if(g&&hc&&hc.fieldname==n&&g.row.docname==docname){hc.template.refresh();}else{cur_frm.fields_dict[table_field].grid.refresh_cell(docname,n);}}}else if(cur_frm&&cur_frm.fields_dict){if(cur_frm.fields_dict[n]&&cur_frm.fields_dict[n].refresh)
cur_frm.fields_dict[n].refresh();}}
set_field_options=function(n,txt){var df=get_field(cur_frm.doctype,n,cur_frm.docname);if(df)df.options=txt;refresh_field(n);}
set_field_permlevel=function(n,level){var df=get_field(cur_frm.doctype,n,cur_frm.docname);if(df)df.permlevel=level;refresh_field(n);}
toggle_field=function(n,hidden){var df_obj=get_field_obj(n);var df=get_field(cur_frm.doctype,n,cur_frm.docname);if(df){if(df_obj.df.fieldtype==="Section Break"){$(df_obj.row.wrapper).toggle(hidden?false:true);}else if(df_obj.df.fieldtype==="Column Break"){$(df_obj.cell.wrapper).toggle(hidden?false:true);}else{df.hidden=hidden;refresh_field(n);}}
else{console.log((hidden?"hide_field":"unhide_field")+" cannot find field "+n);}}
hide_field=function(n){if(cur_frm){if(n.substr)toggle_field(n,1);else{for(var i in n)toggle_field(n[i],1)}}}
unhide_field=function(n){if(cur_frm){if(n.substr)toggle_field(n,0);else{for(var i in n)toggle_field(n[i],0)}}}
get_field_obj=function(fn){return cur_frm.fields_dict[fn];}
set_missing_values=function(doc,dict){var fields_to_set={};$.each(dict,function(i,v){if(!doc[i]){fields_to_set[i]=v;}});if(fields_to_set){set_multiple(doc.doctype,doc.name,fields_to_set);}}
/*
 *	lib/js/legacy/widgets/form/form_comments.js
 */
wn.widgets.form.comments={n_comments:{},comment_list:{},sync:function(dt,dn,r){var f=wn.widgets.form.comments;f.n_comments[dn]=r.n_comments;f.comment_list[dn]=r.comment_list;},add:function(input,dt,dn,callback){$c('webnotes.widgets.form.comments.add_comment',wn.widgets.form.comments.get_args(input,dt,dn),function(r,rt){wn.widgets.form.comments.update_comment_list(input,dt,dn);input.value='';callback(input,dt,dn);});},remove:function(dt,dn,comment_id,callback){$c('webnotes.widgets.form.comments.remove_comment',{id:comment_id,dt:dt,dn:dn},callback);},get_args:function(input,dt,dn){return{comment:input.value,comment_by:user,comment_by_fullname:user_fullname,comment_doctype:dt,comment_docname:dn}},update_comment_list:function(input,dt,dn){var f=wn.widgets.form.comments;f.n_comments[dn]=cint(f.n_comments[dn])+1;f.comment_list[dn]=add_lists([f.get_args(input,dt,dn)],f.comment_list[dn]);}}
CommentList=function(parent,dt,dn){this.wrapper=$a(parent,'div','',{margin:'16px'});this.input_area=$a(this.wrapper,'div','',{margin:'2px'});this.lst_area=$a(this.wrapper,'div','',{margin:'2px'});this.make_input();this.make_lst();this.dt;this.dn;}
CommentList.prototype.run=function(){this.lst.run();}
CommentList.prototype.make_input=function(){var me=this;this.input=$a(this.input_area,'textarea','',{height:'60px',width:'300px',fontSize:'14px'});this.btn=$btn($a(this.input_area,'div'),'Post',function(){me.add_comment();},{marginTop:'8px'});}
CommentList.prototype.add_comment=function(){var me=this;var callback=function(input,dt,dn){me.lst.run();}
wn.widgets.form.comments.add(this.input,cur_frm.docname,cur_frm.doctype,callback)}
CommentList.prototype.make_lst=function(){if(!this.lst){wn.require('js/listing.js');var l=new Listing('Comments',1);var me=this;l.colwidths=['100%'];l.opts.hide_export=1;l.opts.hide_print=1;l.opts.hide_refresh=1;l.opts.no_border=1;l.opts.hide_rec_label=0;l.opts.show_calc=0;l.opts.round_corners=0;l.opts.alt_cell_style={};l.opts.cell_style={padding:'3px'};l.no_rec_message='No comments yet. Be the first one to comment!';l.get_query=function(){this.query=repl("select t1.name, t1.comment, t1.comment_by, '', \
   t1.creation, t1.comment_doctype, t1.comment_docname, \
   ifnull(concat_ws(' ',ifnull(t2.first_name,''),ifnull(t2.middle_name,''),\
   ifnull(t2.last_name,'')),''), '', \
   DAYOFMONTH(t1.creation), MONTHNAME(t1.creation), YEAR(t1.creation), \
   hour(t1.creation), minute(t1.creation), second(t1.creation) \
   from `tabComment` t1, `tabProfile` t2 \
   where t1.comment_doctype = '%(dt)s' and t1.comment_docname = '%(dn)s' \
   and t1.comment_by = t2.name order by t1.creation desc",{dt:me.dt,dn:me.dn});this.query_max=repl("select count(name) from `tabComment` where \
  comment_doctype='%(dt)s' and comment_docname='%(dn)s'",{'dt':me.dt,'dn':me.dn});}
l.show_cell=function(cell,ri,ci,d){new CommentItem(cell,ri,ci,d,me)}
this.lst=l;this.lst.make(this.lst_area);}}
CommentItem=function(cell,ri,ci,d,comment){this.comment=comment;$y(cell,{padding:'4px 0px'})
var t=make_table(cell,1,3,'100%',['15%','65%','20%'],{padding:'4px'});this.img=$a($td(t,0,0),'img','',{width:'40px'});this.cmt_by=$a($td(t,0,0),'div');this.set_picture(d,ri);this.cmt_dtl=$a($td(t,0,1),'div','comment',{fontSize:'11px'});this.cmt=$a($td(t,0,1),'div','',{fontSize:'14px'});this.show_cmt($td(t,0,1),ri,ci,d);this.cmt_delete($td(t,0,2),ri,ci,d);}
CommentItem.prototype.set_picture=function(d,ri){this.user.src=wn.user_info(d[ri][2]).image;this.cmt_by.innerHTML=d[ri][7]?d[ri][7]:d[ri][2];}
CommentItem.prototype.show_cmt=function(cell,ri,ci,d){if(d[ri][4]){hr=d[ri][12];min=d[ri][13];sec=d[ri][14];if(parseInt(hr)>12){time=(parseInt(hr)-12)+':'+min+' PM'}
else{time=hr+':'+min+' AM'}}
this.cmt_dtl.innerHTML='On '+d[ri][10].substring(0,3)+' '+d[ri][9]+', '+d[ri][11]+' at '+time;this.cmt.innerHTML=replace_newlines(d[ri][1]);}
CommentItem.prototype.cmt_delete=function(cell,ri,ci,d){var me=this;if(d[ri][2]==user||d[ri][3]==user){del=$a(cell,'i','icon-remove-sign',{cursor:'pointer'});del.cmt_id=d[ri][0];del.onclick=function(){wn.widgets.form.comments.remove(cur_frm.doctype,cur_frm.docname,this.cmt_id,function(){me.comment.lst.run();})}}}
/*
 *	lib/js/legacy/wn/widgets/form/sidebar.js
 */
wn.widgets.form.sidebar={Sidebar:function(form){var me=this;this.form=form;this.opts={sections:[{title:'Actions',items:[{type:'link',label:'New',icon:'icon-plus',display:function(){return in_list(profile.can_create,form.doctype)},onclick:function(){new_doc(me.form.doctype)}},{type:'link',label:'List',icon:'icon-list',display:function(){return!me.form.meta.issingle;},onclick:function(){window.location.href="#!List/"+me.form.doctype}},{type:'link',label:'Refresh',icon:'icon-refresh',onclick:function(){me.form.reload_doc()}},{type:'link',label:'Print',display:function(){return!(me.form.doc.__islocal||me.form.meta.allow_print);},icon:'icon-print',onclick:function(){me.form.print_doc()}},{type:'link',label:'Email',display:function(){return!(me.form.doc.__islocal||me.form.meta.allow_email);},icon:'icon-envelope',onclick:function(){me.form.email_doc()}},{type:'link',label:'Copy',display:function(){return in_list(profile.can_create,me.form.doctype)&&!me.form.meta.allow_copy},icon:'icon-file',onclick:function(){me.form.copy_doc()}},{type:'link',label:'Delete',display:function(){return(cint(me.form.doc.docstatus)!=1)&&!me.form.doc.__islocal&&wn.model.can_delete(me.form.doctype);},icon:'icon-remove-sign',onclick:function(){me.form.savetrash()}}]},{title:'Assign To',render:function(wrapper){me.form.assign_to=new wn.widgets.form.sidebar.AssignTo(wrapper,me,me.form.doctype,me.form.docname);},display:function(){return!me.form.doc.__islocal}},{title:'Attachments',render:function(wrapper){me.form.attachments=new wn.widgets.form.sidebar.Attachments(wrapper,me,me.form.doctype,me.form.docname);},display:function(){return me.form.meta.allow_attach}},{title:'Comments',render:function(wrapper){new wn.widgets.form.sidebar.Comments(wrapper,me,me.form.doctype,me.form.docname);},display:function(){return!me.form.doc.__islocal}},{title:'Tags',render:function(wrapper){me.form.taglist=new TagList(wrapper,me.form.doc._user_tags?me.form.doc._user_tags.split(','):[],me.form.doctype,me.form.docname,0,function(){});},display:function(){return!me.form.doc.__islocal}},{title:'Users',render:function(wrapper){var doc=cur_frm.doc;var scrub_date=function(d){if(d)t=d.split(' ');else return'';return dateutil.str_to_user(t[0])+' '+t[1];}
$(wrapper).html(repl('<p>Created:<br> <span class="avatar-small">\
       <img title="%(created_by)s" src="%(avatar_created)s" /></span> \
       <span class="help small">%(creation)s</span></p>\
       <p>Modified:<br> <span class="avatar-small">\
       <img title="%(modified_by)s" src="%(avatar_modified)s" /></span> \
       <span class="help small">%(modified)s</span></p>',{created_by:wn.user_info(doc.owner).fullname,avatar_created:wn.user_info(doc.owner).image,creation:scrub_date(doc.creation),modified_by:wn.user_info(doc.modified_by).fullname,avatar_modified:wn.user_info(doc.modified_by).image,modified:scrub_date(doc.modified)}));},display:function(){return!me.form.doc.__islocal}},{title:'Help',render:function(wrapper){$(wrapper).html('<div class="help small">'
+wn.markdown(me.form.meta.description)+'</div>')},display:function(){return me.form.meta.description}}]}
this.refresh=function(){var parent=this.form.page_layout.sidebar_area;if(!this.sidebar){this.sidebar=new wn.widgets.PageSidebar(parent,this.opts);}else{this.sidebar.refresh();}}}}
/*
 *	lib/js/legacy/wn/widgets/form/comments.js
 */
wn.widgets.form.sidebar.Comments=function(parent,sidebar,doctype,docname){var me=this;this.sidebar=sidebar;this.doctype=doctype;this.docname=docname;this.refresh=function(){$c('webnotes.widgets.form.comments.get_comments',{dt:me.doctype,dn:me.docname,limit:5},function(r,rt){wn.widgets.form.comments.sync(me.doctype,me.docname,r);me.make_body();});}
this.make_body=function(){if(this.wrapper)this.wrapper.innerHTML='';else this.wrapper=$a(parent,'div','sidebar-comment-wrapper');this.input=$a_input(this.wrapper,'text');this.btn=$btn(this.wrapper,'Post',function(){me.add_comment()},{marginLeft:'8px'});this.render_comments()}
this.render_comments=function(){var f=wn.widgets.form.comments;var cl=f.comment_list[me.docname]
this.msg=$a(this.wrapper,'div','help small');if(cl){this.msg.innerHTML=cl.length+' out of '+f.n_comments[me.docname]+' comments';if(f.n_comments[me.docname]>cl.length){this.msg.innerHTML+=' <span class="link_type" \
     onclick="cur_frm.show_comments()">Show all</span>'}
for(var i=0;i<cl.length;i++){this.render_one_comment(cl[i]);}}else{this.msg.innerHTML='Be the first one to comment.'}}
this.render_one_comment=function(det){$a(this.wrapper,'div','social sidebar-comment-text','',det.comment);$a(this.wrapper,'div','sidebar-comment-info','',comment_when(det.creation)+' by '+det.comment_by_fullname);}
this.add_comment=function(){if(!this.input.value)return;this.btn.set_working();wn.widgets.form.comments.add(this.input,me.doctype,me.docname,function(){me.btn.done_working();me.make_body();});}
this.refresh();}
/*
 *	lib/js/legacy/wn/widgets/form/attachments.js
 */
wn.widgets.form.sidebar.Attachments=function(parent,sidebar,doctype,docname){var me=this;this.frm=sidebar.form;this.make=function(){if(this.wrapper)this.wrapper.innerHTML='';else this.wrapper=$a(parent,'div','sidebar-comment-wrapper');this.attach_wrapper=$a(this.wrapper,'div');if(this.frm.doc.__islocal){this.attach_wrapper.innerHTML='<div class="help">Attachments can be \
    uploaded after saving</div>';return;}
var n=this.frm.doc.file_list?this.frm.doc.file_list.split('\n').length:0;if(n<this.frm.meta.max_attachments||!this.frm.meta.max_attachments){this.btn=$btn($a(this.wrapper,'div','sidebar-comment-message'),'Add',function(){me.add_attachment()});}
this.render();}
this.render=function(){this.attach_wrapper.innerHTML=''
var doc=locals[me.frm.doctype][me.frm.docname];var fl=doc.file_list?doc.file_list.split('\n'):[];for(var i=0;i<fl.length;i++){new wn.widgets.form.sidebar.Attachment(this.attach_wrapper,fl[i],me.frm)}}
this.add_attachment=function(){if(!this.dialog){this.dialog=new wn.widgets.Dialog({title:'Add Attachment',width:400})
$y(this.dialog.body,{margin:'13px'})
this.dialog.make();}
this.dialog.body.innerHTML='';this.dialog.show();wn.upload.make({parent:this.dialog.body,args:{from_form:1,doctype:doctype,docname:docname},callback:wn.widgets.form.file_upload_done});}
this.make();}
wn.widgets.form.sidebar.Attachment=function(parent,filedet,frm){filedet=filedet.split(',')
this.filename=filedet[0];this.fileid=filedet[1];this.frm=frm;var me=this;this.wrapper=$a(parent,'div','sidebar-comment-message');this.remove_fileid=function(){var doc=locals[me.frm.doctype][me.frm.docname];var fl=doc.file_list.split('\n');new_fl=[];for(var i=0;i<fl.length;i++){if(fl[i].split(',')[1]!=me.fileid)new_fl.push(fl[i]);}
doc.file_list=new_fl.join('\n');}
var display_name=this.fileid;if(this.fileid&&this.fileid.substr(0,8)=='FileData')
display_name=this.filename;this.ln=$a(this.wrapper,'a','link_type small',{},display_name);this.ln.href='files/'+this.fileid;this.ln.target='_blank';this.del=$a(this.wrapper,'span','close','','&#215;');this.del.onclick=function(){var yn=confirm("Are you sure you want to delete the attachment?")
if(yn){var callback=function(r,rt){locals[me.frm.doctype][me.frm.docname].modified=r.message;$dh(me.wrapper);me.remove_fileid();frm.refresh();}
$c('webnotes.widgets.form.utils.remove_attach',args={'fid':me.fileid,dt:me.frm.doctype,dn:me.frm.docname},callback);}}}
wn.widgets.form.file_upload_done=function(doctype,docname,fileid,filename,at_id,new_timestamp){var doc=locals[doctype][docname];if(doc.file_list){var fl=doc.file_list.split('\n')
fl.push(filename+','+fileid)
doc.file_list=fl.join('\n');}
else
doc.file_list=filename+','+fileid;doc.modified=new_timestamp;var frm=wn.views.formview[doctype].frm;frm.attachments.dialog.hide();msgprint('File Uploaded Sucessfully.');frm.refresh();}
/*
 *	lib/js/legacy/wn/widgets/form/assign_to.js
 */
wn.widgets.form.sidebar.AssignTo=Class.extend({init:function(parent,sidebar,doctype,docname){var me=this;this.doctype=doctype;this.name=docname;this.wrapper=$a(parent,'div','sidebar-comment-wrapper');this.body=$a(this.wrapper,'div');this.add_btn=$btn($a(this.wrapper,'div','sidebar-comment-message'),'Assign',function(){me.add();})
this.refresh();},refresh:function(){var me=this;$c('webnotes.widgets.form.assign_to.get',{doctype:me.doctype,name:me.name},function(r,rt){me.render(r.message)})},render:function(d){var me=this;$(this.body).empty();if(this.dialog){this.dialog.hide();}
for(var i=0;i<d.length;i++){$(this.body).append(repl('<div>%(owner)s \
    <a class="close" href="#" data-owner="%(owner)s">&#215</a></div>',d[i]))}
$(this.body).find('a.close').click(function(){$c('webnotes.widgets.form.assign_to.remove',{doctype:me.doctype,name:me.name,assign_to:$(this).attr('data-owner')},function(r,rt){me.render(r.message);});return false;});},add:function(){var me=this;if(!me.dialog){me.dialog=new wn.widgets.Dialog({title:'Add to To Do',width:350,fields:[{fieldtype:'Link',fieldname:'assign_to',options:'Profile',label:'Assign To',description:'Add to To Do List of',reqd:true},{fieldtype:'Data',fieldname:'description',label:'Comment'},{fieldtype:'Date',fieldname:'date',label:'Complete By'},{fieldtype:'Select',fieldname:'priority',label:'Priority',options:'Low\nMedium\nHigh','default':'Medium'},{fieldtype:'Check',fieldname:'notify',label:'Notify By Email'},{fieldtype:'Button',label:'Add',fieldname:'add_btn'}]});me.dialog.fields_dict.add_btn.input.onclick=function(){var assign_to=me.dialog.fields_dict.assign_to.get_value();if(assign_to){$c('webnotes.widgets.form.assign_to.add',{doctype:me.doctype,name:me.name,assign_to:assign_to,description:me.dialog.fields_dict.description.get_value(),priority:me.dialog.fields_dict.priority.get_value(),date:me.dialog.fields_dict.date.get_value(),notify:me.dialog.fields_dict.notify.get_value()},function(r,rt){me.render(r.message);});}}}
me.dialog.clear();me.dialog.show();}});
/*
 *	lib/js/wn/app.js
 */
wn.Application=Class.extend({init:function(){var me=this;if(window.app){wn.call({method:'startup',callback:function(r,rt){wn.provide('wn.boot');wn.boot=r;if(wn.boot.profile.name=='Guest'){window.location='index.html';return;}
me.startup();}})}else{this.startup();}},startup:function(){this.load_bootinfo();this.make_page_container();this.make_nav_bar();this.set_favicon();$(document).trigger('startup');if(wn.boot){wn.route();}
$(document).trigger('app_ready');},load_bootinfo:function(){if(wn.boot){LocalDB.sync(wn.boot.docs);wn.control_panel=wn.boot.control_panel;if(wn.boot.error_messages)
console.log(wn.boot.error_messages)
if(wn.boot.server_messages)
msgprint(wn.boot.server_messages);this.set_globals();}else{this.set_as_guest();}},set_globals:function(){profile=wn.boot.profile;user=wn.boot.profile.name;user_fullname=wn.user_info(user).fullname;user_defaults=profile.defaults;user_roles=profile.roles;user_email=profile.email;sys_defaults=wn.boot.sysdefaults;},set_as_guest:function(){profile={name:'Guest'};user='Guest';user_fullname='Guest';user_defaults={};user_roles=['Guest'];user_email='';sys_defaults={};},make_page_container:function(){wn.container=new wn.views.Container();wn.views.make_403();wn.views.make_404();},make_nav_bar:function(){if(wn.boot){wn.container.wntoolbar=new wn.ui.toolbar.Toolbar();}},logout:function(){var me=this;me.logged_out=true;wn.call({method:'logout',callback:function(r){if(r.exc){console.log(r.exc);}
me.redirect_to_login();}})},redirect_to_login:function(){window.location.href='index.html';},set_favicon:function(){var link=$('link[type="image/x-icon"]').remove().attr("href");var favicon='\
   <link rel="shortcut icon" href="'+link+'" type="image/x-icon"> \
   <link rel="icon" href="'+link+'" type="image/x-icon">'
$(favicon).appendTo('head');}})
/*
 *	erpnext/startup/startup.js
 */
var current_module;var is_system_manager=0;wn.provide('erpnext.startup');erpnext.modules={'Selling':'selling-home','Accounts':'accounts-home','Stock':'stock-home','Buying':'buying-home','Support':'support-home','Projects':'projects-home','Production':'production-home','Website':'website-home','HR':'hr-home','Setup':'Setup','Activity':'activity','To Do':'todo','Calendar':'calendar','Messages':'messages','Knowledge Base':'questions','Dashboard':'dashboard'}
wn.provide('wn.modules');$.extend(wn.modules,erpnext.modules);wn.modules['Core']='Setup';erpnext.startup.set_globals=function(){if(inList(user_roles,'System Manager'))is_system_manager=1;}
erpnext.startup.start=function(){console.log('Starting up...');$('#startup_div').html('Starting up...').toggle(true);erpnext.startup.set_globals();if(user!='Guest'){if(wn.boot.user_background){erpnext.set_user_background(wn.boot.user_background);}
wn.boot.profile.allow_modules=wn.boot.profile.allow_modules.concat(['To Do','Knowledge Base','Calendar','Activity','Messages'])
erpnext.toolbar.setup();erpnext.startup.set_periodic_updates();$('footer').html('<div class="web-footer erpnext-footer">\
   <a href="#!attributions">ERPNext | Attributions and License</a></div>');if(in_list(user_roles,'System Manager')&&(wn.boot.setup_complete=='No')){wn.require("js/complete_setup.js");erpnext.complete_setup.show();}
if(wn.boot.expires_on&&in_list(user_roles,'System Manager')){var today=dateutil.str_to_obj(dateutil.get_today());var expires_on=dateutil.str_to_obj(wn.boot.expires_on);var diff=dateutil.get_diff(expires_on,today);if(0<=diff&&diff<=15){var expiry_string=diff==0?"today":repl("in %(diff)s day(s)",{diff:diff});$('header').append(repl('<div class="expiry-info"> \
     Your ERPNext subscription will <b>expire %(expiry_string)s</b>. \
     Please renew your subscription to continue using ERPNext \
     (and remove this annoying banner). \
    </div>',{expiry_string:expiry_string}));}else if(diff<0){$('header').append(repl('<div class="expiry-info"> \
     This ERPNext subscription <b>has expired</b>. \
    </div>',{expiry_string:expiry_string}));}}
erpnext.set_about();if(wn.control_panel.custom_startup_code)
eval(wn.control_panel.custom_startup_code);}
$('body').append('<a class="erpnext-logo" title="Powered by ERPNext" \
  href="http://erpnext.com" target="_blank"></a>')}
erpnext.update_messages=function(reset){if(inList(['Guest'],user)||!wn.session_alive){return;}
if(!reset){var set_messages=function(r){if(!r.exc){erpnext.toolbar.set_new_comments(r.message.unread_messages);var show_in_circle=function(parent_id,msg){var parent=$('#'+parent_id);if(parent){if(msg){parent.find('span:first').text(msg);parent.toggle(true);}else{parent.toggle(false);}}}
show_in_circle('unread_messages',r.message.unread_messages.length);show_in_circle('open_support_tickets',r.message.open_support_tickets);show_in_circle('things_todo',r.message.things_todo);show_in_circle('todays_events',r.message.todays_events);show_in_circle('open_tasks',r.message.open_tasks);show_in_circle('unanswered_questions',r.message.unanswered_questions);}else{clearInterval(wn.updates.id);}}
wn.call({method:'startup.startup.get_global_status_messages',callback:set_messages});}else{erpnext.toolbar.set_new_comments(0);$('#unread_messages').toggle(false);}}
erpnext.startup.set_periodic_updates=function(){wn.updates={};if(wn.updates.id){clearInterval(wn.updates.id);}
wn.updates.id=setInterval(erpnext.update_messages,60000);}
erpnext.set_user_background=function(src){set_style(repl('#body_div { background: url("files/%(src)s") repeat;}',{src:src}))}
$(document).bind('startup',function(){erpnext.startup.start();});erpnext.send_message=function(opts){if(opts.btn){$(opts.btn).start_working();}
wn.call({method:'website.send_message',args:opts,callback:function(r){if(opts.btn){$(opts.btn).done_working();}
if(opts.callback)opts.callback(r)}});}
erpnext.hide_naming_series=function(){if(cur_frm.fields_dict.naming_series){hide_field('naming_series');if(cur_frm.doc.__islocal){unhide_field('naming_series');}}}
/*
 *	erpnext/startup/js/modules.js
 */
wn.provide('erpnext.module_page');erpnext.module_page.setup_page=function(module,wrapper){erpnext.module_page.hide_links(wrapper);erpnext.module_page.make_list(module,wrapper);$(wrapper).find("a[title]").tooltip({delay:{show:500,hide:100}});}
erpnext.module_page.hide_links=function(wrapper){$(wrapper).find('[href*="List/"]').each(function(){var href=$(this).attr('href');var dt=href.split('/')[1];if(wn.boot.profile.all_read.indexOf(get_label_doctype(dt))==-1){var txt=$(this).text();$(this).parent().css('color','#999').html(txt);}});$(wrapper).find('[data-doctype]').each(function(){var dt=$(this).attr('data-doctype');if(wn.boot.profile.all_read.indexOf(dt)==-1){var txt=$(this).text();$(this).parent().css('color','#999').html(txt);}});$(wrapper).find('[href*="Form/"]').each(function(){var href=$(this).attr('href');var dt=href.split('/')[1];if(wn.boot.profile.all_read.indexOf(get_label_doctype(dt))==-1){var txt=$(this).text();$(this).parent().css('color','#999').html(txt);}});}
erpnext.module_page.make_list=function(module,wrapper){var $w=$(wrapper).find('.reports-list');var $parent1=$('<div style="width: 45%; float: left; margin-right: 4.5%"></div>').appendTo($w);var $parent2=$('<div style="width: 45%; float: left;"></div>').appendTo($w);wrapper.list1=new wn.ui.Listing({parent:$parent1,method:'utilities.get_sc_list',render_row:function(row,data){if(!data.parent_doc_type)data.parent_doc_type=data.doc_type;$(row).html(repl('<a href="#!Report/%(doc_type)s/%(criteria_name)s" \
    data-doctype="%(parent_doc_type)s">\
    %(criteria_name)s</a>',data))},args:{module:module},no_refresh:true,callback:function(r){erpnext.module_page.hide_links($parent1)}});wrapper.list1.run();wrapper.list2=new wn.ui.Listing({parent:$parent2,method:'utilities.get_report_list',render_row:function(row,data){$(row).html(repl('<a href="#!Report2/%(ref_doctype)s/%(name)s" \
    data-doctype="%(ref_doctype)s">\
    %(name)s</a>',data))},args:{module:module},no_refresh:true,callback:function(r){erpnext.module_page.hide_links($parent2)}});wrapper.list2.run();$parent1.find('.list-toolbar-wrapper').prepend("<div class=\"show-all-reports\">\
   <a href=\"#List/Search Criteria\"> [ List Of All Reports ]</a></div>");$parent2.find('.list-toolbar-wrapper').prepend("<div class=\"show-all-reports\">\
   <a href=\"#List/Report\"> [ List Of All Reports (New) ]</a></div>");}
/*
 *	erpnext/startup/js/toolbar.js
 */
wn.provide('erpnext.toolbar');erpnext.toolbar.setup=function(){erpnext.toolbar.add_modules();$('#toolbar-user').append('<li><a href="#!profile-settings">Profile Settings</a></li>');$('.navbar .pull-right').append('\
  <li><a href="#!messages" title="Unread Messages"><span class="navbar-new-comments"></span></a></li>');$('.navbar .pull-right').prepend('<li class="dropdown">\
  <a class="dropdown-toggle" data-toggle="dropdown" href="#" \
   onclick="return false;">Help<b class="caret"></b></a>\
  <ul class="dropdown-menu" id="toolbar-help">\
  </ul></li>')
$('#toolbar-help').append('<li><a href="https://erpnext.com/manual" target="_blank">\
  Documentation</a></li>')
$('#toolbar-help').append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">\
  Forum</a></li>')
$('#toolbar-help').append('<li><a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
  Live Chat (Office Hours)</a></li>')
erpnext.toolbar.set_new_comments();}
erpnext.toolbar.add_modules=function(){$('<li class="dropdown">\
  <a class="dropdown-toggle" data-toggle="dropdown" href="#"\
   onclick="return false;">Modules<b class="caret"></b></a>\
  <ul class="dropdown-menu modules">\
  </ul>\
  </li>').prependTo('.navbar .nav:first');if(wn.boot.modules_list&&typeof(wn.boot.modules_list)=='string'){wn.boot.modules_list=JSON.parse(wn.boot.modules_list);}
else
wn.boot.modules_list=keys(erpnext.modules).sort();for(var i in wn.boot.modules_list){var m=wn.boot.modules_list[i]
if(m!='Setup'&&wn.boot.profile.allow_modules.indexOf(m)!=-1){args={module:m,module_page:erpnext.modules[m],module_label:m=='HR'?'Human Resources':m}
$('.navbar .modules').append(repl('<li><a href="#!%(module_page)s" \
    data-module="%(module)s">%(module_label)s</a></li>',args));}}
if(user_roles.indexOf("Accounts Manager")!=-1){$('.navbar .modules').append('<li><a href="#!dashboard" \
   data-module="Dashboard">Dashboard</a></li>');}
if(user_roles.indexOf("System Manager")!=-1){$('.navbar .modules').append('<li class="divider"></li>\
  <li><a href="#!Setup" data-module="Setup">Setup</a></li>');}}
erpnext.toolbar.set_new_comments=function(new_comments){var navbar_nc=$('.navbar-new-comments');if(new_comments&&new_comments.length>0){navbar_nc.text(new_comments.length);navbar_nc.addClass('navbar-new-comments-true')
$.each(new_comments,function(i,v){var msg='New Message: '+(v[1].length<=100?v[1]:(v[1].substr(0,100)+"..."));var id=v[0].replace('/','-');if(!$('#'+id)[0]){show_alert(msg,id);}})}else{navbar_nc.removeClass('navbar-new-comments-true');navbar_nc.text(0);}}
/*
 *	erpnext/startup/js/feature_setup.js
 */
pscript.feature_dict={'fs_projects':{'BOM':{'fields':['project_name']},'Delivery Note':{'fields':['project_name']},'Purchase Invoice':{'entries':['project_name']},'Production Order':{'fields':['project_name']},'Purchase Order':{'po_details':['project_name']},'Purchase Receipt':{'purchase_receipt_details':['project_name']},'Sales Invoice':{'fields':['project_name']},'Sales Order':{'fields':['project_name']},'Stock Entry':{'fields':['project_name']},'Timesheet':{'timesheet_details':['project_name']}},'fs_packing_details':{},'fs_discounts':{'Delivery Note':{'delivery_note_details':['adj_rate']},'Quotation':{'quotation_details':['adj_rate']},'Sales Invoice':{'entries':['adj_rate']},'Sales Order':{'sales_order_details':['adj_rate','ref_rate']}},'fs_purchase_discounts':{'Purchase Order':{'po_details':['purchase_ref_rate','discount_rate','import_ref_rate']},'Purchase Receipt':{'purchase_receipt_details':['purchase_ref_rate','discount_rate','import_ref_rate']},'Purchase Invoice':{'entries':['purchase_ref_rate','discount_rate','import_ref_rate']}},'fs_brands':{'Delivery Note':{'delivery_note_details':['brand']},'Purchase Request':{'indent_details':['brand']},'Item':{'fields':['brand']},'Purchase Order':{'po_details':['brand']},'Purchase Invoice':{'entries':['brand']},'Quotation':{'quotation_details':['brand']},'Sales Invoice':{'entries':['brand']},'Sales BOM':{'fields':['new_item_brand']},'Sales Order':{'sales_order_details':['brand']},'Serial No':{'fields':['brand']}},'fs_after_sales_installations':{'Delivery Note':{'fields':['installation_status','per_installed'],'delivery_note_details':['installed_qty']}},'fs_item_batch_nos':{'Delivery Note':{'delivery_note_details':['batch_no']},'Item':{'fields':['has_batch_no']},'Purchase Receipt':{'purchase_receipt_details':['batch_no']},'Quality Inspection':{'fields':['batch_no']},'Sales and Pruchase Return Wizard':{'return_details':['batch_no']},'Sales Invoice':{'entries':['batch_no']},'Stock Entry':{'mtn_details':['batch_no']},'Stock Ledger Entry':{'fields':['batch_no']}},'fs_item_serial_nos':{'Customer Issue':{'fields':['serial_no']},'Delivery Note':{'delivery_note_details':['serial_no'],'packing_details':['serial_no']},'Installation Note':{'installed_item_details':['serial_no']},'Item':{'fields':['has_serial_no']},'Maintenance Schedule':{'item_maintenance_detail':['serial_no'],'maintenance_schedule_detail':['serial_no']},'Maintenance Visit':{'maintenance_visit_details':['serial_no']},'Purchase Receipt':{'purchase_receipt_details':['serial_no']},'Quality Inspection':{'fields':['item_serial_no']},'Sales and Pruchase Return Wizard':{'return_details':['serial_no']},'Sales Invoice':{'entries':['serial_no']},'Stock Entry':{'mtn_details':['serial_no']},'Stock Ledger Entry':{'fields':['serial_no']}},'fs_item_barcode':{'Item':{'fields':['barcode']},'Delivery Note':{'delivery_note_details':['barcode']},'Sales Invoice':{'entries':['barcode']}},'fs_item_group_in_details':{'Delivery Note':{'delivery_note_details':['item_group']},'Opportunity':{'enquiry_details':['item_group']},'Purchase Request':{'indent_details':['item_group']},'Item':{'fields':['item_group']},'Global Defaults':{'fields':['default_item_group']},'Purchase Order':{'po_details':['item_group']},'Purchase Receipt':{'purchase_receipt_details':['item_group']},'Purchase Voucher':{'entries':['item_group']},'Quotation':{'quotation_details':['item_group']},'Sales Invoice':{'entries':['item_group']},'Sales BOM':{'fields':['serial_no']},'Sales Order':{'sales_order_details':['item_group']},'Serial No':{'fields':['item_group']},'Sales Partner':{'partner_target_details':['item_group']},'Sales Person':{'target_details':['item_group']},'Territory':{'target_details':['item_group']}},'fs_page_break':{'Delivery Note':{'delivery_note_details':['page_break'],'packing_details':['page_break']},'Purchase Request':{'indent_details':['page_break']},'Purchase Order':{'po_details':['page_break']},'Purchase Receipt':{'purchase_receipt_details':['page_break']},'Purchase Voucher':{'entries':['page_break']},'Quotation':{'quotation_details':['page_break']},'Sales Invoice':{'entries':['page_break']},'Sales Order':{'sales_order_details':['page_break']}},'fs_exports':{'Delivery Note':{'fields':['Note','conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'delivery_note_details':['base_ref_rate','amount','basic_rate']},'POS Setting':{'fields':['conversion_rate','currency']},'Quotation':{'fields':['Note HTML','OT Notes','conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'quotation_details':['base_ref_rate','amount','basic_rate']},'Sales Invoice':{'fields':['conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'entries':['base_ref_rate','amount','basic_rate']},'Item':{'ref_rate_details':['ref_currency']},'Sales BOM':{'fields':['currency']},'Sales Order':{'fields':['Note1','OT Notes','conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'sales_order_details':['base_ref_rate','amount','basic_rate']}},'fs_imports':{'Purchase Invoice':{'fields':['conversion_rate','currency','grand_total_import','in_words_import','net_total_import','other_charges_added_import','other_charges_deducted_import'],'entries':['purchase_ref_rate','amount','rate']},'Purchase Order':{'fields':['Note HTML','conversion_rate','currency','grand_total_import','in_words_import','net_total_import','other_charges_added_import','other_charges_deducted_import'],'po_details':['purchase_ref_rate','amount','purchase_rate']},'Purchase Receipt':{'fields':['conversion_rate','currency','grand_total_import','in_words_import','net_total_import','other_charges_added_import','other_charges_deducted_import'],'purchase_receipt_details':['purchase_ref_rate','amount','purchase_rate']},'Supplier Quotation':{'fields':['conversion_rate','currency']}},'fs_item_advanced':{'Item':{'fields':['item_customer_details']}},'fs_sales_extras':{'Address':{'fields':['sales_partner']},'Contact':{'fields':['sales_partner']},'Customer':{'fields':['sales_team']},'Delivery Note':{'fields':['sales_team','Packing List']},'Item':{'fields':['item_customer_details']},'Sales Invoice':{'fields':['sales_team']},'Sales Order':{'fields':['sales_team','Packing List']}},'fs_more_info':{'Delivery Note':{'fields':['More Info']},'Opportunity':{'fields':['More Info']},'Purchase Request':{'fields':['More Info']},'Lead':{'fields':['More Info']},'Purchase Invoice':{'fields':['More Info']},'Purchase Order':{'fields':['More Info']},'Purchase Receipt':{'fields':['More Info']},'Quotation':{'fields':['More Info']},'Sales Invoice':{'fields':['More Info']},'Sales Order':{'fields':['More Info']},},'fs_quality':{'Item':{'fields':['Item Inspection Criteria','inspection_required']},'Purchase Receipt':{'purchase_receipt_details':['qa_no']}},'fs_manufacturing':{'Item':{'fields':['Manufacturing']}},'fs_pos':{'Sales Invoice':{'fields':['is_pos']}},'fs_recurring_invoice':{'Sales Invoice':{'fields':['Recurring Invoice']}}}
$(document).bind('form_refresh',function(){for(sys_feat in sys_defaults)
{if(sys_defaults[sys_feat]=='0'&&(sys_feat in pscript.feature_dict))
{if(cur_frm.doc.doctype in pscript.feature_dict[sys_feat])
{for(fort in pscript.feature_dict[sys_feat][cur_frm.doc.doctype])
{if(fort=='fields')
hide_field(pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort]);else if(cur_frm.fields_dict[fort])
{for(grid_field in pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort])
cur_frm.fields_dict[fort].grid.set_column_disp(pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort][grid_field],false);}
else
msgprint('Grid "'+fort+'" does not exists');}}}}})
/*
 *	conf.js
 */
wn.provide('erpnext');erpnext.set_about=function(){wn.provide('wn.app');$.extend(wn.app,{name:'ERPNext',license:'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',source:'https://github.com/webnotes/erpnext',publisher:'Web Notes Technologies Pvt Ltd, Mumbai',copyright:'&copy; Web Notes Technologies Pvt Ltd',version:'2'});}
wn.modules_path='erpnext';$(document).bind('toolbar_setup',function(){$('.brand').html((wn.boot.website_settings.brand_html||'erpnext')+' <i class="icon-home icon-white navbar-icon-home" ></i>').css('max-width','200px').css('overflow','hidden').hover(function(){$(this).find('.icon-home').addClass('navbar-icon-home-hover');},function(){$(this).find('.icon-home').removeClass('navbar-icon-home-hover');});});