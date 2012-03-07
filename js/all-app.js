
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
 *	lib/js/legacy/jquery/jquery-ui.min.js
 *//*
 * jQuery UI 1.7.3
 *
 * Copyright (c) 2009 AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT (MIT-LICENSE.txt)
 * and GPL (GPL-LICENSE.txt) licenses.
 *
 * http://docs.jquery.com/UI
 */
jQuery.ui||(function(c){var i=c.fn.remove,d=c.browser.mozilla&&(parseFloat(c.browser.version)<1.9);c.ui={version:"1.7.3",plugin:{add:function(k,l,n){var m=c.ui[k].prototype;for(var j in n){m.plugins[j]=m.plugins[j]||[];m.plugins[j].push([l,n[j]])}},call:function(j,l,k){var n=j.plugins[l];if(!n||!j.element[0].parentNode){return}for(var m=0;m<n.length;m++){if(j.options[n[m][0]]){n[m][1].apply(j.element,k)}}}},contains:function(k,j){return document.compareDocumentPosition?k.compareDocumentPosition(j)&16:k!==j&&k.contains(j)},hasScroll:function(m,k){if(c(m).css("overflow")=="hidden"){return false}var j=(k&&k=="left")?"scrollLeft":"scrollTop",l=false;if(m[j]>0){return true}m[j]=1;l=(m[j]>0);m[j]=0;return l},isOverAxis:function(k,j,l){return(k>j)&&(k<(j+l))},isOver:function(o,k,n,m,j,l){return c.ui.isOverAxis(o,n,j)&&c.ui.isOverAxis(k,m,l)},keyCode:{BACKSPACE:8,CAPS_LOCK:20,COMMA:188,CONTROL:17,DELETE:46,DOWN:40,END:35,ENTER:13,ESCAPE:27,HOME:36,INSERT:45,LEFT:37,NUMPAD_ADD:107,NUMPAD_DECIMAL:110,NUMPAD_DIVIDE:111,NUMPAD_ENTER:108,NUMPAD_MULTIPLY:106,NUMPAD_SUBTRACT:109,PAGE_DOWN:34,PAGE_UP:33,PERIOD:190,RIGHT:39,SHIFT:16,SPACE:32,TAB:9,UP:38}};if(d){var f=c.attr,e=c.fn.removeAttr,h="http://www.w3.org/2005/07/aaa",a=/^aria-/,b=/^wairole:/;c.attr=function(k,j,l){var m=l!==undefined;return(j=="role"?(m?f.call(this,k,j,"wairole:"+l):(f.apply(this,arguments)||"").replace(b,"")):(a.test(j)?(m?k.setAttributeNS(h,j.replace(a,"aaa:"),l):f.call(this,k,j.replace(a,"aaa:"))):f.apply(this,arguments)))};c.fn.removeAttr=function(j){return(a.test(j)?this.each(function(){this.removeAttributeNS(h,j.replace(a,""))}):e.call(this,j))}}c.fn.extend({remove:function(j,k){return this.each(function(){if(!k){if(!j||c.filter(j,[this]).length){c("*",this).add(this).each(function(){c(this).triggerHandler("remove")})}}return i.call(c(this),j,k)})},enableSelection:function(){return this.attr("unselectable","off").css("MozUserSelect","").unbind("selectstart.ui")},disableSelection:function(){return this.attr("unselectable","on").css("MozUserSelect","none").bind("selectstart.ui",function(){return false})},scrollParent:function(){var j;if((c.browser.msie&&(/(static|relative)/).test(this.css("position")))||(/absolute/).test(this.css("position"))){j=this.parents().filter(function(){return(/(relative|absolute|fixed)/).test(c.curCSS(this,"position",1))&&(/(auto|scroll)/).test(c.curCSS(this,"overflow",1)+c.curCSS(this,"overflow-y",1)+c.curCSS(this,"overflow-x",1))}).eq(0)}else{j=this.parents().filter(function(){return(/(auto|scroll)/).test(c.curCSS(this,"overflow",1)+c.curCSS(this,"overflow-y",1)+c.curCSS(this,"overflow-x",1))}).eq(0)}return(/fixed/).test(this.css("position"))||!j.length?c(document):j}});c.extend(c.expr[":"],{data:function(l,k,j){return !!c.data(l,j[3])},focusable:function(k){var l=k.nodeName.toLowerCase(),j=c.attr(k,"tabindex");return(/input|select|textarea|button|object/.test(l)?!k.disabled:"a"==l||"area"==l?k.href||!isNaN(j):!isNaN(j))&&!c(k)["area"==l?"parents":"closest"](":hidden").length},tabbable:function(k){var j=c.attr(k,"tabindex");return(isNaN(j)||j>=0)&&c(k).is(":focusable")}});function g(m,n,o,l){function k(q){var p=c[m][n][q]||[];return(typeof p=="string"?p.split(/,?\s+/):p)}var j=k("getter");if(l.length==1&&typeof l[0]=="string"){j=j.concat(k("getterSetter"))}return(c.inArray(o,j)!=-1)}c.widget=function(k,j){var l=k.split(".")[0];k=k.split(".")[1];c.fn[k]=function(p){var n=(typeof p=="string"),o=Array.prototype.slice.call(arguments,1);if(n&&p.substring(0,1)=="_"){return this}if(n&&g(l,k,p,o)){var m=c.data(this[0],k);return(m?m[p].apply(m,o):undefined)}return this.each(function(){var q=c.data(this,k);(!q&&!n&&c.data(this,k,new c[l][k](this,p))._init());(q&&n&&c.isFunction(q[p])&&q[p].apply(q,o))})};c[l]=c[l]||{};c[l][k]=function(o,n){var m=this;this.namespace=l;this.widgetName=k;this.widgetEventPrefix=c[l][k].eventPrefix||k;this.widgetBaseClass=l+"-"+k;this.options=c.extend({},c.widget.defaults,c[l][k].defaults,c.metadata&&c.metadata.get(o)[k],n);this.element=c(o).bind("setData."+k,function(q,p,r){if(q.target==o){return m._setData(p,r)}}).bind("getData."+k,function(q,p){if(q.target==o){return m._getData(p)}}).bind("remove",function(){return m.destroy()})};c[l][k].prototype=c.extend({},c.widget.prototype,j);c[l][k].getterSetter="option"};c.widget.prototype={_init:function(){},destroy:function(){this.element.removeData(this.widgetName).removeClass(this.widgetBaseClass+"-disabled "+this.namespace+"-state-disabled").removeAttr("aria-disabled")},option:function(l,m){var k=l,j=this;if(typeof l=="string"){if(m===undefined){return this._getData(l)}k={};k[l]=m}c.each(k,function(n,o){j._setData(n,o)})},_getData:function(j){return this.options[j]},_setData:function(j,k){this.options[j]=k;if(j=="disabled"){this.element[k?"addClass":"removeClass"](this.widgetBaseClass+"-disabled "+this.namespace+"-state-disabled").attr("aria-disabled",k)}},enable:function(){this._setData("disabled",false)},disable:function(){this._setData("disabled",true)},_trigger:function(l,m,n){var p=this.options[l],j=(l==this.widgetEventPrefix?l:this.widgetEventPrefix+l);m=c.Event(m);m.type=j;if(m.originalEvent){for(var k=c.event.props.length,o;k;){o=c.event.props[--k];m[o]=m.originalEvent[o]}}this.element.trigger(m,n);return !(c.isFunction(p)&&p.call(this.element[0],m,n)===false||m.isDefaultPrevented())}};c.widget.defaults={disabled:false};c.ui.mouse={_mouseInit:function(){var j=this;this.element.bind("mousedown."+this.widgetName,function(k){return j._mouseDown(k)}).bind("click."+this.widgetName,function(k){if(j._preventClickEvent){j._preventClickEvent=false;k.stopImmediatePropagation();return false}});if(c.browser.msie){this._mouseUnselectable=this.element.attr("unselectable");this.element.attr("unselectable","on")}this.started=false},_mouseDestroy:function(){this.element.unbind("."+this.widgetName);(c.browser.msie&&this.element.attr("unselectable",this._mouseUnselectable))},_mouseDown:function(l){l.originalEvent=l.originalEvent||{};if(l.originalEvent.mouseHandled){return}(this._mouseStarted&&this._mouseUp(l));this._mouseDownEvent=l;var k=this,m=(l.which==1),j=(typeof this.options.cancel=="string"?c(l.target).parents().add(l.target).filter(this.options.cancel).length:false);if(!m||j||!this._mouseCapture(l)){return true}this.mouseDelayMet=!this.options.delay;if(!this.mouseDelayMet){this._mouseDelayTimer=setTimeout(function(){k.mouseDelayMet=true},this.options.delay)}if(this._mouseDistanceMet(l)&&this._mouseDelayMet(l)){this._mouseStarted=(this._mouseStart(l)!==false);if(!this._mouseStarted){l.preventDefault();return true}}this._mouseMoveDelegate=function(n){return k._mouseMove(n)};this._mouseUpDelegate=function(n){return k._mouseUp(n)};c(document).bind("mousemove."+this.widgetName,this._mouseMoveDelegate).bind("mouseup."+this.widgetName,this._mouseUpDelegate);(c.browser.safari||l.preventDefault());l.originalEvent.mouseHandled=true;return true},_mouseMove:function(j){if(c.browser.msie&&!j.button){return this._mouseUp(j)}if(this._mouseStarted){this._mouseDrag(j);return j.preventDefault()}if(this._mouseDistanceMet(j)&&this._mouseDelayMet(j)){this._mouseStarted=(this._mouseStart(this._mouseDownEvent,j)!==false);(this._mouseStarted?this._mouseDrag(j):this._mouseUp(j))}return !this._mouseStarted},_mouseUp:function(j){c(document).unbind("mousemove."+this.widgetName,this._mouseMoveDelegate).unbind("mouseup."+this.widgetName,this._mouseUpDelegate);if(this._mouseStarted){this._mouseStarted=false;this._preventClickEvent=(j.target==this._mouseDownEvent.target);this._mouseStop(j)}return false},_mouseDistanceMet:function(j){return(Math.max(Math.abs(this._mouseDownEvent.pageX-j.pageX),Math.abs(this._mouseDownEvent.pageY-j.pageY))>=this.options.distance)},_mouseDelayMet:function(j){return this.mouseDelayMet},_mouseStart:function(j){},_mouseDrag:function(j){},_mouseStop:function(j){},_mouseCapture:function(j){return true}};c.ui.mouse.defaults={cancel:null,distance:1,delay:0}})(jQuery);;/*
 * jQuery UI Selectable 1.7.3
 *
 * Copyright (c) 2009 AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT (MIT-LICENSE.txt)
 * and GPL (GPL-LICENSE.txt) licenses.
 *
 * http://docs.jquery.com/UI/Selectables
 *
 * Depends:
 *	ui.core.js
 */
(function(a){a.widget("ui.selectable",a.extend({},a.ui.mouse,{_init:function(){var b=this;this.element.addClass("ui-selectable");this.dragged=false;var c;this.refresh=function(){c=a(b.options.filter,b.element[0]);c.each(function(){var d=a(this);var e=d.offset();a.data(this,"selectable-item",{element:this,$element:d,left:e.left,top:e.top,right:e.left+d.outerWidth(),bottom:e.top+d.outerHeight(),startselected:false,selected:d.hasClass("ui-selected"),selecting:d.hasClass("ui-selecting"),unselecting:d.hasClass("ui-unselecting")})})};this.refresh();this.selectees=c.addClass("ui-selectee");this._mouseInit();this.helper=a(document.createElement("div")).css({border:"1px dotted black"}).addClass("ui-selectable-helper")},destroy:function(){this.element.removeClass("ui-selectable ui-selectable-disabled").removeData("selectable").unbind(".selectable");this._mouseDestroy()},_mouseStart:function(d){var b=this;this.opos=[d.pageX,d.pageY];if(this.options.disabled){return}var c=this.options;this.selectees=a(c.filter,this.element[0]);this._trigger("start",d);a(c.appendTo).append(this.helper);this.helper.css({"z-index":100,position:"absolute",left:d.clientX,top:d.clientY,width:0,height:0});if(c.autoRefresh){this.refresh()}this.selectees.filter(".ui-selected").each(function(){var e=a.data(this,"selectable-item");e.startselected=true;if(!d.metaKey){e.$element.removeClass("ui-selected");e.selected=false;e.$element.addClass("ui-unselecting");e.unselecting=true;b._trigger("unselecting",d,{unselecting:e.element})}});a(d.target).parents().andSelf().each(function(){var e=a.data(this,"selectable-item");if(e){e.$element.removeClass("ui-unselecting").addClass("ui-selecting");e.unselecting=false;e.selecting=true;e.selected=true;b._trigger("selecting",d,{selecting:e.element});return false}})},_mouseDrag:function(i){var c=this;this.dragged=true;if(this.options.disabled){return}var e=this.options;var d=this.opos[0],h=this.opos[1],b=i.pageX,g=i.pageY;if(d>b){var f=b;b=d;d=f}if(h>g){var f=g;g=h;h=f}this.helper.css({left:d,top:h,width:b-d,height:g-h});this.selectees.each(function(){var j=a.data(this,"selectable-item");if(!j||j.element==c.element[0]){return}var k=false;if(e.tolerance=="touch"){k=(!(j.left>b||j.right<d||j.top>g||j.bottom<h))}else{if(e.tolerance=="fit"){k=(j.left>d&&j.right<b&&j.top>h&&j.bottom<g)}}if(k){if(j.selected){j.$element.removeClass("ui-selected");j.selected=false}if(j.unselecting){j.$element.removeClass("ui-unselecting");j.unselecting=false}if(!j.selecting){j.$element.addClass("ui-selecting");j.selecting=true;c._trigger("selecting",i,{selecting:j.element})}}else{if(j.selecting){if(i.metaKey&&j.startselected){j.$element.removeClass("ui-selecting");j.selecting=false;j.$element.addClass("ui-selected");j.selected=true}else{j.$element.removeClass("ui-selecting");j.selecting=false;if(j.startselected){j.$element.addClass("ui-unselecting");j.unselecting=true}c._trigger("unselecting",i,{unselecting:j.element})}}if(j.selected){if(!i.metaKey&&!j.startselected){j.$element.removeClass("ui-selected");j.selected=false;j.$element.addClass("ui-unselecting");j.unselecting=true;c._trigger("unselecting",i,{unselecting:j.element})}}}});return false},_mouseStop:function(d){var b=this;this.dragged=false;var c=this.options;a(".ui-unselecting",this.element[0]).each(function(){var e=a.data(this,"selectable-item");e.$element.removeClass("ui-unselecting");e.unselecting=false;e.startselected=false;b._trigger("unselected",d,{unselected:e.element})});a(".ui-selecting",this.element[0]).each(function(){var e=a.data(this,"selectable-item");e.$element.removeClass("ui-selecting").addClass("ui-selected");e.selecting=false;e.selected=true;e.startselected=true;b._trigger("selected",d,{selected:e.element})});this._trigger("stop",d);this.helper.remove();return false}}));a.extend(a.ui.selectable,{version:"1.7.3",defaults:{appendTo:"body",autoRefresh:true,cancel:":input,option",delay:0,distance:0,filter:"*",tolerance:"touch"}})})(jQuery);;/*
 * jQuery UI Datepicker 1.7.3
 *
 * Copyright (c) 2009 AUTHORS.txt (http://jqueryui.com/about)
 * Dual licensed under the MIT (MIT-LICENSE.txt)
 * and GPL (GPL-LICENSE.txt) licenses.
 *
 * http://docs.jquery.com/UI/Datepicker
 *
 * Depends:
 *	ui.core.js
 */
(function($){$.extend($.ui,{datepicker:{version:"1.7.3"}});var PROP_NAME="datepicker";function Datepicker(){this.debug=false;this._curInst=null;this._keyEvent=false;this._disabledInputs=[];this._datepickerShowing=false;this._inDialog=false;this._mainDivId="ui-datepicker-div";this._inlineClass="ui-datepicker-inline";this._appendClass="ui-datepicker-append";this._triggerClass="ui-datepicker-trigger";this._dialogClass="ui-datepicker-dialog";this._disableClass="ui-datepicker-disabled";this._unselectableClass="ui-datepicker-unselectable";this._currentClass="ui-datepicker-current-day";this._dayOverClass="ui-datepicker-days-cell-over";this.regional=[];this.regional[""]={closeText:"Done",prevText:"Prev",nextText:"Next",currentText:"Today",monthNames:["January","February","March","April","May","June","July","August","September","October","November","December"],monthNamesShort:["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],dayNames:["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],dayNamesShort:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],dayNamesMin:["Su","Mo","Tu","We","Th","Fr","Sa"],dateFormat:"mm/dd/yy",firstDay:0,isRTL:false};this._defaults={showOn:"focus",showAnim:"show",showOptions:{},defaultDate:null,appendText:"",buttonText:"...",buttonImage:"",buttonImageOnly:false,hideIfNoPrevNext:false,navigationAsDateFormat:false,gotoCurrent:false,changeMonth:false,changeYear:false,showMonthAfterYear:false,yearRange:"-10:+10",showOtherMonths:false,calculateWeek:this.iso8601Week,shortYearCutoff:"+10",minDate:null,maxDate:null,duration:"normal",beforeShowDay:null,beforeShow:null,onSelect:null,onChangeMonthYear:null,onClose:null,numberOfMonths:1,showCurrentAtPos:0,stepMonths:1,stepBigMonths:12,altField:"",altFormat:"",constrainInput:true,showButtonPanel:false};$.extend(this._defaults,this.regional[""]);this.dpDiv=$('<div id="'+this._mainDivId+'" class="ui-datepicker ui-widget ui-widget-content ui-helper-clearfix ui-corner-all ui-helper-hidden-accessible"></div>')}$.extend(Datepicker.prototype,{markerClassName:"hasDatepicker",log:function(){if(this.debug){console.log.apply("",arguments)}},setDefaults:function(settings){extendRemove(this._defaults,settings||{});return this},_attachDatepicker:function(target,settings){var inlineSettings=null;for(var attrName in this._defaults){var attrValue=target.getAttribute("date:"+attrName);if(attrValue){inlineSettings=inlineSettings||{};try{inlineSettings[attrName]=eval(attrValue)}catch(err){inlineSettings[attrName]=attrValue}}}var nodeName=target.nodeName.toLowerCase();var inline=(nodeName=="div"||nodeName=="span");if(!target.id){target.id="dp"+(++this.uuid)}var inst=this._newInst($(target),inline);inst.settings=$.extend({},settings||{},inlineSettings||{});if(nodeName=="input"){this._connectDatepicker(target,inst)}else{if(inline){this._inlineDatepicker(target,inst)}}},_newInst:function(target,inline){var id=target[0].id.replace(/([:\[\]\.])/g,"\\\\$1");return{id:id,input:target,selectedDay:0,selectedMonth:0,selectedYear:0,drawMonth:0,drawYear:0,inline:inline,dpDiv:(!inline?this.dpDiv:$('<div class="'+this._inlineClass+' ui-datepicker ui-widget ui-widget-content ui-helper-clearfix ui-corner-all"></div>'))}},_connectDatepicker:function(target,inst){var input=$(target);inst.append=$([]);inst.trigger=$([]);if(input.hasClass(this.markerClassName)){return}var appendText=this._get(inst,"appendText");var isRTL=this._get(inst,"isRTL");if(appendText){inst.append=$('<span class="'+this._appendClass+'">'+appendText+"</span>");input[isRTL?"before":"after"](inst.append)}var showOn=this._get(inst,"showOn");if(showOn=="focus"||showOn=="both"){input.focus(this._showDatepicker)}if(showOn=="button"||showOn=="both"){var buttonText=this._get(inst,"buttonText");var buttonImage=this._get(inst,"buttonImage");inst.trigger=$(this._get(inst,"buttonImageOnly")?$("<img/>").addClass(this._triggerClass).attr({src:buttonImage,alt:buttonText,title:buttonText}):$('<button type="button"></button>').addClass(this._triggerClass).html(buttonImage==""?buttonText:$("<img/>").attr({src:buttonImage,alt:buttonText,title:buttonText})));input[isRTL?"before":"after"](inst.trigger);inst.trigger.click(function(){if($.datepicker._datepickerShowing&&$.datepicker._lastInput==target){$.datepicker._hideDatepicker()}else{$.datepicker._showDatepicker(target)}return false})}input.addClass(this.markerClassName).keydown(this._doKeyDown).keypress(this._doKeyPress).bind("setData.datepicker",function(event,key,value){inst.settings[key]=value}).bind("getData.datepicker",function(event,key){return this._get(inst,key)});$.data(target,PROP_NAME,inst)},_inlineDatepicker:function(target,inst){var divSpan=$(target);if(divSpan.hasClass(this.markerClassName)){return}divSpan.addClass(this.markerClassName).append(inst.dpDiv).bind("setData.datepicker",function(event,key,value){inst.settings[key]=value}).bind("getData.datepicker",function(event,key){return this._get(inst,key)});$.data(target,PROP_NAME,inst);this._setDate(inst,this._getDefaultDate(inst));this._updateDatepicker(inst);this._updateAlternate(inst)},_dialogDatepicker:function(input,dateText,onSelect,settings,pos){var inst=this._dialogInst;if(!inst){var id="dp"+(++this.uuid);this._dialogInput=$('<input type="text" id="'+id+'" size="1" style="position: absolute; top: -100px;"/>');this._dialogInput.keydown(this._doKeyDown);$("body").append(this._dialogInput);inst=this._dialogInst=this._newInst(this._dialogInput,false);inst.settings={};$.data(this._dialogInput[0],PROP_NAME,inst)}extendRemove(inst.settings,settings||{});this._dialogInput.val(dateText);this._pos=(pos?(pos.length?pos:[pos.pageX,pos.pageY]):null);if(!this._pos){var browserWidth=window.innerWidth||document.documentElement.clientWidth||document.body.clientWidth;var browserHeight=window.innerHeight||document.documentElement.clientHeight||document.body.clientHeight;var scrollX=document.documentElement.scrollLeft||document.body.scrollLeft;var scrollY=document.documentElement.scrollTop||document.body.scrollTop;this._pos=[(browserWidth/2)-100+scrollX,(browserHeight/2)-150+scrollY]}this._dialogInput.css("left",this._pos[0]+"px").css("top",this._pos[1]+"px");inst.settings.onSelect=onSelect;this._inDialog=true;this.dpDiv.addClass(this._dialogClass);this._showDatepicker(this._dialogInput[0]);if($.blockUI){$.blockUI(this.dpDiv)}$.data(this._dialogInput[0],PROP_NAME,inst);return this},_destroyDatepicker:function(target){var $target=$(target);var inst=$.data(target,PROP_NAME);if(!$target.hasClass(this.markerClassName)){return}var nodeName=target.nodeName.toLowerCase();$.removeData(target,PROP_NAME);if(nodeName=="input"){inst.append.remove();inst.trigger.remove();$target.removeClass(this.markerClassName).unbind("focus",this._showDatepicker).unbind("keydown",this._doKeyDown).unbind("keypress",this._doKeyPress)}else{if(nodeName=="div"||nodeName=="span"){$target.removeClass(this.markerClassName).empty()}}},_enableDatepicker:function(target){var $target=$(target);var inst=$.data(target,PROP_NAME);if(!$target.hasClass(this.markerClassName)){return}var nodeName=target.nodeName.toLowerCase();if(nodeName=="input"){target.disabled=false;inst.trigger.filter("button").each(function(){this.disabled=false}).end().filter("img").css({opacity:"1.0",cursor:""})}else{if(nodeName=="div"||nodeName=="span"){var inline=$target.children("."+this._inlineClass);inline.children().removeClass("ui-state-disabled")}}this._disabledInputs=$.map(this._disabledInputs,function(value){return(value==target?null:value)})},_disableDatepicker:function(target){var $target=$(target);var inst=$.data(target,PROP_NAME);if(!$target.hasClass(this.markerClassName)){return}var nodeName=target.nodeName.toLowerCase();if(nodeName=="input"){target.disabled=true;inst.trigger.filter("button").each(function(){this.disabled=true}).end().filter("img").css({opacity:"0.5",cursor:"default"})}else{if(nodeName=="div"||nodeName=="span"){var inline=$target.children("."+this._inlineClass);inline.children().addClass("ui-state-disabled")}}this._disabledInputs=$.map(this._disabledInputs,function(value){return(value==target?null:value)});this._disabledInputs[this._disabledInputs.length]=target},_isDisabledDatepicker:function(target){if(!target){return false}for(var i=0;i<this._disabledInputs.length;i++){if(this._disabledInputs[i]==target){return true}}return false},_getInst:function(target){try{return $.data(target,PROP_NAME)}catch(err){throw"Missing instance data for this datepicker"}},_optionDatepicker:function(target,name,value){var inst=this._getInst(target);if(arguments.length==2&&typeof name=="string"){return(name=="defaults"?$.extend({},$.datepicker._defaults):(inst?(name=="all"?$.extend({},inst.settings):this._get(inst,name)):null))}var settings=name||{};if(typeof name=="string"){settings={};settings[name]=value}if(inst){if(this._curInst==inst){this._hideDatepicker(null)}var date=this._getDateDatepicker(target);extendRemove(inst.settings,settings);this._setDateDatepicker(target,date);this._updateDatepicker(inst)}},_changeDatepicker:function(target,name,value){this._optionDatepicker(target,name,value)},_refreshDatepicker:function(target){var inst=this._getInst(target);if(inst){this._updateDatepicker(inst)}},_setDateDatepicker:function(target,date,endDate){var inst=this._getInst(target);if(inst){this._setDate(inst,date,endDate);this._updateDatepicker(inst);this._updateAlternate(inst)}},_getDateDatepicker:function(target){var inst=this._getInst(target);if(inst&&!inst.inline){this._setDateFromField(inst)}return(inst?this._getDate(inst):null)},_doKeyDown:function(event){var inst=$.datepicker._getInst(event.target);var handled=true;var isRTL=inst.dpDiv.is(".ui-datepicker-rtl");inst._keyEvent=true;if($.datepicker._datepickerShowing){switch(event.keyCode){case 9:$.datepicker._hideDatepicker(null,"");break;case 13:var sel=$("td."+$.datepicker._dayOverClass+", td."+$.datepicker._currentClass,inst.dpDiv);if(sel[0]){$.datepicker._selectDay(event.target,inst.selectedMonth,inst.selectedYear,sel[0])}else{$.datepicker._hideDatepicker(null,$.datepicker._get(inst,"duration"))}return false;break;case 27:$.datepicker._hideDatepicker(null,$.datepicker._get(inst,"duration"));break;case 33:$.datepicker._adjustDate(event.target,(event.ctrlKey?-$.datepicker._get(inst,"stepBigMonths"):-$.datepicker._get(inst,"stepMonths")),"M");break;case 34:$.datepicker._adjustDate(event.target,(event.ctrlKey?+$.datepicker._get(inst,"stepBigMonths"):+$.datepicker._get(inst,"stepMonths")),"M");break;case 35:if(event.ctrlKey||event.metaKey){$.datepicker._clearDate(event.target)}handled=event.ctrlKey||event.metaKey;break;case 36:if(event.ctrlKey||event.metaKey){$.datepicker._gotoToday(event.target)}handled=event.ctrlKey||event.metaKey;break;case 37:if(event.ctrlKey||event.metaKey){$.datepicker._adjustDate(event.target,(isRTL?+1:-1),"D")}handled=event.ctrlKey||event.metaKey;if(event.originalEvent.altKey){$.datepicker._adjustDate(event.target,(event.ctrlKey?-$.datepicker._get(inst,"stepBigMonths"):-$.datepicker._get(inst,"stepMonths")),"M")}break;case 38:if(event.ctrlKey||event.metaKey){$.datepicker._adjustDate(event.target,-7,"D")}handled=event.ctrlKey||event.metaKey;break;case 39:if(event.ctrlKey||event.metaKey){$.datepicker._adjustDate(event.target,(isRTL?-1:+1),"D")}handled=event.ctrlKey||event.metaKey;if(event.originalEvent.altKey){$.datepicker._adjustDate(event.target,(event.ctrlKey?+$.datepicker._get(inst,"stepBigMonths"):+$.datepicker._get(inst,"stepMonths")),"M")}break;case 40:if(event.ctrlKey||event.metaKey){$.datepicker._adjustDate(event.target,+7,"D")}handled=event.ctrlKey||event.metaKey;break;default:handled=false}}else{if(event.keyCode==36&&event.ctrlKey){$.datepicker._showDatepicker(this)}else{handled=false}}if(handled){event.preventDefault();event.stopPropagation()}},_doKeyPress:function(event){var inst=$.datepicker._getInst(event.target);if($.datepicker._get(inst,"constrainInput")){var chars=$.datepicker._possibleChars($.datepicker._get(inst,"dateFormat"));var chr=String.fromCharCode(event.charCode==undefined?event.keyCode:event.charCode);return event.ctrlKey||(chr<" "||!chars||chars.indexOf(chr)>-1)}},_showDatepicker:function(input){input=input.target||input;if(input.nodeName.toLowerCase()!="input"){input=$("input",input.parentNode)[0]}if($.datepicker._isDisabledDatepicker(input)||$.datepicker._lastInput==input){return}var inst=$.datepicker._getInst(input);var beforeShow=$.datepicker._get(inst,"beforeShow");extendRemove(inst.settings,(beforeShow?beforeShow.apply(input,[input,inst]):{}));$.datepicker._hideDatepicker(null,"");$.datepicker._lastInput=input;$.datepicker._setDateFromField(inst);if($.datepicker._inDialog){input.value=""}if(!$.datepicker._pos){$.datepicker._pos=$.datepicker._findPos(input);$.datepicker._pos[1]+=input.offsetHeight}var isFixed=false;$(input).parents().each(function(){isFixed|=$(this).css("position")=="fixed";return !isFixed});if(isFixed&&$.browser.opera){$.datepicker._pos[0]-=document.documentElement.scrollLeft;$.datepicker._pos[1]-=document.documentElement.scrollTop}var offset={left:$.datepicker._pos[0],top:$.datepicker._pos[1]};$.datepicker._pos=null;inst.rangeStart=null;inst.dpDiv.css({position:"absolute",display:"block",top:"-1000px"});$.datepicker._updateDatepicker(inst);offset=$.datepicker._checkOffset(inst,offset,isFixed);inst.dpDiv.css({position:($.datepicker._inDialog&&$.blockUI?"static":(isFixed?"fixed":"absolute")),display:"none",left:offset.left+"px",top:offset.top+"px"});if(!inst.inline){var showAnim=$.datepicker._get(inst,"showAnim")||"show";var duration=$.datepicker._get(inst,"duration");var postProcess=function(){$.datepicker._datepickerShowing=true;if($.browser.msie&&parseInt($.browser.version,10)<7){$("iframe.ui-datepicker-cover").css({width:inst.dpDiv.width()+4,height:inst.dpDiv.height()+4})}};if($.effects&&$.effects[showAnim]){inst.dpDiv.show(showAnim,$.datepicker._get(inst,"showOptions"),duration,postProcess)}else{inst.dpDiv[showAnim](duration,postProcess)}if(duration==""){postProcess()}if(inst.input[0].type!="hidden"){inst.input[0].focus()}$.datepicker._curInst=inst}},_updateDatepicker:function(inst){var dims={width:inst.dpDiv.width()+4,height:inst.dpDiv.height()+4};var self=this;inst.dpDiv.empty().append(this._generateHTML(inst)).find("iframe.ui-datepicker-cover").css({width:dims.width,height:dims.height}).end().find("button, .ui-datepicker-prev, .ui-datepicker-next, .ui-datepicker-calendar td a").bind("mouseout",function(){$(this).removeClass("ui-state-hover");if(this.className.indexOf("ui-datepicker-prev")!=-1){$(this).removeClass("ui-datepicker-prev-hover")}if(this.className.indexOf("ui-datepicker-next")!=-1){$(this).removeClass("ui-datepicker-next-hover")}}).bind("mouseover",function(){if(!self._isDisabledDatepicker(inst.inline?inst.dpDiv.parent()[0]:inst.input[0])){$(this).parents(".ui-datepicker-calendar").find("a").removeClass("ui-state-hover");$(this).addClass("ui-state-hover");if(this.className.indexOf("ui-datepicker-prev")!=-1){$(this).addClass("ui-datepicker-prev-hover")}if(this.className.indexOf("ui-datepicker-next")!=-1){$(this).addClass("ui-datepicker-next-hover")}}}).end().find("."+this._dayOverClass+" a").trigger("mouseover").end();var numMonths=this._getNumberOfMonths(inst);var cols=numMonths[1];var width=17;if(cols>1){inst.dpDiv.addClass("ui-datepicker-multi-"+cols).css("width",(width*cols)+"em")}else{inst.dpDiv.removeClass("ui-datepicker-multi-2 ui-datepicker-multi-3 ui-datepicker-multi-4").width("")}inst.dpDiv[(numMonths[0]!=1||numMonths[1]!=1?"add":"remove")+"Class"]("ui-datepicker-multi");inst.dpDiv[(this._get(inst,"isRTL")?"add":"remove")+"Class"]("ui-datepicker-rtl");if(inst.input&&inst.input[0].type!="hidden"&&inst==$.datepicker._curInst){$(inst.input[0]).focus()}},_checkOffset:function(inst,offset,isFixed){var dpWidth=inst.dpDiv.outerWidth();var dpHeight=inst.dpDiv.outerHeight();var inputWidth=inst.input?inst.input.outerWidth():0;var inputHeight=inst.input?inst.input.outerHeight():0;var viewWidth=(window.innerWidth||document.documentElement.clientWidth||document.body.clientWidth)+$(document).scrollLeft();var viewHeight=(window.innerHeight||document.documentElement.clientHeight||document.body.clientHeight)+$(document).scrollTop();offset.left-=(this._get(inst,"isRTL")?(dpWidth-inputWidth):0);offset.left-=(isFixed&&offset.left==inst.input.offset().left)?$(document).scrollLeft():0;offset.top-=(isFixed&&offset.top==(inst.input.offset().top+inputHeight))?$(document).scrollTop():0;offset.left-=(offset.left+dpWidth>viewWidth&&viewWidth>dpWidth)?Math.abs(offset.left+dpWidth-viewWidth):0;offset.top-=(offset.top+dpHeight>viewHeight&&viewHeight>dpHeight)?Math.abs(offset.top+dpHeight+inputHeight*2-viewHeight):0;return offset},_findPos:function(obj){while(obj&&(obj.type=="hidden"||obj.nodeType!=1)){obj=obj.nextSibling}var position=$(obj).offset();return[position.left,position.top]},_hideDatepicker:function(input,duration){var inst=this._curInst;if(!inst||(input&&inst!=$.data(input,PROP_NAME))){return}if(inst.stayOpen){this._selectDate("#"+inst.id,this._formatDate(inst,inst.currentDay,inst.currentMonth,inst.currentYear))}inst.stayOpen=false;if(this._datepickerShowing){duration=(duration!=null?duration:this._get(inst,"duration"));var showAnim=this._get(inst,"showAnim");var postProcess=function(){$.datepicker._tidyDialog(inst)};if(duration!=""&&$.effects&&$.effects[showAnim]){inst.dpDiv.hide(showAnim,$.datepicker._get(inst,"showOptions"),duration,postProcess)}else{inst.dpDiv[(duration==""?"hide":(showAnim=="slideDown"?"slideUp":(showAnim=="fadeIn"?"fadeOut":"hide")))](duration,postProcess)}if(duration==""){this._tidyDialog(inst)}var onClose=this._get(inst,"onClose");if(onClose){onClose.apply((inst.input?inst.input[0]:null),[(inst.input?inst.input.val():""),inst])}this._datepickerShowing=false;this._lastInput=null;if(this._inDialog){this._dialogInput.css({position:"absolute",left:"0",top:"-100px"});if($.blockUI){$.unblockUI();$("body").append(this.dpDiv)}}this._inDialog=false}this._curInst=null},_tidyDialog:function(inst){inst.dpDiv.removeClass(this._dialogClass).unbind(".ui-datepicker-calendar")},_checkExternalClick:function(event){if(!$.datepicker._curInst){return}var $target=$(event.target);if(($target.parents("#"+$.datepicker._mainDivId).length==0)&&!$target.hasClass($.datepicker.markerClassName)&&!$target.hasClass($.datepicker._triggerClass)&&$.datepicker._datepickerShowing&&!($.datepicker._inDialog&&$.blockUI)){$.datepicker._hideDatepicker(null,"")}},_adjustDate:function(id,offset,period){var target=$(id);var inst=this._getInst(target[0]);if(this._isDisabledDatepicker(target[0])){return}this._adjustInstDate(inst,offset+(period=="M"?this._get(inst,"showCurrentAtPos"):0),period);this._updateDatepicker(inst)},_gotoToday:function(id){var target=$(id);var inst=this._getInst(target[0]);if(this._get(inst,"gotoCurrent")&&inst.currentDay){inst.selectedDay=inst.currentDay;inst.drawMonth=inst.selectedMonth=inst.currentMonth;inst.drawYear=inst.selectedYear=inst.currentYear}else{var date=new Date();inst.selectedDay=date.getDate();inst.drawMonth=inst.selectedMonth=date.getMonth();inst.drawYear=inst.selectedYear=date.getFullYear()}this._notifyChange(inst);this._adjustDate(target)},_selectMonthYear:function(id,select,period){var target=$(id);var inst=this._getInst(target[0]);inst._selectingMonthYear=false;inst["selected"+(period=="M"?"Month":"Year")]=inst["draw"+(period=="M"?"Month":"Year")]=parseInt(select.options[select.selectedIndex].value,10);this._notifyChange(inst);this._adjustDate(target)},_clickMonthYear:function(id){var target=$(id);var inst=this._getInst(target[0]);if(inst.input&&inst._selectingMonthYear&&!$.browser.msie){inst.input[0].focus()}inst._selectingMonthYear=!inst._selectingMonthYear},_selectDay:function(id,month,year,td){var target=$(id);if($(td).hasClass(this._unselectableClass)||this._isDisabledDatepicker(target[0])){return}var inst=this._getInst(target[0]);inst.selectedDay=inst.currentDay=$("a",td).html();inst.selectedMonth=inst.currentMonth=month;inst.selectedYear=inst.currentYear=year;if(inst.stayOpen){inst.endDay=inst.endMonth=inst.endYear=null}this._selectDate(id,this._formatDate(inst,inst.currentDay,inst.currentMonth,inst.currentYear));if(inst.stayOpen){inst.rangeStart=this._daylightSavingAdjust(new Date(inst.currentYear,inst.currentMonth,inst.currentDay));this._updateDatepicker(inst)}},_clearDate:function(id){var target=$(id);var inst=this._getInst(target[0]);inst.stayOpen=false;inst.endDay=inst.endMonth=inst.endYear=inst.rangeStart=null;this._selectDate(target,"")},_selectDate:function(id,dateStr){var target=$(id);var inst=this._getInst(target[0]);dateStr=(dateStr!=null?dateStr:this._formatDate(inst));if(inst.input){inst.input.val(dateStr)}this._updateAlternate(inst);var onSelect=this._get(inst,"onSelect");if(onSelect){onSelect.apply((inst.input?inst.input[0]:null),[dateStr,inst])}else{if(inst.input){inst.input.trigger("change")}}if(inst.inline){this._updateDatepicker(inst)}else{if(!inst.stayOpen){this._hideDatepicker(null,this._get(inst,"duration"));this._lastInput=inst.input[0];if(typeof(inst.input[0])!="object"){inst.input[0].focus()}this._lastInput=null}}},_updateAlternate:function(inst){var altField=this._get(inst,"altField");if(altField){var altFormat=this._get(inst,"altFormat")||this._get(inst,"dateFormat");var date=this._getDate(inst);dateStr=this.formatDate(altFormat,date,this._getFormatConfig(inst));$(altField).each(function(){$(this).val(dateStr)})}},noWeekends:function(date){var day=date.getDay();return[(day>0&&day<6),""]},iso8601Week:function(date){var checkDate=new Date(date.getFullYear(),date.getMonth(),date.getDate());var firstMon=new Date(checkDate.getFullYear(),1-1,4);var firstDay=firstMon.getDay()||7;firstMon.setDate(firstMon.getDate()+1-firstDay);if(firstDay<4&&checkDate<firstMon){checkDate.setDate(checkDate.getDate()-3);return $.datepicker.iso8601Week(checkDate)}else{if(checkDate>new Date(checkDate.getFullYear(),12-1,28)){firstDay=new Date(checkDate.getFullYear()+1,1-1,4).getDay()||7;if(firstDay>4&&(checkDate.getDay()||7)<firstDay-3){return 1}}}return Math.floor(((checkDate-firstMon)/86400000)/7)+1},parseDate:function(format,value,settings){if(format==null||value==null){throw"Invalid arguments"}value=(typeof value=="object"?value.toString():value+"");if(value==""){return null}var shortYearCutoff=(settings?settings.shortYearCutoff:null)||this._defaults.shortYearCutoff;var dayNamesShort=(settings?settings.dayNamesShort:null)||this._defaults.dayNamesShort;var dayNames=(settings?settings.dayNames:null)||this._defaults.dayNames;var monthNamesShort=(settings?settings.monthNamesShort:null)||this._defaults.monthNamesShort;var monthNames=(settings?settings.monthNames:null)||this._defaults.monthNames;var year=-1;var month=-1;var day=-1;var doy=-1;var literal=false;var lookAhead=function(match){var matches=(iFormat+1<format.length&&format.charAt(iFormat+1)==match);if(matches){iFormat++}return matches};var getNumber=function(match){lookAhead(match);var origSize=(match=="@"?14:(match=="y"?4:(match=="o"?3:2)));var size=origSize;var num=0;while(size>0&&iValue<value.length&&value.charAt(iValue)>="0"&&value.charAt(iValue)<="9"){num=num*10+parseInt(value.charAt(iValue++),10);size--}if(size==origSize){throw"Missing number at position "+iValue}return num};var getName=function(match,shortNames,longNames){var names=(lookAhead(match)?longNames:shortNames);var size=0;for(var j=0;j<names.length;j++){size=Math.max(size,names[j].length)}var name="";var iInit=iValue;while(size>0&&iValue<value.length){name+=value.charAt(iValue++);for(var i=0;i<names.length;i++){if(name==names[i]){return i+1}}size--}throw"Unknown name at position "+iInit};var checkLiteral=function(){if(value.charAt(iValue)!=format.charAt(iFormat)){throw"Unexpected literal at position "+iValue}iValue++};var iValue=0;for(var iFormat=0;iFormat<format.length;iFormat++){if(literal){if(format.charAt(iFormat)=="'"&&!lookAhead("'")){literal=false}else{checkLiteral()}}else{switch(format.charAt(iFormat)){case"d":day=getNumber("d");break;case"D":getName("D",dayNamesShort,dayNames);break;case"o":doy=getNumber("o");break;case"m":month=getNumber("m");break;case"M":month=getName("M",monthNamesShort,monthNames);break;case"y":year=getNumber("y");break;case"@":var date=new Date(getNumber("@"));year=date.getFullYear();month=date.getMonth()+1;day=date.getDate();break;case"'":if(lookAhead("'")){checkLiteral()}else{literal=true}break;default:checkLiteral()}}}if(year==-1){year=new Date().getFullYear()}else{if(year<100){year+=new Date().getFullYear()-new Date().getFullYear()%100+(year<=shortYearCutoff?0:-100)}}if(doy>-1){month=1;day=doy;do{var dim=this._getDaysInMonth(year,month-1);if(day<=dim){break}month++;day-=dim}while(true)}var date=this._daylightSavingAdjust(new Date(year,month-1,day));if(date.getFullYear()!=year||date.getMonth()+1!=month||date.getDate()!=day){throw"Invalid date"}return date},ATOM:"yy-mm-dd",COOKIE:"D, dd M yy",ISO_8601:"yy-mm-dd",RFC_822:"D, d M y",RFC_850:"DD, dd-M-y",RFC_1036:"D, d M y",RFC_1123:"D, d M yy",RFC_2822:"D, d M yy",RSS:"D, d M y",TIMESTAMP:"@",W3C:"yy-mm-dd",formatDate:function(format,date,settings){if(!date){return""}var dayNamesShort=(settings?settings.dayNamesShort:null)||this._defaults.dayNamesShort;var dayNames=(settings?settings.dayNames:null)||this._defaults.dayNames;var monthNamesShort=(settings?settings.monthNamesShort:null)||this._defaults.monthNamesShort;var monthNames=(settings?settings.monthNames:null)||this._defaults.monthNames;var lookAhead=function(match){var matches=(iFormat+1<format.length&&format.charAt(iFormat+1)==match);if(matches){iFormat++}return matches};var formatNumber=function(match,value,len){var num=""+value;if(lookAhead(match)){while(num.length<len){num="0"+num}}return num};var formatName=function(match,value,shortNames,longNames){return(lookAhead(match)?longNames[value]:shortNames[value])};var output="";var literal=false;if(date){for(var iFormat=0;iFormat<format.length;iFormat++){if(literal){if(format.charAt(iFormat)=="'"&&!lookAhead("'")){literal=false}else{output+=format.charAt(iFormat)}}else{switch(format.charAt(iFormat)){case"d":output+=formatNumber("d",date.getDate(),2);break;case"D":output+=formatName("D",date.getDay(),dayNamesShort,dayNames);break;case"o":var doy=date.getDate();for(var m=date.getMonth()-1;m>=0;m--){doy+=this._getDaysInMonth(date.getFullYear(),m)}output+=formatNumber("o",doy,3);break;case"m":output+=formatNumber("m",date.getMonth()+1,2);break;case"M":output+=formatName("M",date.getMonth(),monthNamesShort,monthNames);break;case"y":output+=(lookAhead("y")?date.getFullYear():(date.getYear()%100<10?"0":"")+date.getYear()%100);break;case"@":output+=date.getTime();break;case"'":if(lookAhead("'")){output+="'"}else{literal=true}break;default:output+=format.charAt(iFormat)}}}}return output},_possibleChars:function(format){var chars="";var literal=false;for(var iFormat=0;iFormat<format.length;iFormat++){if(literal){if(format.charAt(iFormat)=="'"&&!lookAhead("'")){literal=false}else{chars+=format.charAt(iFormat)}}else{switch(format.charAt(iFormat)){case"d":case"m":case"y":case"@":chars+="0123456789";break;case"D":case"M":return null;case"'":if(lookAhead("'")){chars+="'"}else{literal=true}break;default:chars+=format.charAt(iFormat)}}}return chars},_get:function(inst,name){return inst.settings[name]!==undefined?inst.settings[name]:this._defaults[name]},_setDateFromField:function(inst){var dateFormat=this._get(inst,"dateFormat");var dates=inst.input?inst.input.val():null;inst.endDay=inst.endMonth=inst.endYear=null;var date=defaultDate=this._getDefaultDate(inst);var settings=this._getFormatConfig(inst);try{date=this.parseDate(dateFormat,dates,settings)||defaultDate}catch(event){this.log(event);date=defaultDate}inst.selectedDay=date.getDate();inst.drawMonth=inst.selectedMonth=date.getMonth();inst.drawYear=inst.selectedYear=date.getFullYear();inst.currentDay=(dates?date.getDate():0);inst.currentMonth=(dates?date.getMonth():0);inst.currentYear=(dates?date.getFullYear():0);this._adjustInstDate(inst)},_getDefaultDate:function(inst){var date=this._determineDate(this._get(inst,"defaultDate"),new Date());var minDate=this._getMinMaxDate(inst,"min",true);var maxDate=this._getMinMaxDate(inst,"max");date=(minDate&&date<minDate?minDate:date);date=(maxDate&&date>maxDate?maxDate:date);return date},_determineDate:function(date,defaultDate){var offsetNumeric=function(offset){var date=new Date();date.setDate(date.getDate()+offset);return date};var offsetString=function(offset,getDaysInMonth){var date=new Date();var year=date.getFullYear();var month=date.getMonth();var day=date.getDate();var pattern=/([+-]?[0-9]+)\s*(d|D|w|W|m|M|y|Y)?/g;var matches=pattern.exec(offset);while(matches){switch(matches[2]||"d"){case"d":case"D":day+=parseInt(matches[1],10);break;case"w":case"W":day+=parseInt(matches[1],10)*7;break;case"m":case"M":month+=parseInt(matches[1],10);day=Math.min(day,getDaysInMonth(year,month));break;case"y":case"Y":year+=parseInt(matches[1],10);day=Math.min(day,getDaysInMonth(year,month));break}matches=pattern.exec(offset)}return new Date(year,month,day)};date=(date==null?defaultDate:(typeof date=="string"?offsetString(date,this._getDaysInMonth):(typeof date=="number"?(isNaN(date)?defaultDate:offsetNumeric(date)):date)));date=(date&&date.toString()=="Invalid Date"?defaultDate:date);if(date){date.setHours(0);date.setMinutes(0);date.setSeconds(0);date.setMilliseconds(0)}return this._daylightSavingAdjust(date)},_daylightSavingAdjust:function(date){if(!date){return null}date.setHours(date.getHours()>12?date.getHours()+2:0);return date},_setDate:function(inst,date,endDate){var clear=!(date);var origMonth=inst.selectedMonth;var origYear=inst.selectedYear;date=this._determineDate(date,new Date());inst.selectedDay=inst.currentDay=date.getDate();inst.drawMonth=inst.selectedMonth=inst.currentMonth=date.getMonth();inst.drawYear=inst.selectedYear=inst.currentYear=date.getFullYear();if(origMonth!=inst.selectedMonth||origYear!=inst.selectedYear){this._notifyChange(inst)}this._adjustInstDate(inst);if(inst.input){inst.input.val(clear?"":this._formatDate(inst))}},_getDate:function(inst){var startDate=(!inst.currentYear||(inst.input&&inst.input.val()=="")?null:this._daylightSavingAdjust(new Date(inst.currentYear,inst.currentMonth,inst.currentDay)));return startDate},_generateHTML:function(inst){var today=new Date();today=this._daylightSavingAdjust(new Date(today.getFullYear(),today.getMonth(),today.getDate()));var isRTL=this._get(inst,"isRTL");var showButtonPanel=this._get(inst,"showButtonPanel");var hideIfNoPrevNext=this._get(inst,"hideIfNoPrevNext");var navigationAsDateFormat=this._get(inst,"navigationAsDateFormat");var numMonths=this._getNumberOfMonths(inst);var showCurrentAtPos=this._get(inst,"showCurrentAtPos");var stepMonths=this._get(inst,"stepMonths");var stepBigMonths=this._get(inst,"stepBigMonths");var isMultiMonth=(numMonths[0]!=1||numMonths[1]!=1);var currentDate=this._daylightSavingAdjust((!inst.currentDay?new Date(9999,9,9):new Date(inst.currentYear,inst.currentMonth,inst.currentDay)));var minDate=this._getMinMaxDate(inst,"min",true);var maxDate=this._getMinMaxDate(inst,"max");var drawMonth=inst.drawMonth-showCurrentAtPos;var drawYear=inst.drawYear;if(drawMonth<0){drawMonth+=12;drawYear--}if(maxDate){var maxDraw=this._daylightSavingAdjust(new Date(maxDate.getFullYear(),maxDate.getMonth()-numMonths[1]+1,maxDate.getDate()));maxDraw=(minDate&&maxDraw<minDate?minDate:maxDraw);while(this._daylightSavingAdjust(new Date(drawYear,drawMonth,1))>maxDraw){drawMonth--;if(drawMonth<0){drawMonth=11;drawYear--}}}inst.drawMonth=drawMonth;inst.drawYear=drawYear;var prevText=this._get(inst,"prevText");prevText=(!navigationAsDateFormat?prevText:this.formatDate(prevText,this._daylightSavingAdjust(new Date(drawYear,drawMonth-stepMonths,1)),this._getFormatConfig(inst)));var prev=(this._canAdjustMonth(inst,-1,drawYear,drawMonth)?'<a class="ui-datepicker-prev ui-corner-all" onclick="DP_jQuery.datepicker._adjustDate(\'#'+inst.id+"', -"+stepMonths+", 'M');\" title=\""+prevText+'"><span class="ui-icon ui-icon-circle-triangle-'+(isRTL?"e":"w")+'">'+prevText+"</span></a>":(hideIfNoPrevNext?"":'<a class="ui-datepicker-prev ui-corner-all ui-state-disabled" title="'+prevText+'"><span class="ui-icon ui-icon-circle-triangle-'+(isRTL?"e":"w")+'">'+prevText+"</span></a>"));var nextText=this._get(inst,"nextText");nextText=(!navigationAsDateFormat?nextText:this.formatDate(nextText,this._daylightSavingAdjust(new Date(drawYear,drawMonth+stepMonths,1)),this._getFormatConfig(inst)));var next=(this._canAdjustMonth(inst,+1,drawYear,drawMonth)?'<a class="ui-datepicker-next ui-corner-all" onclick="DP_jQuery.datepicker._adjustDate(\'#'+inst.id+"', +"+stepMonths+", 'M');\" title=\""+nextText+'"><span class="ui-icon ui-icon-circle-triangle-'+(isRTL?"w":"e")+'">'+nextText+"</span></a>":(hideIfNoPrevNext?"":'<a class="ui-datepicker-next ui-corner-all ui-state-disabled" title="'+nextText+'"><span class="ui-icon ui-icon-circle-triangle-'+(isRTL?"w":"e")+'">'+nextText+"</span></a>"));var currentText=this._get(inst,"currentText");var gotoDate=(this._get(inst,"gotoCurrent")&&inst.currentDay?currentDate:today);currentText=(!navigationAsDateFormat?currentText:this.formatDate(currentText,gotoDate,this._getFormatConfig(inst)));var controls=(!inst.inline?'<button type="button" class="ui-datepicker-close ui-state-default ui-priority-primary ui-corner-all" onclick="DP_jQuery.datepicker._hideDatepicker();">'+this._get(inst,"closeText")+"</button>":"");var buttonPanel=(showButtonPanel)?'<div class="ui-datepicker-buttonpane ui-widget-content">'+(isRTL?controls:"")+(this._isInRange(inst,gotoDate)?'<button type="button" class="ui-datepicker-current ui-state-default ui-priority-secondary ui-corner-all" onclick="DP_jQuery.datepicker._gotoToday(\'#'+inst.id+"');\">"+currentText+"</button>":"")+(isRTL?"":controls)+"</div>":"";var firstDay=parseInt(this._get(inst,"firstDay"),10);firstDay=(isNaN(firstDay)?0:firstDay);var dayNames=this._get(inst,"dayNames");var dayNamesShort=this._get(inst,"dayNamesShort");var dayNamesMin=this._get(inst,"dayNamesMin");var monthNames=this._get(inst,"monthNames");var monthNamesShort=this._get(inst,"monthNamesShort");var beforeShowDay=this._get(inst,"beforeShowDay");var showOtherMonths=this._get(inst,"showOtherMonths");var calculateWeek=this._get(inst,"calculateWeek")||this.iso8601Week;var endDate=inst.endDay?this._daylightSavingAdjust(new Date(inst.endYear,inst.endMonth,inst.endDay)):currentDate;var defaultDate=this._getDefaultDate(inst);var html="";for(var row=0;row<numMonths[0];row++){var group="";for(var col=0;col<numMonths[1];col++){var selectedDate=this._daylightSavingAdjust(new Date(drawYear,drawMonth,inst.selectedDay));var cornerClass=" ui-corner-all";var calender="";if(isMultiMonth){calender+='<div class="ui-datepicker-group ui-datepicker-group-';switch(col){case 0:calender+="first";cornerClass=" ui-corner-"+(isRTL?"right":"left");break;case numMonths[1]-1:calender+="last";cornerClass=" ui-corner-"+(isRTL?"left":"right");break;default:calender+="middle";cornerClass="";break}calender+='">'}calender+='<div class="ui-datepicker-header ui-widget-header ui-helper-clearfix'+cornerClass+'">'+(/all|left/.test(cornerClass)&&row==0?(isRTL?next:prev):"")+(/all|right/.test(cornerClass)&&row==0?(isRTL?prev:next):"")+this._generateMonthYearHeader(inst,drawMonth,drawYear,minDate,maxDate,selectedDate,row>0||col>0,monthNames,monthNamesShort)+'</div><table class="ui-datepicker-calendar"><thead><tr>';var thead="";for(var dow=0;dow<7;dow++){var day=(dow+firstDay)%7;thead+="<th"+((dow+firstDay+6)%7>=5?' class="ui-datepicker-week-end"':"")+'><span title="'+dayNames[day]+'">'+dayNamesMin[day]+"</span></th>"}calender+=thead+"</tr></thead><tbody>";var daysInMonth=this._getDaysInMonth(drawYear,drawMonth);if(drawYear==inst.selectedYear&&drawMonth==inst.selectedMonth){inst.selectedDay=Math.min(inst.selectedDay,daysInMonth)}var leadDays=(this._getFirstDayOfMonth(drawYear,drawMonth)-firstDay+7)%7;var numRows=(isMultiMonth?6:Math.ceil((leadDays+daysInMonth)/7));var printDate=this._daylightSavingAdjust(new Date(drawYear,drawMonth,1-leadDays));for(var dRow=0;dRow<numRows;dRow++){calender+="<tr>";var tbody="";for(var dow=0;dow<7;dow++){var daySettings=(beforeShowDay?beforeShowDay.apply((inst.input?inst.input[0]:null),[printDate]):[true,""]);var otherMonth=(printDate.getMonth()!=drawMonth);var unselectable=otherMonth||!daySettings[0]||(minDate&&printDate<minDate)||(maxDate&&printDate>maxDate);tbody+='<td class="'+((dow+firstDay+6)%7>=5?" ui-datepicker-week-end":"")+(otherMonth?" ui-datepicker-other-month":"")+((printDate.getTime()==selectedDate.getTime()&&drawMonth==inst.selectedMonth&&inst._keyEvent)||(defaultDate.getTime()==printDate.getTime()&&defaultDate.getTime()==selectedDate.getTime())?" "+this._dayOverClass:"")+(unselectable?" "+this._unselectableClass+" ui-state-disabled":"")+(otherMonth&&!showOtherMonths?"":" "+daySettings[1]+(printDate.getTime()>=currentDate.getTime()&&printDate.getTime()<=endDate.getTime()?" "+this._currentClass:"")+(printDate.getTime()==today.getTime()?" ui-datepicker-today":""))+'"'+((!otherMonth||showOtherMonths)&&daySettings[2]?' title="'+daySettings[2]+'"':"")+(unselectable?"":" onclick=\"DP_jQuery.datepicker._selectDay('#"+inst.id+"',"+drawMonth+","+drawYear+', this);return false;"')+">"+(otherMonth?(showOtherMonths?printDate.getDate():"&#xa0;"):(unselectable?'<span class="ui-state-default">'+printDate.getDate()+"</span>":'<a class="ui-state-default'+(printDate.getTime()==today.getTime()?" ui-state-highlight":"")+(printDate.getTime()>=currentDate.getTime()&&printDate.getTime()<=endDate.getTime()?" ui-state-active":"")+'" href="#">'+printDate.getDate()+"</a>"))+"</td>";printDate.setDate(printDate.getDate()+1);printDate=this._daylightSavingAdjust(printDate)}calender+=tbody+"</tr>"}drawMonth++;if(drawMonth>11){drawMonth=0;drawYear++}calender+="</tbody></table>"+(isMultiMonth?"</div>"+((numMonths[0]>0&&col==numMonths[1]-1)?'<div class="ui-datepicker-row-break"></div>':""):"");group+=calender}html+=group}html+=buttonPanel+($.browser.msie&&parseInt($.browser.version,10)<7&&!inst.inline?'<iframe src="javascript:false;" class="ui-datepicker-cover" frameborder="0"></iframe>':"");inst._keyEvent=false;return html},_generateMonthYearHeader:function(inst,drawMonth,drawYear,minDate,maxDate,selectedDate,secondary,monthNames,monthNamesShort){minDate=(inst.rangeStart&&minDate&&selectedDate<minDate?selectedDate:minDate);var changeMonth=this._get(inst,"changeMonth");var changeYear=this._get(inst,"changeYear");var showMonthAfterYear=this._get(inst,"showMonthAfterYear");var html='<div class="ui-datepicker-title">';var monthHtml="";if(secondary||!changeMonth){monthHtml+='<span class="ui-datepicker-month">'+monthNames[drawMonth]+"</span> "}else{var inMinYear=(minDate&&minDate.getFullYear()==drawYear);var inMaxYear=(maxDate&&maxDate.getFullYear()==drawYear);monthHtml+='<select class="ui-datepicker-month" onchange="DP_jQuery.datepicker._selectMonthYear(\'#'+inst.id+"', this, 'M');\" onclick=\"DP_jQuery.datepicker._clickMonthYear('#"+inst.id+"');\">";for(var month=0;month<12;month++){if((!inMinYear||month>=minDate.getMonth())&&(!inMaxYear||month<=maxDate.getMonth())){monthHtml+='<option value="'+month+'"'+(month==drawMonth?' selected="selected"':"")+">"+monthNamesShort[month]+"</option>"}}monthHtml+="</select>"}if(!showMonthAfterYear){html+=monthHtml+((secondary||changeMonth||changeYear)&&(!(changeMonth&&changeYear))?"&#xa0;":"")}if(secondary||!changeYear){html+='<span class="ui-datepicker-year">'+drawYear+"</span>"}else{var years=this._get(inst,"yearRange").split(":");var year=0;var endYear=0;if(years.length!=2){year=drawYear-10;endYear=drawYear+10}else{if(years[0].charAt(0)=="+"||years[0].charAt(0)=="-"){year=drawYear+parseInt(years[0],10);endYear=drawYear+parseInt(years[1],10)}else{year=parseInt(years[0],10);endYear=parseInt(years[1],10)}}year=(minDate?Math.max(year,minDate.getFullYear()):year);endYear=(maxDate?Math.min(endYear,maxDate.getFullYear()):endYear);html+='<select class="ui-datepicker-year" onchange="DP_jQuery.datepicker._selectMonthYear(\'#'+inst.id+"', this, 'Y');\" onclick=\"DP_jQuery.datepicker._clickMonthYear('#"+inst.id+"');\">";for(;year<=endYear;year++){html+='<option value="'+year+'"'+(year==drawYear?' selected="selected"':"")+">"+year+"</option>"}html+="</select>"}if(showMonthAfterYear){html+=(secondary||changeMonth||changeYear?"&#xa0;":"")+monthHtml}html+="</div>";return html},_adjustInstDate:function(inst,offset,period){var year=inst.drawYear+(period=="Y"?offset:0);var month=inst.drawMonth+(period=="M"?offset:0);var day=Math.min(inst.selectedDay,this._getDaysInMonth(year,month))+(period=="D"?offset:0);var date=this._daylightSavingAdjust(new Date(year,month,day));var minDate=this._getMinMaxDate(inst,"min",true);var maxDate=this._getMinMaxDate(inst,"max");date=(minDate&&date<minDate?minDate:date);date=(maxDate&&date>maxDate?maxDate:date);inst.selectedDay=date.getDate();inst.drawMonth=inst.selectedMonth=date.getMonth();inst.drawYear=inst.selectedYear=date.getFullYear();if(period=="M"||period=="Y"){this._notifyChange(inst)}},_notifyChange:function(inst){var onChange=this._get(inst,"onChangeMonthYear");if(onChange){onChange.apply((inst.input?inst.input[0]:null),[inst.selectedYear,inst.selectedMonth+1,inst])}},_getNumberOfMonths:function(inst){var numMonths=this._get(inst,"numberOfMonths");return(numMonths==null?[1,1]:(typeof numMonths=="number"?[1,numMonths]:numMonths))},_getMinMaxDate:function(inst,minMax,checkRange){var date=this._determineDate(this._get(inst,minMax+"Date"),null);return(!checkRange||!inst.rangeStart?date:(!date||inst.rangeStart>date?inst.rangeStart:date))},_getDaysInMonth:function(year,month){return 32-new Date(year,month,32).getDate()},_getFirstDayOfMonth:function(year,month){return new Date(year,month,1).getDay()},_canAdjustMonth:function(inst,offset,curYear,curMonth){var numMonths=this._getNumberOfMonths(inst);var date=this._daylightSavingAdjust(new Date(curYear,curMonth+(offset<0?offset:numMonths[1]),1));if(offset<0){date.setDate(this._getDaysInMonth(date.getFullYear(),date.getMonth()))}return this._isInRange(inst,date)},_isInRange:function(inst,date){var newMinDate=(!inst.rangeStart?null:this._daylightSavingAdjust(new Date(inst.selectedYear,inst.selectedMonth,inst.selectedDay)));newMinDate=(newMinDate&&inst.rangeStart<newMinDate?inst.rangeStart:newMinDate);var minDate=newMinDate||this._getMinMaxDate(inst,"min");var maxDate=this._getMinMaxDate(inst,"max");return((!minDate||date>=minDate)&&(!maxDate||date<=maxDate))},_getFormatConfig:function(inst){var shortYearCutoff=this._get(inst,"shortYearCutoff");shortYearCutoff=(typeof shortYearCutoff!="string"?shortYearCutoff:new Date().getFullYear()%100+parseInt(shortYearCutoff,10));return{shortYearCutoff:shortYearCutoff,dayNamesShort:this._get(inst,"dayNamesShort"),dayNames:this._get(inst,"dayNames"),monthNamesShort:this._get(inst,"monthNamesShort"),monthNames:this._get(inst,"monthNames")}},_formatDate:function(inst,day,month,year){if(!day){inst.currentDay=inst.selectedDay;inst.currentMonth=inst.selectedMonth;inst.currentYear=inst.selectedYear}var date=(day?(typeof day=="object"?day:this._daylightSavingAdjust(new Date(year,month,day))):this._daylightSavingAdjust(new Date(inst.currentYear,inst.currentMonth,inst.currentDay)));return this.formatDate(this._get(inst,"dateFormat"),date,this._getFormatConfig(inst))}});function extendRemove(target,props){$.extend(target,props);for(var name in props){if(props[name]==null||props[name]==undefined){target[name]=props[name]}}return target}function isArray(a){return(a&&(($.browser.safari&&typeof a=="object"&&a.length)||(a.constructor&&a.constructor.toString().match(/\Array\(\)/))))}$.fn.datepicker=function(options){if(!$.datepicker.initialized){$(document).mousedown($.datepicker._checkExternalClick).find("body").append($.datepicker.dpDiv);$.datepicker.initialized=true}var otherArgs=Array.prototype.slice.call(arguments,1);if(typeof options=="string"&&(options=="isDisabled"||options=="getDate")){return $.datepicker["_"+options+"Datepicker"].apply($.datepicker,[this[0]].concat(otherArgs))}if(options=="option"&&arguments.length==2&&typeof arguments[1]=="string"){return $.datepicker["_"+options+"Datepicker"].apply($.datepicker,[this[0]].concat(otherArgs))}return this.each(function(){typeof options=="string"?$.datepicker["_"+options+"Datepicker"].apply($.datepicker,[this].concat(otherArgs)):$.datepicker._attachDatepicker(this,options)})};$.datepicker=new Datepicker();$.datepicker.initialized=false;$.datepicker.uuid=new Date().getTime();$.datepicker.version="1.7.3";window.DP_jQuery=$})(jQuery);;
/*
 * jquery.qtip. The jQuery tooltip plugin
 *
 * Copyright (c) 2009 Craig Thompson
 * http://craigsworks.com
 *
 * Licensed under MIT
 * http://www.opensource.org/licenses/mit-license.php
 *
 * Launch  : February 2009
 * Version : 1.0.0-rc3
 * Released: Tuesday 12th May, 2009 - 00:00
 * Debug: jquery.qtip.debug.js
 */
(function(f){f.fn.qtip=function(B,u){var y,t,A,s,x,w,v,z;if(typeof B=="string"){if(typeof f(this).data("qtip")!=="object"){f.fn.qtip.log.error.call(self,1,f.fn.qtip.constants.NO_TOOLTIP_PRESENT,false)}if(B=="api"){return f(this).data("qtip").interfaces[f(this).data("qtip").current]}else{if(B=="interfaces"){return f(this).data("qtip").interfaces}}}else{if(!B){B={}}if(typeof B.content!=="object"||(B.content.jquery&&B.content.length>0)){B.content={text:B.content}}if(typeof B.content.title!=="object"){B.content.title={text:B.content.title}}if(typeof B.position!=="object"){B.position={corner:B.position}}if(typeof B.position.corner!=="object"){B.position.corner={target:B.position.corner,tooltip:B.position.corner}}if(typeof B.show!=="object"){B.show={when:B.show}}if(typeof B.show.when!=="object"){B.show.when={event:B.show.when}}if(typeof B.show.effect!=="object"){B.show.effect={type:B.show.effect}}if(typeof B.hide!=="object"){B.hide={when:B.hide}}if(typeof B.hide.when!=="object"){B.hide.when={event:B.hide.when}}if(typeof B.hide.effect!=="object"){B.hide.effect={type:B.hide.effect}}if(typeof B.style!=="object"){B.style={name:B.style}}B.style=c(B.style);s=f.extend(true,{},f.fn.qtip.defaults,B);s.style=a.call({options:s},s.style);s.user=f.extend(true,{},B)}return f(this).each(function(){if(typeof B=="string"){w=B.toLowerCase();A=f(this).qtip("interfaces");if(typeof A=="object"){if(u===true&&w=="destroy"){while(A.length>0){A[A.length-1].destroy()}}else{if(u!==true){A=[f(this).qtip("api")]}for(y=0;y<A.length;y++){if(w=="destroy"){A[y].destroy()}else{if(A[y].status.rendered===true){if(w=="show"){A[y].show()}else{if(w=="hide"){A[y].hide()}else{if(w=="focus"){A[y].focus()}else{if(w=="disable"){A[y].disable(true)}else{if(w=="enable"){A[y].disable(false)}}}}}}}}}}}else{v=f.extend(true,{},s);v.hide.effect.length=s.hide.effect.length;v.show.effect.length=s.show.effect.length;if(v.position.container===false){v.position.container=f(document.body)}if(v.position.target===false){v.position.target=f(this)}if(v.show.when.target===false){v.show.when.target=f(this)}if(v.hide.when.target===false){v.hide.when.target=f(this)}t=f.fn.qtip.interfaces.length;for(y=0;y<t;y++){if(typeof f.fn.qtip.interfaces[y]=="undefined"){t=y;break}}x=new d(f(this),v,t);f.fn.qtip.interfaces[t]=x;if(typeof f(this).data("qtip")=="object"){if(typeof f(this).attr("qtip")==="undefined"){f(this).data("qtip").current=f(this).data("qtip").interfaces.length}f(this).data("qtip").interfaces.push(x)}else{f(this).data("qtip",{current:0,interfaces:[x]})}if(v.content.prerender===false&&v.show.when.event!==false&&v.show.ready!==true){v.show.when.target.bind(v.show.when.event+".qtip-"+t+"-create",{qtip:t},function(C){z=f.fn.qtip.interfaces[C.data.qtip];z.options.show.when.target.unbind(z.options.show.when.event+".qtip-"+C.data.qtip+"-create");z.cache.mouse={x:C.pageX,y:C.pageY};p.call(z);z.options.show.when.target.trigger(z.options.show.when.event)})}else{x.cache.mouse={x:v.show.when.target.offset().left,y:v.show.when.target.offset().top};p.call(x)}}})};function d(u,t,v){var s=this;s.id=v;s.options=t;s.status={animated:false,rendered:false,disabled:false,focused:false};s.elements={target:u.addClass(s.options.style.classes.target),tooltip:null,wrapper:null,content:null,contentWrapper:null,title:null,button:null,tip:null,bgiframe:null};s.cache={mouse:{},position:{},toggle:0};s.timers={};f.extend(s,s.options.api,{show:function(y){var x,z;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"show")}if(s.elements.tooltip.css("display")!=="none"){return s}s.elements.tooltip.stop(true,false);x=s.beforeShow.call(s,y);if(x===false){return s}function w(){if(s.options.position.type!=="static"){s.focus()}s.onShow.call(s,y);if(f.browser.msie){s.elements.tooltip.get(0).style.removeAttribute("filter")}}s.cache.toggle=1;if(s.options.position.type!=="static"){s.updatePosition(y,(s.options.show.effect.length>0))}if(typeof s.options.show.solo=="object"){z=f(s.options.show.solo)}else{if(s.options.show.solo===true){z=f("div.qtip").not(s.elements.tooltip)}}if(z){z.each(function(){if(f(this).qtip("api").status.rendered===true){f(this).qtip("api").hide()}})}if(typeof s.options.show.effect.type=="function"){s.options.show.effect.type.call(s.elements.tooltip,s.options.show.effect.length);s.elements.tooltip.queue(function(){w();f(this).dequeue()})}else{switch(s.options.show.effect.type.toLowerCase()){case"fade":s.elements.tooltip.fadeIn(s.options.show.effect.length,w);break;case"slide":s.elements.tooltip.slideDown(s.options.show.effect.length,function(){w();if(s.options.position.type!=="static"){s.updatePosition(y,true)}});break;case"grow":s.elements.tooltip.show(s.options.show.effect.length,w);break;default:s.elements.tooltip.show(null,w);break}s.elements.tooltip.addClass(s.options.style.classes.active)}return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_SHOWN,"show")},hide:function(y){var x;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"hide")}else{if(s.elements.tooltip.css("display")==="none"){return s}}clearTimeout(s.timers.show);s.elements.tooltip.stop(true,false);x=s.beforeHide.call(s,y);if(x===false){return s}function w(){s.onHide.call(s,y)}s.cache.toggle=0;if(typeof s.options.hide.effect.type=="function"){s.options.hide.effect.type.call(s.elements.tooltip,s.options.hide.effect.length);s.elements.tooltip.queue(function(){w();f(this).dequeue()})}else{switch(s.options.hide.effect.type.toLowerCase()){case"fade":s.elements.tooltip.fadeOut(s.options.hide.effect.length,w);break;case"slide":s.elements.tooltip.slideUp(s.options.hide.effect.length,w);break;case"grow":s.elements.tooltip.hide(s.options.hide.effect.length,w);break;default:s.elements.tooltip.hide(null,w);break}s.elements.tooltip.removeClass(s.options.style.classes.active)}return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_HIDDEN,"hide")},updatePosition:function(w,x){var C,G,L,J,H,E,y,I,B,D,K,A,F,z;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"updatePosition")}else{if(s.options.position.type=="static"){return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.CANNOT_POSITION_STATIC,"updatePosition")}}G={position:{left:0,top:0},dimensions:{height:0,width:0},corner:s.options.position.corner.target};L={position:s.getPosition(),dimensions:s.getDimensions(),corner:s.options.position.corner.tooltip};if(s.options.position.target!=="mouse"){if(s.options.position.target.get(0).nodeName.toLowerCase()=="area"){J=s.options.position.target.attr("coords").split(",");for(C=0;C<J.length;C++){J[C]=parseInt(J[C])}H=s.options.position.target.parent("map").attr("name");E=f('img[usemap="#'+H+'"]:first').offset();G.position={left:Math.floor(E.left+J[0]),top:Math.floor(E.top+J[1])};switch(s.options.position.target.attr("shape").toLowerCase()){case"rect":G.dimensions={width:Math.ceil(Math.abs(J[2]-J[0])),height:Math.ceil(Math.abs(J[3]-J[1]))};break;case"circle":G.dimensions={width:J[2]+1,height:J[2]+1};break;case"poly":G.dimensions={width:J[0],height:J[1]};for(C=0;C<J.length;C++){if(C%2==0){if(J[C]>G.dimensions.width){G.dimensions.width=J[C]}if(J[C]<J[0]){G.position.left=Math.floor(E.left+J[C])}}else{if(J[C]>G.dimensions.height){G.dimensions.height=J[C]}if(J[C]<J[1]){G.position.top=Math.floor(E.top+J[C])}}}G.dimensions.width=G.dimensions.width-(G.position.left-E.left);G.dimensions.height=G.dimensions.height-(G.position.top-E.top);break;default:return f.fn.qtip.log.error.call(s,4,f.fn.qtip.constants.INVALID_AREA_SHAPE,"updatePosition");break}G.dimensions.width-=2;G.dimensions.height-=2}else{if(s.options.position.target.add(document.body).length===1){G.position={left:f(document).scrollLeft(),top:f(document).scrollTop()};G.dimensions={height:f(window).height(),width:f(window).width()}}else{if(typeof s.options.position.target.attr("qtip")!=="undefined"){G.position=s.options.position.target.qtip("api").cache.position}else{G.position=s.options.position.target.offset()}G.dimensions={height:s.options.position.target.outerHeight(),width:s.options.position.target.outerWidth()}}}y=f.extend({},G.position);if(G.corner.search(/right/i)!==-1){y.left+=G.dimensions.width}if(G.corner.search(/bottom/i)!==-1){y.top+=G.dimensions.height}if(G.corner.search(/((top|bottom)Middle)|center/)!==-1){y.left+=(G.dimensions.width/2)}if(G.corner.search(/((left|right)Middle)|center/)!==-1){y.top+=(G.dimensions.height/2)}}else{G.position=y={left:s.cache.mouse.x,top:s.cache.mouse.y};G.dimensions={height:1,width:1}}if(L.corner.search(/right/i)!==-1){y.left-=L.dimensions.width}if(L.corner.search(/bottom/i)!==-1){y.top-=L.dimensions.height}if(L.corner.search(/((top|bottom)Middle)|center/)!==-1){y.left-=(L.dimensions.width/2)}if(L.corner.search(/((left|right)Middle)|center/)!==-1){y.top-=(L.dimensions.height/2)}I=(f.browser.msie)?1:0;B=(f.browser.msie&&parseInt(f.browser.version.charAt(0))===6)?1:0;if(s.options.style.border.radius>0){if(L.corner.search(/Left/)!==-1){y.left-=s.options.style.border.radius}else{if(L.corner.search(/Right/)!==-1){y.left+=s.options.style.border.radius}}if(L.corner.search(/Top/)!==-1){y.top-=s.options.style.border.radius}else{if(L.corner.search(/Bottom/)!==-1){y.top+=s.options.style.border.radius}}}if(I){if(L.corner.search(/top/)!==-1){y.top-=I}else{if(L.corner.search(/bottom/)!==-1){y.top+=I}}if(L.corner.search(/left/)!==-1){y.left-=I}else{if(L.corner.search(/right/)!==-1){y.left+=I}}if(L.corner.search(/leftMiddle|rightMiddle/)!==-1){y.top-=1}}if(s.options.position.adjust.screen===true){y=o.call(s,y,G,L)}if(s.options.position.target==="mouse"&&s.options.position.adjust.mouse===true){if(s.options.position.adjust.screen===true&&s.elements.tip){K=s.elements.tip.attr("rel")}else{K=s.options.position.corner.tooltip}y.left+=(K.search(/right/i)!==-1)?-6:6;y.top+=(K.search(/bottom/i)!==-1)?-6:6}if(!s.elements.bgiframe&&f.browser.msie&&parseInt(f.browser.version.charAt(0))==6){f("select, object").each(function(){A=f(this).offset();A.bottom=A.top+f(this).height();A.right=A.left+f(this).width();if(y.top+L.dimensions.height>=A.top&&y.left+L.dimensions.width>=A.left){k.call(s)}})}y.left+=s.options.position.adjust.x;y.top+=s.options.position.adjust.y;F=s.getPosition();if(y.left!=F.left||y.top!=F.top){z=s.beforePositionUpdate.call(s,w);if(z===false){return s}s.cache.position=y;if(x===true){s.status.animated=true;s.elements.tooltip.animate(y,200,"swing",function(){s.status.animated=false})}else{s.elements.tooltip.css(y)}s.onPositionUpdate.call(s,w);if(typeof w!=="undefined"&&w.type&&w.type!=="mousemove"){f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_POSITION_UPDATED,"updatePosition")}}return s},updateWidth:function(w){var x;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"updateWidth")}else{if(w&&typeof w!=="number"){return f.fn.qtip.log.error.call(s,2,"newWidth must be of type number","updateWidth")}}x=s.elements.contentWrapper.siblings().add(s.elements.tip).add(s.elements.button);if(!w){if(typeof s.options.style.width.value=="number"){w=s.options.style.width.value}else{s.elements.tooltip.css({width:"auto"});x.hide();if(f.browser.msie){s.elements.wrapper.add(s.elements.contentWrapper.children()).css({zoom:"normal"})}w=s.getDimensions().width+1;if(!s.options.style.width.value){if(w>s.options.style.width.max){w=s.options.style.width.max}if(w<s.options.style.width.min){w=s.options.style.width.min}}}}if(w%2!==0){w-=1}s.elements.tooltip.width(w);x.show();if(s.options.style.border.radius){s.elements.tooltip.find(".qtip-betweenCorners").each(function(y){f(this).width(w-(s.options.style.border.radius*2))})}if(f.browser.msie){s.elements.wrapper.add(s.elements.contentWrapper.children()).css({zoom:"1"});s.elements.wrapper.width(w);if(s.elements.bgiframe){s.elements.bgiframe.width(w).height(s.getDimensions.height)}}return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_WIDTH_UPDATED,"updateWidth")},updateStyle:function(w){var z,A,x,y,B;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"updateStyle")}else{if(typeof w!=="string"||!f.fn.qtip.styles[w]){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.STYLE_NOT_DEFINED,"updateStyle")}}s.options.style=a.call(s,f.fn.qtip.styles[w],s.options.user.style);s.elements.content.css(q(s.options.style));if(s.options.content.title.text!==false){s.elements.title.css(q(s.options.style.title,true))}s.elements.contentWrapper.css({borderColor:s.options.style.border.color});if(s.options.style.tip.corner!==false){if(f("<canvas>").get(0).getContext){z=s.elements.tooltip.find(".qtip-tip canvas:first");x=z.get(0).getContext("2d");x.clearRect(0,0,300,300);y=z.parent("div[rel]:first").attr("rel");B=b(y,s.options.style.tip.size.width,s.options.style.tip.size.height);h.call(s,z,B,s.options.style.tip.color||s.options.style.border.color)}else{if(f.browser.msie){z=s.elements.tooltip.find('.qtip-tip [nodeName="shape"]');z.attr("fillcolor",s.options.style.tip.color||s.options.style.border.color)}}}if(s.options.style.border.radius>0){s.elements.tooltip.find(".qtip-betweenCorners").css({backgroundColor:s.options.style.border.color});if(f("<canvas>").get(0).getContext){A=g(s.options.style.border.radius);s.elements.tooltip.find(".qtip-wrapper canvas").each(function(){x=f(this).get(0).getContext("2d");x.clearRect(0,0,300,300);y=f(this).parent("div[rel]:first").attr("rel");r.call(s,f(this),A[y],s.options.style.border.radius,s.options.style.border.color)})}else{if(f.browser.msie){s.elements.tooltip.find('.qtip-wrapper [nodeName="arc"]').each(function(){f(this).attr("fillcolor",s.options.style.border.color)})}}}return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_STYLE_UPDATED,"updateStyle")},updateContent:function(A,y){var z,x,w;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"updateContent")}else{if(!A){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.NO_CONTENT_PROVIDED,"updateContent")}}z=s.beforeContentUpdate.call(s,A);if(typeof z=="string"){A=z}else{if(z===false){return}}if(f.browser.msie){s.elements.contentWrapper.children().css({zoom:"normal"})}if(A.jquery&&A.length>0){A.clone(true).appendTo(s.elements.content).show()}else{s.elements.content.html(A)}x=s.elements.content.find("img[complete=false]");if(x.length>0){w=0;x.each(function(C){f('<img src="'+f(this).attr("src")+'" />').load(function(){if(++w==x.length){B()}})})}else{B()}function B(){s.updateWidth();if(y!==false){if(s.options.position.type!=="static"){s.updatePosition(s.elements.tooltip.is(":visible"),true)}if(s.options.style.tip.corner!==false){n.call(s)}}}s.onContentUpdate.call(s);return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_CONTENT_UPDATED,"loadContent")},loadContent:function(w,z,A){var y;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"loadContent")}y=s.beforeContentLoad.call(s);if(y===false){return s}if(A=="post"){f.post(w,z,x)}else{f.get(w,z,x)}function x(B){s.onContentLoad.call(s);f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_CONTENT_LOADED,"loadContent");s.updateContent(B)}return s},updateTitle:function(w){if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"updateTitle")}else{if(!w){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.NO_CONTENT_PROVIDED,"updateTitle")}}returned=s.beforeTitleUpdate.call(s);if(returned===false){return s}if(s.elements.button){s.elements.button=s.elements.button.clone(true)}s.elements.title.html(w);if(s.elements.button){s.elements.title.prepend(s.elements.button)}s.onTitleUpdate.call(s);return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_TITLE_UPDATED,"updateTitle")},focus:function(A){var y,x,w,z;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"focus")}else{if(s.options.position.type=="static"){return f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.CANNOT_FOCUS_STATIC,"focus")}}y=parseInt(s.elements.tooltip.css("z-index"));x=6000+f("div.qtip[qtip]").length-1;if(!s.status.focused&&y!==x){z=s.beforeFocus.call(s,A);if(z===false){return s}f("div.qtip[qtip]").not(s.elements.tooltip).each(function(){if(f(this).qtip("api").status.rendered===true){w=parseInt(f(this).css("z-index"));if(typeof w=="number"&&w>-1){f(this).css({zIndex:parseInt(f(this).css("z-index"))-1})}f(this).qtip("api").status.focused=false}});s.elements.tooltip.css({zIndex:x});s.status.focused=true;s.onFocus.call(s,A);f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_FOCUSED,"focus")}return s},disable:function(w){if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"disable")}if(w){if(!s.status.disabled){s.status.disabled=true;f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_DISABLED,"disable")}else{f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.TOOLTIP_ALREADY_DISABLED,"disable")}}else{if(s.status.disabled){s.status.disabled=false;f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_ENABLED,"disable")}else{f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.TOOLTIP_ALREADY_ENABLED,"disable")}}return s},destroy:function(){var w,x,y;x=s.beforeDestroy.call(s);if(x===false){return s}if(s.status.rendered){s.options.show.when.target.unbind("mousemove.qtip",s.updatePosition);s.options.show.when.target.unbind("mouseout.qtip",s.hide);s.options.show.when.target.unbind(s.options.show.when.event+".qtip");s.options.hide.when.target.unbind(s.options.hide.when.event+".qtip");s.elements.tooltip.unbind(s.options.hide.when.event+".qtip");s.elements.tooltip.unbind("mouseover.qtip",s.focus);s.elements.tooltip.remove()}else{s.options.show.when.target.unbind(s.options.show.when.event+".qtip-create")}if(typeof s.elements.target.data("qtip")=="object"){y=s.elements.target.data("qtip").interfaces;if(typeof y=="object"&&y.length>0){for(w=0;w<y.length-1;w++){if(y[w].id==s.id){y.splice(w,1)}}}}delete f.fn.qtip.interfaces[s.id];if(typeof y=="object"&&y.length>0){s.elements.target.data("qtip").current=y.length-1}else{s.elements.target.removeData("qtip")}s.onDestroy.call(s);f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_DESTROYED,"destroy");return s.elements.target},getPosition:function(){var w,x;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"getPosition")}w=(s.elements.tooltip.css("display")!=="none")?false:true;if(w){s.elements.tooltip.css({visiblity:"hidden"}).show()}x=s.elements.tooltip.offset();if(w){s.elements.tooltip.css({visiblity:"visible"}).hide()}return x},getDimensions:function(){var w,x;if(!s.status.rendered){return f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.TOOLTIP_NOT_RENDERED,"getDimensions")}w=(!s.elements.tooltip.is(":visible"))?true:false;if(w){s.elements.tooltip.css({visiblity:"hidden"}).show()}x={height:s.elements.tooltip.outerHeight(),width:s.elements.tooltip.outerWidth()};if(w){s.elements.tooltip.css({visiblity:"visible"}).hide()}return x}})}function p(){var s,w,u,t,v,y,x;s=this;s.beforeRender.call(s);s.status.rendered=true;s.elements.tooltip='<div qtip="'+s.id+'" class="qtip '+(s.options.style.classes.tooltip||s.options.style)+'"style="display:none; -moz-border-radius:0; -webkit-border-radius:0; border-radius:0;position:'+s.options.position.type+';">  <div class="qtip-wrapper" style="position:relative; overflow:hidden; text-align:left;">    <div class="qtip-contentWrapper" style="overflow:hidden;">       <div class="qtip-content '+s.options.style.classes.content+'"></div></div></div></div>';s.elements.tooltip=f(s.elements.tooltip);s.elements.tooltip.appendTo(s.options.position.container);s.elements.tooltip.data("qtip",{current:0,interfaces:[s]});s.elements.wrapper=s.elements.tooltip.children("div:first");s.elements.contentWrapper=s.elements.wrapper.children("div:first").css({background:s.options.style.background});s.elements.content=s.elements.contentWrapper.children("div:first").css(q(s.options.style));if(f.browser.msie){s.elements.wrapper.add(s.elements.content).css({zoom:1})}if(s.options.hide.when.event=="unfocus"){s.elements.tooltip.attr("unfocus",true)}if(typeof s.options.style.width.value=="number"){s.updateWidth()}if(f("<canvas>").get(0).getContext||f.browser.msie){if(s.options.style.border.radius>0){m.call(s)}else{s.elements.contentWrapper.css({border:s.options.style.border.width+"px solid "+s.options.style.border.color})}if(s.options.style.tip.corner!==false){e.call(s)}}else{s.elements.contentWrapper.css({border:s.options.style.border.width+"px solid "+s.options.style.border.color});s.options.style.border.radius=0;s.options.style.tip.corner=false;f.fn.qtip.log.error.call(s,2,f.fn.qtip.constants.CANVAS_VML_NOT_SUPPORTED,"render")}if((typeof s.options.content.text=="string"&&s.options.content.text.length>0)||(s.options.content.text.jquery&&s.options.content.text.length>0)){u=s.options.content.text}else{if(typeof s.elements.target.attr("title")=="string"&&s.elements.target.attr("title").length>0){u=s.elements.target.attr("title").replace("\\n","<br />");s.elements.target.attr("title","")}else{if(typeof s.elements.target.attr("alt")=="string"&&s.elements.target.attr("alt").length>0){u=s.elements.target.attr("alt").replace("\\n","<br />");s.elements.target.attr("alt","")}else{u=" ";f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.NO_VALID_CONTENT,"render")}}}if(s.options.content.title.text!==false){j.call(s)}s.updateContent(u);l.call(s);if(s.options.show.ready===true){s.show()}if(s.options.content.url!==false){t=s.options.content.url;v=s.options.content.data;y=s.options.content.method||"get";s.loadContent(t,v,y)}s.onRender.call(s);f.fn.qtip.log.error.call(s,1,f.fn.qtip.constants.EVENT_RENDERED,"render")}function m(){var F,z,t,B,x,E,u,G,D,y,w,C,A,s,v;F=this;F.elements.wrapper.find(".qtip-borderBottom, .qtip-borderTop").remove();t=F.options.style.border.width;B=F.options.style.border.radius;x=F.options.style.border.color||F.options.style.tip.color;E=g(B);u={};for(z in E){u[z]='<div rel="'+z+'" style="'+((z.search(/Left/)!==-1)?"left":"right")+":0; position:absolute; height:"+B+"px; width:"+B+'px; overflow:hidden; line-height:0.1px; font-size:1px">';if(f("<canvas>").get(0).getContext){u[z]+='<canvas height="'+B+'" width="'+B+'" style="vertical-align: top"></canvas>'}else{if(f.browser.msie){G=B*2+3;u[z]+='<v:arc stroked="false" fillcolor="'+x+'" startangle="'+E[z][0]+'" endangle="'+E[z][1]+'" style="width:'+G+"px; height:"+G+"px; margin-top:"+((z.search(/bottom/)!==-1)?-2:-1)+"px; margin-left:"+((z.search(/Right/)!==-1)?E[z][2]-3.5:-1)+'px; vertical-align:top; display:inline-block; behavior:url(#default#VML)"></v:arc>'}}u[z]+="</div>"}D=F.getDimensions().width-(Math.max(t,B)*2);y='<div class="qtip-betweenCorners" style="height:'+B+"px; width:"+D+"px; overflow:hidden; background-color:"+x+'; line-height:0.1px; font-size:1px;">';w='<div class="qtip-borderTop" dir="ltr" style="height:'+B+"px; margin-left:"+B+'px; line-height:0.1px; font-size:1px; padding:0;">'+u.topLeft+u.topRight+y;F.elements.wrapper.prepend(w);C='<div class="qtip-borderBottom" dir="ltr" style="height:'+B+"px; margin-left:"+B+'px; line-height:0.1px; font-size:1px; padding:0;">'+u.bottomLeft+u.bottomRight+y;F.elements.wrapper.append(C);if(f("<canvas>").get(0).getContext){F.elements.wrapper.find("canvas").each(function(){A=E[f(this).parent("[rel]:first").attr("rel")];r.call(F,f(this),A,B,x)})}else{if(f.browser.msie){F.elements.tooltip.append('<v:image style="behavior:url(#default#VML);"></v:image>')}}s=Math.max(B,(B+(t-B)));v=Math.max(t-B,0);F.elements.contentWrapper.css({border:"0px solid "+x,borderWidth:v+"px "+s+"px"})}function r(u,w,s,t){var v=u.get(0).getContext("2d");v.fillStyle=t;v.beginPath();v.arc(w[0],w[1],s,0,Math.PI*2,false);v.fill()}function e(v){var t,s,x,u,w;t=this;if(t.elements.tip!==null){t.elements.tip.remove()}s=t.options.style.tip.color||t.options.style.border.color;if(t.options.style.tip.corner===false){return}else{if(!v){v=t.options.style.tip.corner}}x=b(v,t.options.style.tip.size.width,t.options.style.tip.size.height);t.elements.tip='<div class="'+t.options.style.classes.tip+'" dir="ltr" rel="'+v+'" style="position:absolute; height:'+t.options.style.tip.size.height+"px; width:"+t.options.style.tip.size.width+'px; margin:0 auto; line-height:0.1px; font-size:1px;">';if(f("<canvas>").get(0).getContext){t.elements.tip+='<canvas height="'+t.options.style.tip.size.height+'" width="'+t.options.style.tip.size.width+'"></canvas>'}else{if(f.browser.msie){u=t.options.style.tip.size.width+","+t.options.style.tip.size.height;w="m"+x[0][0]+","+x[0][1];w+=" l"+x[1][0]+","+x[1][1];w+=" "+x[2][0]+","+x[2][1];w+=" xe";t.elements.tip+='<v:shape fillcolor="'+s+'" stroked="false" filled="true" path="'+w+'" coordsize="'+u+'" style="width:'+t.options.style.tip.size.width+"px; height:"+t.options.style.tip.size.height+"px; line-height:0.1px; display:inline-block; behavior:url(#default#VML); vertical-align:"+((v.search(/top/)!==-1)?"bottom":"top")+'"></v:shape>';t.elements.tip+='<v:image style="behavior:url(#default#VML);"></v:image>';t.elements.contentWrapper.css("position","relative")}}t.elements.tooltip.prepend(t.elements.tip+"</div>");t.elements.tip=t.elements.tooltip.find("."+t.options.style.classes.tip).eq(0);if(f("<canvas>").get(0).getContext){h.call(t,t.elements.tip.find("canvas:first"),x,s)}if(v.search(/top/)!==-1&&f.browser.msie&&parseInt(f.browser.version.charAt(0))===6){t.elements.tip.css({marginTop:-4})}n.call(t,v)}function h(t,v,s){var u=t.get(0).getContext("2d");u.fillStyle=s;u.beginPath();u.moveTo(v[0][0],v[0][1]);u.lineTo(v[1][0],v[1][1]);u.lineTo(v[2][0],v[2][1]);u.fill()}function n(u){var t,w,s,x,v;t=this;if(t.options.style.tip.corner===false||!t.elements.tip){return}if(!u){u=t.elements.tip.attr("rel")}w=positionAdjust=(f.browser.msie)?1:0;t.elements.tip.css(u.match(/left|right|top|bottom/)[0],0);if(u.search(/top|bottom/)!==-1){if(f.browser.msie){if(parseInt(f.browser.version.charAt(0))===6){positionAdjust=(u.search(/top/)!==-1)?-3:1}else{positionAdjust=(u.search(/top/)!==-1)?1:2}}if(u.search(/Middle/)!==-1){t.elements.tip.css({left:"50%",marginLeft:-(t.options.style.tip.size.width/2)})}else{if(u.search(/Left/)!==-1){t.elements.tip.css({left:t.options.style.border.radius-w})}else{if(u.search(/Right/)!==-1){t.elements.tip.css({right:t.options.style.border.radius+w})}}}if(u.search(/top/)!==-1){t.elements.tip.css({top:-positionAdjust})}else{t.elements.tip.css({bottom:positionAdjust})}}else{if(u.search(/left|right/)!==-1){if(f.browser.msie){positionAdjust=(parseInt(f.browser.version.charAt(0))===6)?1:((u.search(/left/)!==-1)?1:2)}if(u.search(/Middle/)!==-1){t.elements.tip.css({top:"50%",marginTop:-(t.options.style.tip.size.height/2)})}else{if(u.search(/Top/)!==-1){t.elements.tip.css({top:t.options.style.border.radius-w})}else{if(u.search(/Bottom/)!==-1){t.elements.tip.css({bottom:t.options.style.border.radius+w})}}}if(u.search(/left/)!==-1){t.elements.tip.css({left:-positionAdjust})}else{t.elements.tip.css({right:positionAdjust})}}}s="padding-"+u.match(/left|right|top|bottom/)[0];x=t.options.style.tip.size[(s.search(/left|right/)!==-1)?"width":"height"];t.elements.tooltip.css("padding",0);t.elements.tooltip.css(s,x);if(f.browser.msie&&parseInt(f.browser.version.charAt(0))==6){v=parseInt(t.elements.tip.css("margin-top"))||0;v+=parseInt(t.elements.content.css("margin-top"))||0;t.elements.tip.css({marginTop:v})}}function j(){var s=this;if(s.elements.title!==null){s.elements.title.remove()}s.elements.title=f('<div class="'+s.options.style.classes.title+'">').css(q(s.options.style.title,true)).css({zoom:(f.browser.msie)?1:0}).prependTo(s.elements.contentWrapper);if(s.options.content.title.text){s.updateTitle.call(s,s.options.content.title.text)}if(s.options.content.title.button!==false&&typeof s.options.content.title.button=="string"){s.elements.button=f('<a class="'+s.options.style.classes.button+'" style="float:right; position: relative"></a>').css(q(s.options.style.button,true)).html(s.options.content.title.button).prependTo(s.elements.title).click(function(t){if(!s.status.disabled){s.hide(t)}})}}function l(){var t,v,u,s;t=this;v=t.options.show.when.target;u=t.options.hide.when.target;if(t.options.hide.fixed){u=u.add(t.elements.tooltip)}if(t.options.hide.when.event=="inactive"){s=["click","dblclick","mousedown","mouseup","mousemove","mouseout","mouseenter","mouseleave","mouseover"];function y(z){if(t.status.disabled===true){return}clearTimeout(t.timers.inactive);t.timers.inactive=setTimeout(function(){f(s).each(function(){u.unbind(this+".qtip-inactive");t.elements.content.unbind(this+".qtip-inactive")});t.hide(z)},t.options.hide.delay)}}else{if(t.options.hide.fixed===true){t.elements.tooltip.bind("mouseover.qtip",function(){if(t.status.disabled===true){return}clearTimeout(t.timers.hide)})}}function x(z){if(t.status.disabled===true){return}if(t.options.hide.when.event=="inactive"){f(s).each(function(){u.bind(this+".qtip-inactive",y);t.elements.content.bind(this+".qtip-inactive",y)});y()}clearTimeout(t.timers.show);clearTimeout(t.timers.hide);t.timers.show=setTimeout(function(){t.show(z)},t.options.show.delay)}function w(z){if(t.status.disabled===true){return}if(t.options.hide.fixed===true&&t.options.hide.when.event.search(/mouse(out|leave)/i)!==-1&&f(z.relatedTarget).parents("div.qtip[qtip]").length>0){z.stopPropagation();z.preventDefault();clearTimeout(t.timers.hide);return false}clearTimeout(t.timers.show);clearTimeout(t.timers.hide);t.elements.tooltip.stop(true,true);t.timers.hide=setTimeout(function(){t.hide(z)},t.options.hide.delay)}if((t.options.show.when.target.add(t.options.hide.when.target).length===1&&t.options.show.when.event==t.options.hide.when.event&&t.options.hide.when.event!=="inactive")||t.options.hide.when.event=="unfocus"){t.cache.toggle=0;v.bind(t.options.show.when.event+".qtip",function(z){if(t.cache.toggle==0){x(z)}else{w(z)}})}else{v.bind(t.options.show.when.event+".qtip",x);if(t.options.hide.when.event!=="inactive"){u.bind(t.options.hide.when.event+".qtip",w)}}if(t.options.position.type.search(/(fixed|absolute)/)!==-1){t.elements.tooltip.bind("mouseover.qtip",t.focus)}if(t.options.position.target==="mouse"&&t.options.position.type!=="static"){v.bind("mousemove.qtip",function(z){t.cache.mouse={x:z.pageX,y:z.pageY};if(t.status.disabled===false&&t.options.position.adjust.mouse===true&&t.options.position.type!=="static"&&t.elements.tooltip.css("display")!=="none"){t.updatePosition(z)}})}}function o(u,v,A){var z,s,x,y,t,w;z=this;if(A.corner=="center"){return v.position}s=f.extend({},u);y={x:false,y:false};t={left:(s.left<f.fn.qtip.cache.screen.scroll.left),right:(s.left+A.dimensions.width+2>=f.fn.qtip.cache.screen.width+f.fn.qtip.cache.screen.scroll.left),top:(s.top<f.fn.qtip.cache.screen.scroll.top),bottom:(s.top+A.dimensions.height+2>=f.fn.qtip.cache.screen.height+f.fn.qtip.cache.screen.scroll.top)};x={left:(t.left&&(A.corner.search(/right/i)!=-1||(A.corner.search(/right/i)==-1&&!t.right))),right:(t.right&&(A.corner.search(/left/i)!=-1||(A.corner.search(/left/i)==-1&&!t.left))),top:(t.top&&A.corner.search(/top/i)==-1),bottom:(t.bottom&&A.corner.search(/bottom/i)==-1)};if(x.left){if(z.options.position.target!=="mouse"){s.left=v.position.left+v.dimensions.width}else{s.left=z.cache.mouse.x}y.x="Left"}else{if(x.right){if(z.options.position.target!=="mouse"){s.left=v.position.left-A.dimensions.width}else{s.left=z.cache.mouse.x-A.dimensions.width}y.x="Right"}}if(x.top){if(z.options.position.target!=="mouse"){s.top=v.position.top+v.dimensions.height}else{s.top=z.cache.mouse.y}y.y="top"}else{if(x.bottom){if(z.options.position.target!=="mouse"){s.top=v.position.top-A.dimensions.height}else{s.top=z.cache.mouse.y-A.dimensions.height}y.y="bottom"}}if(s.left<0){s.left=u.left;y.x=false}if(s.top<0){s.top=u.top;y.y=false}if(z.options.style.tip.corner!==false){s.corner=new String(A.corner);if(y.x!==false){s.corner=s.corner.replace(/Left|Right|Middle/,y.x)}if(y.y!==false){s.corner=s.corner.replace(/top|bottom/,y.y)}if(s.corner!==z.elements.tip.attr("rel")){e.call(z,s.corner)}}return s}function q(u,t){var v,s;v=f.extend(true,{},u);for(s in v){if(t===true&&s.search(/(tip|classes)/i)!==-1){delete v[s]}else{if(!t&&s.search(/(width|border|tip|title|classes|user)/i)!==-1){delete v[s]}}}return v}function c(s){if(typeof s.tip!=="object"){s.tip={corner:s.tip}}if(typeof s.tip.size!=="object"){s.tip.size={width:s.tip.size,height:s.tip.size}}if(typeof s.border!=="object"){s.border={width:s.border}}if(typeof s.width!=="object"){s.width={value:s.width}}if(typeof s.width.max=="string"){s.width.max=parseInt(s.width.max.replace(/([0-9]+)/i,"$1"))}if(typeof s.width.min=="string"){s.width.min=parseInt(s.width.min.replace(/([0-9]+)/i,"$1"))}if(typeof s.tip.size.x=="number"){s.tip.size.width=s.tip.size.x;delete s.tip.size.x}if(typeof s.tip.size.y=="number"){s.tip.size.height=s.tip.size.y;delete s.tip.size.y}return s}function a(){var s,t,u,x,v,w;s=this;u=[true,{}];for(t=0;t<arguments.length;t++){u.push(arguments[t])}x=[f.extend.apply(f,u)];while(typeof x[0].name=="string"){x.unshift(c(f.fn.qtip.styles[x[0].name]))}x.unshift(true,{classes:{tooltip:"qtip-"+(arguments[0].name||"defaults")}},f.fn.qtip.styles.defaults);v=f.extend.apply(f,x);w=(f.browser.msie)?1:0;v.tip.size.width+=w;v.tip.size.height+=w;if(v.tip.size.width%2>0){v.tip.size.width+=1}if(v.tip.size.height%2>0){v.tip.size.height+=1}if(v.tip.corner===true){v.tip.corner=(s.options.position.corner.tooltip==="center")?false:s.options.position.corner.tooltip}return v}function b(v,u,t){var s={bottomRight:[[0,0],[u,t],[u,0]],bottomLeft:[[0,0],[u,0],[0,t]],topRight:[[0,t],[u,0],[u,t]],topLeft:[[0,0],[0,t],[u,t]],topMiddle:[[0,t],[u/2,0],[u,t]],bottomMiddle:[[0,0],[u,0],[u/2,t]],rightMiddle:[[0,0],[u,t/2],[0,t]],leftMiddle:[[u,0],[u,t],[0,t/2]]};s.leftTop=s.bottomRight;s.rightTop=s.bottomLeft;s.leftBottom=s.topRight;s.rightBottom=s.topLeft;return s[v]}function g(s){var t;if(f("<canvas>").get(0).getContext){t={topLeft:[s,s],topRight:[0,s],bottomLeft:[s,0],bottomRight:[0,0]}}else{if(f.browser.msie){t={topLeft:[-90,90,0],topRight:[-90,90,-s],bottomLeft:[90,270,0],bottomRight:[90,270,-s]}}}return t}function k(){var s,t,u;s=this;u=s.getDimensions();t='<iframe class="qtip-bgiframe" frameborder="0" tabindex="-1" src="javascript:false" style="display:block; position:absolute; z-index:-1; filter:alpha(opacity=\'0\'); border: 1px solid red; height:'+u.height+"px; width:"+u.width+'px" />';s.elements.bgiframe=s.elements.wrapper.prepend(t).children(".qtip-bgiframe:first")}f(document).ready(function(){f.fn.qtip.cache={screen:{scroll:{left:f(window).scrollLeft(),top:f(window).scrollTop()},width:f(window).width(),height:f(window).height()}};var s;f(window).bind("resize scroll",function(t){clearTimeout(s);s=setTimeout(function(){if(t.type==="scroll"){f.fn.qtip.cache.screen.scroll={left:f(window).scrollLeft(),top:f(window).scrollTop()}}else{f.fn.qtip.cache.screen.width=f(window).width();f.fn.qtip.cache.screen.height=f(window).height()}for(i=0;i<f.fn.qtip.interfaces.length;i++){var u=f.fn.qtip.interfaces[i];if(u.status.rendered===true&&(u.options.position.type!=="static"||u.options.position.adjust.scroll&&t.type==="scroll"||u.options.position.adjust.resize&&t.type==="resize")){u.updatePosition(t,true)}}},100)});f(document).bind("mousedown.qtip",function(t){if(f(t.target).parents("div.qtip").length===0){f(".qtip[unfocus]").each(function(){var u=f(this).qtip("api");if(f(this).is(":visible")&&!u.status.disabled&&f(t.target).add(u.elements.target).length>1){u.hide(t)}})}})});f.fn.qtip.interfaces=[];f.fn.qtip.log={error:function(){return this}};f.fn.qtip.constants={};f.fn.qtip.defaults={content:{prerender:false,text:false,url:false,data:null,title:{text:false,button:false}},position:{target:false,corner:{target:"bottomRight",tooltip:"topLeft"},adjust:{x:0,y:0,mouse:true,screen:false,scroll:true,resize:true},type:"absolute",container:false},show:{when:{target:false,event:"mouseover"},effect:{type:"fade",length:100},delay:140,solo:false,ready:false},hide:{when:{target:false,event:"mouseout"},effect:{type:"fade",length:100},delay:0,fixed:false},api:{beforeRender:function(){},onRender:function(){},beforePositionUpdate:function(){},onPositionUpdate:function(){},beforeShow:function(){},onShow:function(){},beforeHide:function(){},onHide:function(){},beforeContentUpdate:function(){},onContentUpdate:function(){},beforeContentLoad:function(){},onContentLoad:function(){},beforeTitleUpdate:function(){},onTitleUpdate:function(){},beforeDestroy:function(){},onDestroy:function(){},beforeFocus:function(){},onFocus:function(){}}};f.fn.qtip.styles={defaults:{background:"white",color:"#111",overflow:"hidden",textAlign:"left",width:{min:0,max:250},padding:"5px 9px",border:{width:1,radius:0,color:"#d3d3d3"},tip:{corner:false,color:false,size:{width:13,height:13},opacity:1},title:{background:"#e1e1e1",fontWeight:"bold",padding:"7px 12px"},button:{cursor:"pointer"},classes:{target:"",tip:"qtip-tip",title:"qtip-title",button:"qtip-button",content:"qtip-content",active:"qtip-active"}},cream:{border:{width:3,radius:0,color:"#F9E98E"},title:{background:"#F0DE7D",color:"#A27D35"},background:"#FBF7AA",color:"#A27D35",classes:{tooltip:"qtip-cream"}},light:{border:{width:3,radius:0,color:"#E2E2E2"},title:{background:"#f1f1f1",color:"#454545"},background:"white",color:"#454545",classes:{tooltip:"qtip-light"}},dark:{border:{width:3,radius:0,color:"#303030"},title:{background:"#404040",color:"#f3f3f3"},background:"#505050",color:"#f3f3f3",classes:{tooltip:"qtip-dark"}},red:{border:{width:3,radius:0,color:"#CE6F6F"},title:{background:"#f28279",color:"#9C2F2F"},background:"#F79992",color:"#9C2F2F",classes:{tooltip:"qtip-red"}},green:{border:{width:3,radius:0,color:"#A9DB66"},title:{background:"#b9db8c",color:"#58792E"},background:"#CDE6AC",color:"#58792E",classes:{tooltip:"qtip-green"}},blue:{border:{width:3,radius:0,color:"#ADD9ED"},title:{background:"#D0E9F5",color:"#5E99BD"},background:"#E5F6FE",color:"#4D9FBF",classes:{tooltip:"qtip-blue"}}}})(jQuery);
/*
 *	lib/js/legacy/tiny_mce_33/jquery.tinymce.js
 */(function(b){var e,d,a=[],c=window;b.fn.tinymce=function(j){var p=this,g,k,h,m,i,l="",n="";if(!p.length){return p}if(!j){return tinyMCE.get(p[0].id)}function o(){var r=[],q=0;if(f){f();f=null}p.each(function(t,u){var s,w=u.id,v=j.oninit;if(!w){u.id=w=tinymce.DOM.uniqueId()}s=new tinymce.Editor(w,j);r.push(s);if(v){s.onInit.add(function(){var x,y=v;if(++q==r.length){if(tinymce.is(y,"string")){x=(y.indexOf(".")===-1)?null:tinymce.resolve(y.replace(/\.\w+$/,""));y=tinymce.resolve(y)}y.apply(x||tinymce,r)}})}});b.each(r,function(t,s){s.render()})}if(!c.tinymce&&!d&&(g=j.script_url)){d=1;h=g.substring(0,g.lastIndexOf("/"));if(/_(src|dev)\.js/g.test(g)){n="_src"}m=g.lastIndexOf("?");if(m!=-1){l=g.substring(m+1)}c.tinyMCEPreInit=c.tinyMCEPreInit||{base:h,suffix:n,query:l};if(g.indexOf("gzip")!=-1){i=j.language||"en";g=g+(/\?/.test(g)?"&":"?")+"js=true&core=true&suffix="+escape(n)+"&themes="+escape(j.theme)+"&plugins="+escape(j.plugins)+"&languages="+i;if(!c.tinyMCE_GZ){tinyMCE_GZ={start:function(){tinymce.suffix=n;function q(r){tinymce.ScriptLoader.markDone(tinyMCE.baseURI.toAbsolute(r))}q("langs/"+i+".js");q("themes/"+j.theme+"/editor_template"+n+".js");q("themes/"+j.theme+"/langs/"+i+".js");b.each(j.plugins.split(","),function(s,r){if(r){q("plugins/"+r+"/editor_plugin"+n+".js");q("plugins/"+r+"/langs/"+i+".js")}})},end:function(){}}}}b.ajax({type:"GET",url:g,dataType:"script",cache:true,success:function(){tinymce.dom.Event.domLoaded=1;d=2;if(j.script_loaded){j.script_loaded()}o();b.each(a,function(q,r){r()})}})}else{if(d===1){a.push(o)}else{o()}}return p};b.extend(b.expr[":"],{tinymce:function(g){return g.id&&!!tinyMCE.get(g.id)}});function f(){function i(l){if(l==="remove"){this.each(function(n,o){var m=h(o);if(m){m.remove()}})}this.find("span.mceEditor,div.mceEditor").each(function(n,o){var m=tinyMCE.get(o.id.replace(/_parent$/,""));if(m){m.remove()}})}function k(n){var m=this,l;if(n!==e){i.call(m);m.each(function(p,q){var o;if(o=tinyMCE.get(q.id)){o.setContent(n)}})}else{if(m.length>0){if(l=tinyMCE.get(m[0].id)){return l.getContent()}}}}function h(m){var l=null;(m)&&(m.id)&&(c.tinymce)&&(l=tinyMCE.get(m.id));return l}function g(l){return !!((l)&&(l.length)&&(c.tinymce)&&(l.is(":tinymce")))}var j={};b.each(["text","html","val"],function(n,l){var o=j[l]=b.fn[l],m=(l==="text");b.fn[l]=function(s){var p=this;if(!g(p)){return o.apply(p,arguments)}if(s!==e){k.call(p.filter(":tinymce"),s);o.apply(p.not(":tinymce"),arguments);return p}else{var r="";var q=arguments;(m?p:p.eq(0)).each(function(u,v){var t=h(v);r+=t?(m?t.getContent().replace(/<(?:"[^"]*"|'[^']*'|[^'">])*>/g,""):t.getContent()):o.apply(b(v),q)});return r}}});b.each(["append","prepend"],function(n,m){var o=j[m]=b.fn[m],l=(m==="prepend");b.fn[m]=function(q){var p=this;if(!g(p)){return o.apply(p,arguments)}if(q!==e){p.filter(":tinymce").each(function(s,t){var r=h(t);r&&r.setContent(l?q+r.getContent():r.getContent()+q)});o.apply(p.not(":tinymce"),arguments);return p}}});b.each(["remove","replaceWith","replaceAll","empty"],function(m,l){var n=j[l]=b.fn[l];b.fn[l]=function(){i.call(this,l);return n.apply(this,arguments)}});j.attr=b.fn.attr;b.fn.attr=function(n,q,o){var m=this;if((!n)||(n!=="value")||(!g(m))){return j.attr.call(m,n,q,o)}if(q!==e){k.call(m.filter(":tinymce"),q);j.attr.call(m.not(":tinymce"),n,q,o);return m}else{var p=m[0],l=h(p);return l?l.getContent():j.attr.call(b(p),n,q,o)}}}})(jQuery);
/*
 *	lib/js/lib/bootstrap.min.js
 */!function(a){a(function(){"use strict",a.support.transition=function(){var b=document.body||document.documentElement,c=b.style,d=c.transition!==undefined||c.WebkitTransition!==undefined||c.MozTransition!==undefined||c.MsTransition!==undefined||c.OTransition!==undefined;return d&&{end:function(){var b="TransitionEnd";return a.browser.webkit?b="webkitTransitionEnd":a.browser.mozilla?b="transitionend":a.browser.opera&&(b="oTransitionEnd"),b}()}}()})}(window.jQuery),!function(a){"use strict";var b='[data-dismiss="alert"]',c=function(c){a(c).on("click",b,this.close)};c.prototype={constructor:c,close:function(b){function f(){e.remove(),e.trigger("closed")}var c=a(this),d=c.attr("data-target"),e;d||(d=c.attr("href"),d=d&&d.replace(/.*(?=#[^\s]*$)/,"")),e=a(d),e.trigger("close"),b&&b.preventDefault(),e.length||(e=c.hasClass("alert")?c:c.parent()),e.removeClass("in"),a.support.transition&&e.hasClass("fade")?e.on(a.support.transition.end,f):f()}},a.fn.alert=function(b){return this.each(function(){var d=a(this),e=d.data("alert");e||d.data("alert",e=new c(this)),typeof b=="string"&&e[b].call(d)})},a.fn.alert.Constructor=c,a(function(){a("body").on("click.alert.data-api",b,c.prototype.close)})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.button.defaults,c)};b.prototype={constructor:b,setState:function(a){var b="disabled",c=this.$element,d=c.data(),e=c.is("input")?"val":"html";a+="Text",d.resetText||c.data("resetText",c[e]()),c[e](d[a]||this.options[a]),setTimeout(function(){a=="loadingText"?c.addClass(b).attr(b,b):c.removeClass(b).removeAttr(b)},0)},toggle:function(){var a=this.$element.parent('[data-toggle="buttons-radio"]');a&&a.find(".active").removeClass("active"),this.$element.toggleClass("active")}},a.fn.button=function(c){return this.each(function(){var d=a(this),e=d.data("button"),f=typeof c=="object"&&c;e||d.data("button",e=new b(this,f)),c=="toggle"?e.toggle():c&&e.setState(c)})},a.fn.button.defaults={loadingText:"loading..."},a.fn.button.Constructor=b,a(function(){a("body").on("click.button.data-api","[data-toggle^=button]",function(b){a(b.target).button("toggle")})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.carousel.defaults,c),this.options.slide&&this.slide(this.options.slide)};b.prototype={cycle:function(){return this.interval=setInterval(a.proxy(this.next,this),this.options.interval),this},to:function(b){var c=this.$element.find(".active"),d=c.parent().children(),e=d.index(c),f=this;if(b>d.length-1||b<0)return;return this.sliding?this.$element.one("slid",function(){f.to(b)}):e==b?this.pause().cycle():this.slide(b>e?"next":"prev",a(d[b]))},pause:function(){return clearInterval(this.interval),this},next:function(){if(this.sliding)return;return this.slide("next")},prev:function(){if(this.sliding)return;return this.slide("prev")},slide:function(b,c){var d=this.$element.find(".active"),e=c||d[b](),f=this.interval,g=b=="next"?"left":"right",h=b=="next"?"first":"last",i=this;return this.sliding=!0,f&&this.pause(),e=e.length?e:this.$element.find(".item")[h](),!a.support.transition&&this.$element.hasClass("slide")?(this.$element.trigger("slide"),d.removeClass("active"),e.addClass("active"),this.sliding=!1,this.$element.trigger("slid")):(e.addClass(b),e[0].offsetWidth,d.addClass(g),e.addClass(g),this.$element.trigger("slide"),this.$element.one(a.support.transition.end,function(){e.removeClass([b,g].join(" ")).addClass("active"),d.removeClass(["active",g].join(" ")),i.sliding=!1,setTimeout(function(){i.$element.trigger("slid")},0)})),f&&this.cycle(),this}},a.fn.carousel=function(c){return this.each(function(){var d=a(this),e=d.data("carousel"),f=typeof c=="object"&&c;e||d.data("carousel",e=new b(this,f)),typeof c=="number"?e.to(c):typeof c=="string"||(c=f.slide)?e[c]():e.cycle()})},a.fn.carousel.defaults={interval:5e3},a.fn.carousel.Constructor=b,a(function(){a("body").on("click.carousel.data-api","[data-slide]",function(b){var c=a(this),d,e=a(c.attr("data-target")||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,"")),f=!e.data("modal")&&a.extend({},e.data(),c.data());e.carousel(f),b.preventDefault()})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.collapse.defaults,c),this.options.parent&&(this.$parent=a(this.options.parent)),this.options.toggle&&this.toggle()};b.prototype={constructor:b,dimension:function(){var a=this.$element.hasClass("width");return a?"width":"height"},show:function(){var b=this.dimension(),c=a.camelCase(["scroll",b].join("-")),d=this.$parent&&this.$parent.find(".in"),e;d&&d.length&&(e=d.data("collapse"),d.collapse("hide"),e||d.data("collapse",null)),this.$element[b](0),this.transition("addClass","show","shown"),this.$element[b](this.$element[0][c])},hide:function(){var a=this.dimension();this.reset(this.$element[a]()),this.transition("removeClass","hide","hidden"),this.$element[a](0)},reset:function(a){var b=this.dimension();this.$element.removeClass("collapse")[b](a||"auto")[0].offsetWidth,this.$element.addClass("collapse")},transition:function(b,c,d){var e=this,f=function(){c=="show"&&e.reset(),e.$element.trigger(d)};this.$element.trigger(c)[b]("in"),a.support.transition&&this.$element.hasClass("collapse")?this.$element.one(a.support.transition.end,f):f()},toggle:function(){this[this.$element.hasClass("in")?"hide":"show"]()}},a.fn.collapse=function(c){return this.each(function(){var d=a(this),e=d.data("collapse"),f=typeof c=="object"&&c;e||d.data("collapse",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.collapse.defaults={toggle:!0},a.fn.collapse.Constructor=b,a(function(){a("body").on("click.collapse.data-api","[data-toggle=collapse]",function(b){var c=a(this),d,e=c.attr("data-target")||b.preventDefault()||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,""),f=a(e).data("collapse")?"toggle":c.data();a(e).collapse(f)})})}(window.jQuery),!function(a){function d(){a(b).parent().removeClass("open")}"use strict";var b='[data-toggle="dropdown"]',c=function(b){var c=a(b).on("click.dropdown.data-api",this.toggle);a("html").on("click.dropdown.data-api",function(){c.parent().removeClass("open")})};c.prototype={constructor:c,toggle:function(b){var c=a(this),e=c.attr("data-target"),f,g;return e||(e=c.attr("href"),e=e&&e.replace(/.*(?=#[^\s]*$)/,"")),f=a(e),f.length||(f=c.parent()),g=f.hasClass("open"),d(),!g&&f.toggleClass("open"),!1}},a.fn.dropdown=function(b){return this.each(function(){var d=a(this),e=d.data("dropdown");e||d.data("dropdown",e=new c(this)),typeof b=="string"&&e[b].call(d)})},a.fn.dropdown.Constructor=c,a(function(){a("html").on("click.dropdown.data-api",d),a("body").on("click.dropdown.data-api",b,c.prototype.toggle)})}(window.jQuery),!function(a){function c(){var b=this,c=setTimeout(function(){b.$element.off(a.support.transition.end),d.call(b)},500);this.$element.one(a.support.transition.end,function(){clearTimeout(c),d.call(b)})}function d(a){this.$element.hide().trigger("hidden"),e.call(this)}function e(b){var c=this,d=this.$element.hasClass("fade")?"fade":"";if(this.isShown&&this.options.backdrop){var e=a.support.transition&&d;this.$backdrop=a('<div class="modal-backdrop '+d+'" />').appendTo(document.body),this.options.backdrop!="static"&&this.$backdrop.click(a.proxy(this.hide,this)),e&&this.$backdrop[0].offsetWidth,this.$backdrop.addClass("in"),e?this.$backdrop.one(a.support.transition.end,b):b()}else!this.isShown&&this.$backdrop?(this.$backdrop.removeClass("in"),a.support.transition&&this.$element.hasClass("fade")?this.$backdrop.one(a.support.transition.end,a.proxy(f,this)):f.call(this)):b&&b()}function f(){this.$backdrop.remove(),this.$backdrop=null}function g(){var b=this;this.isShown&&this.options.keyboard?a(document).on("keyup.dismiss.modal",function(a){a.which==27&&b.hide()}):this.isShown||a(document).off("keyup.dismiss.modal")}"use strict";var b=function(b,c){this.options=a.extend({},a.fn.modal.defaults,c),this.$element=a(b).delegate('[data-dismiss="modal"]',"click.dismiss.modal",a.proxy(this.hide,this))};b.prototype={constructor:b,toggle:function(){return this[this.isShown?"hide":"show"]()},show:function(){var b=this;if(this.isShown)return;a("body").addClass("modal-open"),this.isShown=!0,this.$element.trigger("show"),g.call(this),e.call(this,function(){var c=a.support.transition&&b.$element.hasClass("fade");!b.$element.parent().length&&b.$element.appendTo(document.body),b.$element.show(),c&&b.$element[0].offsetWidth,b.$element.addClass("in"),c?b.$element.one(a.support.transition.end,function(){b.$element.trigger("shown")}):b.$element.trigger("shown")})},hide:function(b){b&&b.preventDefault();if(!this.isShown)return;var e=this;this.isShown=!1,a("body").removeClass("modal-open"),g.call(this),this.$element.trigger("hide").removeClass("in"),a.support.transition&&this.$element.hasClass("fade")?c.call(this):d.call(this)}},a.fn.modal=function(c){return this.each(function(){var d=a(this),e=d.data("modal"),f=typeof c=="object"&&c;e||d.data("modal",e=new b(this,f)),typeof c=="string"?e[c]():e.show()})},a.fn.modal.defaults={backdrop:!0,keyboard:!0},a.fn.modal.Constructor=b,a(function(){a("body").on("click.modal.data-api",'[data-toggle="modal"]',function(b){var c=a(this),d,e=a(c.attr("data-target")||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,"")),f=e.data("modal")?"toggle":a.extend({},e.data(),c.data());b.preventDefault(),e.modal(f)})})}(window.jQuery),!function(a){"use strict";var b=function(a,b){this.init("tooltip",a,b)};b.prototype={constructor:b,init:function(b,c,d){var e,f;this.type=b,this.$element=a(c),this.options=this.getOptions(d),this.enabled=!0,this.options.trigger!="manual"&&(e=this.options.trigger=="hover"?"mouseenter":"focus",f=this.options.trigger=="hover"?"mouseleave":"blur",this.$element.on(e,this.options.selector,a.proxy(this.enter,this)),this.$element.on(f,this.options.selector,a.proxy(this.leave,this))),this.options.selector?this._options=a.extend({},this.options,{trigger:"manual",selector:""}):this.fixTitle()},getOptions:function(b){return b=a.extend({},a.fn[this.type].defaults,b,this.$element.data()),b.delay&&typeof b.delay=="number"&&(b.delay={show:b.delay,hide:b.delay}),b},enter:function(b){var c=a(b.currentTarget)[this.type](this._options).data(this.type);!c.options.delay||!c.options.delay.show?c.show():(c.hoverState="in",setTimeout(function(){c.hoverState=="in"&&c.show()},c.options.delay.show))},leave:function(b){var c=a(b.currentTarget)[this.type](this._options).data(this.type);!c.options.delay||!c.options.delay.hide?c.hide():(c.hoverState="out",setTimeout(function(){c.hoverState=="out"&&c.hide()},c.options.delay.hide))},show:function(){var a,b,c,d,e,f,g;if(this.hasContent()&&this.enabled){a=this.tip(),this.setContent(),this.options.animation&&a.addClass("fade"),f=typeof this.options.placement=="function"?this.options.placement.call(this,a[0],this.$element[0]):this.options.placement,b=/in/.test(f),a.remove().css({top:0,left:0,display:"block"}).appendTo(b?this.$element:document.body),c=this.getPosition(b),d=a[0].offsetWidth,e=a[0].offsetHeight;switch(b?f.split(" ")[1]:f){case"bottom":g={top:c.top+c.height,left:c.left+c.width/2-d/2};break;case"top":g={top:c.top-e,left:c.left+c.width/2-d/2};break;case"left":g={top:c.top+c.height/2-e/2,left:c.left-d};break;case"right":g={top:c.top+c.height/2-e/2,left:c.left+c.width}}a.css(g).addClass(f).addClass("in")}},setContent:function(){var a=this.tip();a.find(".tooltip-inner").html(this.getTitle()),a.removeClass("fade in top bottom left right")},hide:function(){function d(){var b=setTimeout(function(){c.off(a.support.transition.end).remove()},500);c.one(a.support.transition.end,function(){clearTimeout(b),c.remove()})}var b=this,c=this.tip();c.removeClass("in"),a.support.transition&&this.$tip.hasClass("fade")?d():c.remove()},fixTitle:function(){var a=this.$element;(a.attr("title")||typeof a.attr("data-original-title")!="string")&&a.attr("data-original-title",a.attr("title")||"").removeAttr("title")},hasContent:function(){return this.getTitle()},getPosition:function(b){return a.extend({},b?{top:0,left:0}:this.$element.offset(),{width:this.$element[0].offsetWidth,height:this.$element[0].offsetHeight})},getTitle:function(){var a,b=this.$element,c=this.options;return a=b.attr("data-original-title")||(typeof c.title=="function"?c.title.call(b[0]):c.title),a=a.toString().replace(/(^\s*|\s*$)/,""),a},tip:function(){return this.$tip=this.$tip||a(this.options.template)},validate:function(){this.$element[0].parentNode||(this.hide(),this.$element=null,this.options=null)},enable:function(){this.enabled=!0},disable:function(){this.enabled=!1},toggleEnabled:function(){this.enabled=!this.enabled},toggle:function(){this[this.tip().hasClass("in")?"hide":"show"]()}},a.fn.tooltip=function(c){return this.each(function(){var d=a(this),e=d.data("tooltip"),f=typeof c=="object"&&c;e||d.data("tooltip",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.tooltip.Constructor=b,a.fn.tooltip.defaults={animation:!0,delay:0,selector:!1,placement:"top",trigger:"hover",title:"",template:'<div class="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'}}(window.jQuery),!function(a){"use strict";var b=function(a,b){this.init("popover",a,b)};b.prototype=a.extend({},a.fn.tooltip.Constructor.prototype,{constructor:b,setContent:function(){var b=this.tip(),c=this.getTitle(),d=this.getContent();b.find(".popover-title")[a.type(c)=="object"?"append":"html"](c),b.find(".popover-content > *")[a.type(d)=="object"?"append":"html"](d),b.removeClass("fade top bottom left right in")},hasContent:function(){return this.getTitle()||this.getContent()},getContent:function(){var a,b=this.$element,c=this.options;return a=b.attr("data-content")||(typeof c.content=="function"?c.content.call(b[0]):c.content),a=a.toString().replace(/(^\s*|\s*$)/,""),a},tip:function(){return this.$tip||(this.$tip=a(this.options.template)),this.$tip}}),a.fn.popover=function(c){return this.each(function(){var d=a(this),e=d.data("popover"),f=typeof c=="object"&&c;e||d.data("popover",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.popover.Constructor=b,a.fn.popover.defaults=a.extend({},a.fn.tooltip.defaults,{placement:"right",content:"",template:'<div class="popover"><div class="arrow"></div><div class="popover-inner"><h3 class="popover-title"></h3><div class="popover-content"><p></p></div></div></div>'})}(window.jQuery),!function(a){function b(b,c){var d=a.proxy(this.process,this),e=a(b).is("body")?a(window):a(b),f;this.options=a.extend({},a.fn.scrollspy.defaults,c),this.$scrollElement=e.on("scroll.scroll.data-api",d),this.selector=(this.options.target||(f=a(b).attr("href"))&&f.replace(/.*(?=#[^\s]+$)/,"")||"")+" .nav li > a",this.$body=a("body").on("click.scroll.data-api",this.selector,d),this.refresh(),this.process()}"use strict",b.prototype={constructor:b,refresh:function(){this.targets=this.$body.find(this.selector).map(function(){var b=a(this).attr("href");return/^#\w/.test(b)&&a(b).length?b:null}),this.offsets=a.map(this.targets,function(b){return a(b).position().top})},process:function(){var a=this.$scrollElement.scrollTop()+this.options.offset,b=this.offsets,c=this.targets,d=this.activeTarget,e;for(e=b.length;e--;)d!=c[e]&&a>=b[e]&&(!b[e+1]||a<=b[e+1])&&this.activate(c[e])},activate:function(a){var b;this.activeTarget=a,this.$body.find(this.selector).parent(".active").removeClass("active"),b=this.$body.find(this.selector+'[href="'+a+'"]').parent("li").addClass("active"),b.parent(".dropdown-menu")&&b.closest("li.dropdown").addClass("active")}},a.fn.scrollspy=function(c){return this.each(function(){var d=a(this),e=d.data("scrollspy"),f=typeof c=="object"&&c;e||d.data("scrollspy",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.scrollspy.Constructor=b,a.fn.scrollspy.defaults={offset:10},a(function(){a('[data-spy="scroll"]').each(function(){var b=a(this);b.scrollspy(b.data())})})}(window.jQuery),!function(a){"use strict";var b=function(b){this.element=a(b)};b.prototype={constructor:b,show:function(){var b=this.element,c=b.closest("ul:not(.dropdown-menu)"),d=b.attr("data-target"),e,f;d||(d=b.attr("href"),d=d&&d.replace(/.*(?=#[^\s]*$)/,""));if(b.parent("li").hasClass("active"))return;e=c.find(".active a").last()[0],b.trigger({type:"show",relatedTarget:e}),f=a(d),this.activate(b.parent("li"),c),this.activate(f,f.parent(),function(){b.trigger({type:"shown",relatedTarget:e})})},activate:function(b,c,d){function g(){e.removeClass("active").find("> .dropdown-menu > .active").removeClass("active"),b.addClass("active"),f?(b[0].offsetWidth,b.addClass("in")):b.removeClass("fade"),b.parent(".dropdown-menu")&&b.closest("li.dropdown").addClass("active"),d&&d()}var e=c.find("> .active"),f=d&&a.support.transition&&e.hasClass("fade");f?e.one(a.support.transition.end,g):g(),e.removeClass("in")}},a.fn.tab=function(c){return this.each(function(){var d=a(this),e=d.data("tab");e||d.data("tab",e=new b(this)),typeof c=="string"&&e[c]()})},a.fn.tab.Constructor=b,a(function(){a("body").on("click.tab.data-api",'[data-toggle="tab"], [data-toggle="pill"]',function(b){b.preventDefault(),a(this).tab("show")})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.typeahead.defaults,c),this.matcher=this.options.matcher||this.matcher,this.sorter=this.options.sorter||this.sorter,this.highlighter=this.options.highlighter||this.highlighter,this.$menu=a(this.options.menu).appendTo("body"),this.source=this.options.source,this.shown=!1,this.listen()};b.prototype={constructor:b,select:function(){var a=this.$menu.find(".active").attr("data-value");return this.$element.val(a),this.hide()},show:function(){var b=a.extend({},this.$element.offset(),{height:this.$element[0].offsetHeight});return this.$menu.css({top:b.top+b.height,left:b.left}),this.$menu.show(),this.shown=!0,this},hide:function(){return this.$menu.hide(),this.shown=!1,this},lookup:function(b){var c=this,d,e;return this.query=this.$element.val(),this.query?(d=a.grep(this.source,function(a){if(c.matcher(a))return a}),d=this.sorter(d),d.length?this.render(d.slice(0,this.options.items)).show():this.shown?this.hide():this):this.shown?this.hide():this},matcher:function(a){return~a.toLowerCase().indexOf(this.query.toLowerCase())},sorter:function(a){var b=[],c=[],d=[],e;while(e=a.shift())e.toLowerCase().indexOf(this.query.toLowerCase())?~e.indexOf(this.query)?c.push(e):d.push(e):b.push(e);return b.concat(c,d)},highlighter:function(a){return a.replace(new RegExp("("+this.query+")","ig"),function(a,b){return"<strong>"+b+"</strong>"})},render:function(b){var c=this;return b=a(b).map(function(b,d){return b=a(c.options.item).attr("data-value",d),b.find("a").html(c.highlighter(d)),b[0]}),b.first().addClass("active"),this.$menu.html(b),this},next:function(b){var c=this.$menu.find(".active").removeClass("active"),d=c.next();d.length||(d=a(this.$menu.find("li")[0])),d.addClass("active")},prev:function(a){var b=this.$menu.find(".active").removeClass("active"),c=b.prev();c.length||(c=this.$menu.find("li").last()),c.addClass("active")},listen:function(){this.$element.on("blur",a.proxy(this.blur,this)).on("keypress",a.proxy(this.keypress,this)).on("keyup",a.proxy(this.keyup,this)),(a.browser.webkit||a.browser.msie)&&this.$element.on("keydown",a.proxy(this.keypress,this)),this.$menu.on("click",a.proxy(this.click,this)).on("mouseenter","li",a.proxy(this.mouseenter,this))},keyup:function(a){a.stopPropagation(),a.preventDefault();switch(a.keyCode){case 40:case 38:break;case 9:case 13:if(!this.shown)return;this.select();break;case 27:this.hide();break;default:this.lookup()}},keypress:function(a){a.stopPropagation();if(!this.shown)return;switch(a.keyCode){case 9:case 13:case 27:a.preventDefault();break;case 38:a.preventDefault(),this.prev();break;case 40:a.preventDefault(),this.next()}},blur:function(a){var b=this;a.stopPropagation(),a.preventDefault(),setTimeout(function(){b.hide()},150)},click:function(a){a.stopPropagation(),a.preventDefault(),this.select()},mouseenter:function(b){this.$menu.find(".active").removeClass("active"),a(b.currentTarget).addClass("active")}},a.fn.typeahead=function(c){return this.each(function(){var d=a(this),e=d.data("typeahead"),f=typeof c=="object"&&c;e||d.data("typeahead",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.typeahead.defaults={source:[],items:8,menu:'<ul class="typeahead dropdown-menu"></ul>',item:'<li><a href="#"></a></li>'},a.fn.typeahead.Constructor=b,a(function(){a("body").on("focus.typeahead.data-api",'[data-provide="typeahead"]',function(b){var c=a(this);if(c.data("typeahead"))return;b.preventDefault(),c.typeahead(c.data())})})}(window.jQuery);
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
wn.versions={check:function(){if(window.localStorage){if(window._version_number==-1||parseInt(localStorage._version_number)!=parseInt(window._version_number)){var localversion=localStorage._version_number;localStorage.clear();console.log("Cache cleared - version: "+localversion
+' to '+_version_number)}
localStorage.setItem('_version_number',window._version_number);}}}
/*
 *	lib/js/wn/assets.js
 */
wn.assets={executed_:{},exists:function(src){if('localStorage'in window&&localStorage.getItem(src))
return true},add:function(src,txt){if('localStorage'in window){localStorage.setItem(src,txt);}},get:function(src){return localStorage.getItem(src);},extn:function(src){if(src.indexOf('?')!=-1){src=src.split('?').slice(-1)[0];}
return src.split('.').slice(-1)[0];},load:function(src){var t=src;$.ajax({url:t,data:{q:Math.floor(Math.random()*1000)},dataType:'text',success:function(txt){wn.assets.add(src,txt);},async:false})},execute:function(src){if(!wn.assets.exists(src)){wn.assets.load(src);}
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
wn.get_cookie=function(c){var t=""+document.cookie;var ind=t.indexOf(c);if(ind==-1||c=="")return"";var ind1=t.indexOf(';',ind);if(ind1==-1)ind1=t.length;return unescape(t.substring(ind+c.length+1,ind1));}
/*
 *	lib/js/wn/model.js
 */
wn.provide('wn.model');wn.model.no_value_type=['Section Break','Column Break','HTML','Table','Button','Image'];
/*
 *	lib/js/wn/page.js
 */
wn.page={set:function(src){var new_selection=$('.inner div.content[_src="'+src+'"]');if(!new_selection.length){wn.assets.execute(src);new_selection=$('.inner div.content[_src="'+src+'"]');}
$('.inner .current_page').removeClass('current_page');new_selection.addClass('current_page');var title=$('nav ul li a[href*="'+src+'"]').attr('title')||'No Title'
state=window.location.hash;if(state!=src){window.location.hash=state;}
else{document.title=title;}}}
/*
 *	lib/js/wn/misc/user.js
 */
wn.user_info=function(uid){var def={'fullname':uid,'image':'lib/images/ui/no_img_m.gif'}
if(!wn.boot.user_info)return def
if(!wn.boot.user_info[uid])return def
if(!wn.boot.user_info[uid].fullname)
wn.boot.user_info[uid].fullname=uid;if(!wn.boot.user_info[uid].image)
wn.boot.user_info[uid].image=def.image;return wn.boot.user_info[uid];}
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
 *	lib/js/wn/request.js
 */
wn.provide('wn.request');wn.request.url='index.cgi';wn.request.prepare=function(opts){if(opts.btn)$(opts.btn).set_working();if(opts.show_spinner)set_loading();if(opts.freeze)freeze();if(!opts.args.cmd){console.log(opts)
throw"Incomplete Request";}}
wn.request.cleanup=function(opts,r){if(opts.btn)$(opts.btn).done_working();if(opts.show_spinner)hide_loading();if(opts.freeze)unfreeze();if(wn.boot.sid&&wn.get_cookie('sid')!=wn.boot.sid){msgprint('Session expired');setTimeout('redirect_to_login()',3000);return;}
if(r.server_messages)msgprint(r.server_messages)
if(r.exc){errprint(r.exc);console.log(r.exc);};if(r.docs)LocalDB.sync(r.docs);}
wn.request.call=function(opts){wn.request.prepare(opts);$.ajax({url:opts.url||wn.request.url,data:opts.args,type:opts.type||'POST',dataType:opts.dataType||'json',success:function(r,xhr){wn.request.cleanup(opts,r);opts.success(r,xhr.responseText);},error:function(xhr,textStatus){wn.request.cleanup(opts,{});msgprint('Unable to complete request: '+textStatus)
if(opts.error)opts.error(xhr)}})}
wn.call=function(opts){var args=opts.args||{};if(opts.module&&opts.page){args.cmd=module+'.page.'+page+'.'+page+'.'+method}else if(opts.method){args.cmd=opts.method;}
wn.request.call({args:args,success:opts.callback,error:opts.error,btn:opts.btn,freeze:opts.freeze,show_spinner:!opts.no_spinner});}
/*
 *	lib/js/core.js
 */
if(!console){var console={log:function(txt){errprint(txt);}}}
wn.versions.check();$(document).bind('ready',function(){var base=window.location.href.split('#')[0];$.each($('a[softlink!="false"]'),function(i,v){if(v.href.substr(0,base.length)==base){var path=(v.href.substr(base.length));if(path.substr(0,1)!='#'){v.href=base+'#'+path;}}});if(!wn.settings.no_history&&window.location.hash){wn.page.set(window.location.hash.substr(1));}});
/*
 *	lib/js/legacy/globals.js
 */
wn.provide('wn.widgets.form');wn.provide('wn.widgets.report');wn.provide('wn.utils');wn.provide('wn.model');wn.provide('wn.profile');wn.provide('wn.session');wn.provide('_f');wn.provide('_p');wn.provide('_r');wn.provide('_c');wn.provide('_e');wn.provide('_startup_data')
wn.settings.no_history=1;var NEWLINE='\n';var login_file='';var version='v170';var profile=null;var session={};var is_testing=false;var user=null;var user_defaults=null;var user_roles=null;var user_fullname=null;var user_email=null;var user_img={};var home_page=null;var hide_autosuggest=null;var page_body=null;var pscript={};var selector=null;var top_index=91;var _f={};var _p={};var _e={};var _r={};var FILTER_SEP='\1';var frms={};var cur_frm=null;var pscript={};var validated=true;var validation_message='';var tinymce_loaded=null;var cur_autosug=null;
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
function nth(number){number=cint(number);var s='th';if((number+'').substr(-1)=='1')s='st';if((number+'').substr(-1)=='2')s='nd';if((number+'').substr(-1)=='3')s='rd';return number+s;}
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
function docstring(obj){return JSON.stringify(obj);}
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
 *	lib/js/legacy/utils/datetime.js
 */
function same_day(d1,d2){if(d1.getFullYear()==d2.getFullYear()&&d1.getMonth()==d2.getMonth()&&d1.getDate()==d2.getDate())return true;else return false;}
var month_list=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];var month_last={1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
var month_list_full=['January','February','March','April','May','June','July','August','September','October','November','December'];var week_list=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];var week_list_full=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];function int_to_str(i,len){i=''+i;if(i.length<len)for(c=0;c<(len-i.length);c++)i='0'+i;return i}
wn.datetime={str_to_obj:function(d){if(!d)return new Date();var tm=[null,null];if(d.search(' ')!=-1){var tm=d.split(' ')[1].split(':');var d=d.split(' ')[0];}
if(d.search('-')!=-1){var t=d.split('-');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else if(d.search('/')!=-1){var t=d.split('/');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else{return new Date();}},obj_to_str:function(d){return d.getFullYear()+'-'+int_to_str(d.getMonth()+1,2)+'-'+int_to_str(d.getDate(),2);},obj_to_user:function(d){return dateutil.str_to_user(dateutil.obj_to_str(d));},get_diff:function(d1,d2){return((d1-d2)/86400000);},get_day_diff:function(d1,d2){return dateutil.get_diff(new Date(d1.getYear(),d1.getMonth(),d1.getDate(),0,0),new Date(d2.getYear(),d2.getMonth(),d2.getDate(),0,0))},add_days:function(d,days){d.setTime(d.getTime()+(days*24*60*60*1000));return d},add_months:function(d,months){dt=dateutil.str_to_obj(d)
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
else if(user_fmt=='mm-dd-yyyy'){var d=d.split('-');return d[2]+'-'+d[0]+'-'+d[1];}},global_date_format:function(d){if(d.substr)d=this.str_to_obj(d);return nth(d.getDate())+' '+month_list_full[d.getMonth()]+' '+d.getFullYear();},get_today:function(){var today=new Date();var m=(today.getMonth()+1)+'';if(m.length==1)m='0'+m;var d=today.getDate()+'';if(d.length==1)d='0'+d;return today.getFullYear()+'-'+m+'-'+d;},get_cur_time:function(){var d=new Date();var hh=d.getHours()+''
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
wn.dom.set_unique_id=function(ele){var id='unique-'+wn.dom.id_count;ele.setAttribute('id',id);wn.dom.id_count++;return id;}
wn.tinymce={add_simple:function(ele,height){if(ele.myid){tinyMCE.execCommand('mceAddControl',true,ele.myid);return;}
ele.myid=wn.dom.set_unique_id(ele);$(ele).tinymce({script_url:'lib/js/legacy/tiny_mce_33/tiny_mce.js',height:height?height:'200px',theme:"advanced",theme_advanced_buttons1:"bold,italic,underline,separator,strikethrough,justifyleft,justifycenter,justifyright,justifyfull,bullist,numlist,outdent,indent,link,unlink,forecolor,backcolor,code,",theme_advanced_buttons2:"",theme_advanced_buttons3:"",theme_advanced_toolbar_location:"top",theme_advanced_toolbar_align:"left",theme_advanced_path:false,theme_advanced_resizing:false});},remove:function(ele){tinyMCE.execCommand('mceRemoveControl',true,ele.myid);},get_value:function(ele){return tinymce.get(ele.myid).getContent();}}
wn.ele={link:function(args){var span=$a(args.parent,'span','link_type',args.style);span.loading_img=$a(args.parent,'img','',{margin:'0px 4px -2px 4px',display:'none'});span.loading_img.src='lib/images/ui/button-load.gif';span.innerHTML=args.label;span.user_onclick=args.onclick;span.onclick=function(){if(!this.disabled)this.user_onclick(this);}
span.set_working=function(){this.disabled=1;$di(this.loading_img);}
span.done_working=function(){this.disabled=0;$dh(this.loading_img);}
return span;}}
function $ln(parent,label,onclick,style){return wn.ele.link({parent:parent,label:label,onclick:onclick,style:style})}
function $btn(parent,label,onclick,style,css_class,is_ajax){wn.require('lib/js/wn/ui/button.js');if(css_class==='green')css_class='btn-info';return new wn.ui.Button({parent:parent,label:label,onclick:onclick,style:style,is_ajax:is_ajax,css_class:css_class}).btn;}
$item_normal=function(ele){$y(ele,{padding:'6px 8px',cursor:'pointer',marginRight:'8px',whiteSpace:'nowrap',overflow:'hidden',borderBottom:'1px solid #DDD'});$bg(ele,'#FFF');$fg(ele,'#000');}
$item_active=function(ele){$bg(ele,'#FE8');$fg(ele,'#000');}
$item_selected=function(ele){$bg(ele,'#777');$fg(ele,'#FFF');}
$item_pressed=function(ele){$bg(ele,'#F90');$fg(ele,'#FFF');};(function($){$.fn.set_working=function(){var ele=this.get(0);if(ele.loading_img){$di(ele.loading_img)}else{ele.disabled=1;ele.loading_img=$a(ele.parentNode,'img','',{marginLeft:'4px',marginBottom:'-2px',display:'inline'});ele.loading_img.src='lib/images/ui/button-load.gif';}}
$.fn.done_working=function(){var ele=this.get(0);ele.disabled=0;if(ele.loading_img){$dh(ele.loading_img)};}})(jQuery);function set_opacity(ele,ieop){var op=ieop/100;if(ele.filters){try{ele.filters.item("DXImageTransform.Microsoft.Alpha").opacity=ieop;}catch(e){ele.style.filter='progid:DXImageTransform.Microsoft.Alpha(opacity='+ieop+')';}}else{ele.style.opacity=op;}}
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
wn.urllib={get_arg:function(name){name=name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");var regexS="[\\?&]"+name+"=([^&#]*)";var regex=new RegExp(regexS);var results=regex.exec(window.location.href);if(results==null)
return"";else
return decodeURIComponent(results[1]);},get_dict:function(){var d={}
var t=window.location.href.split('?')[1];if(!t)return d;if(t.indexOf('#')!=-1)t=t.split('#')[0];if(!t)return d;t=t.split('&');for(var i=0;i<t.length;i++){var a=t[i].split('=');d[decodeURIComponent(a[0])]=decodeURIComponent(a[1]);}
return d;},get_base_url:function(){var url=window.location.href.split('#')[0].split('?')[0].split('index.cgi')[0];if(url.substr(url.length-1,1)=='/')url=url.substr(0,url.length-1)
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
args.docs=compress_doclist(doclist);open_url_post(webnotes.request.url,args);}
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
var growl_area;function show_alert(txt,id){if(!growl_area){growl_area=$a(popup_cont,'div','',{position:'fixed',bottom:'8px',right:'8px',width:'320px',zIndex:10});}
var wrapper=$a(growl_area,'div','',{position:'relative'});var body=$a(wrapper,'div','notice');var c=$a(body,'i','icon-remove-sign',{cssFloat:'right',cursor:'pointer'});$(c).click(function(){$dh(this.wrapper)});c.wrapper=wrapper;var t=$a(body,'div','',{color:'#FFF'});$(t).html(txt);if(id){$(t).attr('id',id);}
$(wrapper).hide().fadeIn(1000);}
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
this.wrapper=document.createElement((this.with_label?'div':'span'));this.label_area=$a(this.wrapper,'div','',{margin:'8px 0px 2px 0px'});if(ischk&&!this.in_grid){this.input_area=$a(this.label_area,'span','',{marginRight:'4px'});this.disp_area=$a(this.label_area,'span','',{marginRight:'4px'});}
if(this.with_label){this.label_span=$a(this.label_area,'span','field_label')
this.label_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 4px'});$dh(this.label_icon);this.label_icon.src='lib/images/icons/error.gif';this.label_icon.title='Mandatory value needs to be entered';this.suggest_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 0px'});$dh(this.suggest_icon);this.suggest_icon.src='lib/images/icons/bullet_arrow_down.png';this.suggest_icon.title='With suggestions';}else{this.label_span=$a(this.label_area,'span','',{marginRight:'4px'})
$dh(this.label_area);}
if(!this.input_area){this.input_area=$a(this.wrapper,(this.with_label?'div':'span'));this.disp_area=$a(this.wrapper,(this.with_label?'div':'span'));}
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
return v;};var _link_onchange_flag=null;function LinkField(){}LinkField.prototype=new Field();LinkField.prototype.make_input=function(){var me=this;if(me.df.no_buttons){this.txt=$a(this.input_area,'input');this.input=this.txt;}else{makeinput_popup(this,'icon-search','icon-play','icon-plus');me.setup_buttons();me.onrefresh=function(){if(me.can_create&&cur_frm.doc.docstatus==0)
$(me.btn2).css('display','inline-block');else $dh(me.btn2);}}
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
f.refresh();if(df.fieldtype=='Button'&&!this.first_button){$(f.input).addClass('btn-info');this.first_button=true;}}}
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
 *	lib/js/legacy/widgets/listing.js
 */
list_opts={cell_style:{padding:'3px 2px'},alt_cell_style:{},head_style:{height:'20px',overflow:'hidden',verticalAlign:'middle',fontWeight:'bold',padding:'1px',fontSize:'13px'},head_main_style:{padding:'0px'},hide_export:1,hide_print:1,hide_refresh:0,hide_rec_label:0,show_calc:1,show_empty_tab:0,no_border:1,append_records:1,table_width:null};function Listing(head_text,no_index,no_loading){this.start=0;this.page_len=20;this.filters_per_line=7;this.cell_idx=0;this.head_text=head_text?head_text:'Result';this.keyword='records';this.no_index=no_index;this.underline=1;this.no_rec_message='No Result';this.show_cell=null;this.show_result=null;this.colnames=null;this.colwidths=null;this.coltypes=null;this.coloptions=null;this.filters={};this.sort_list={};this.sort_order_dict={};this.sort_heads={};this.is_std_query=false;this.server_call=null;this.no_loading=no_loading;this.opts=copy_dict(list_opts);}
Listing.prototype.make=function(parent){var me=this;this.wrapper=parent;this.filter_wrapper=$a(parent,'div','srs_filter_wrapper');this.filter_area=$a(this.filter_wrapper,'div','srs_filter_area');$dh(this.filter_wrapper);this.btn_area=$a(parent,'div','',{margin:'8px 0px'});this.body_area=$a(parent,'div','srs_body_area');if(!this.opts.hide_rec_label)
this.rec_label=$a(this.body_area,'div','',{margin:'4px 0px',color:'#888'});this.results=$a($a(this.body_area,'div','srs_results_area'),'div');this.fetching_area=$a(this.body_area,'div','',{height:'120px',background:'url("lib/images/ui/square_loading.gif") center no-repeat',display:'none'});this.show_no_records=$a(this.body_area,'div','',{margin:'200px 0px',textAlign:'center',fontSize:'14px',color:'#888',display:'none'});this.show_no_records.innerHTML='No Result';if(this.opts.show_empty_tab)
this.make_result_tab();this.bottom_div=$a(this.body_area,'div','',{paddingTop:'8px'});this.make_toolbar();}
Listing.prototype.make_toolbar=function(){var me=this;this.buttons={};var make_btn=function(label,icon,onclick,bold){var btn=$btn(me.btn_area,label,onclick,{marginRight:'4px'});if(bold)$y(btn,{fontWeight:'bold'});me.buttons[label]=btn;}
if(!this.opts.hide_refresh){make_btn('Refresh','ui-icon-refresh',function(btn){me.start=0;me.run();},1);}
if(this.opts.show_new){make_btn('New ','ui-icon-document',function(){new_doc(me.dt);},1);}
if(this.opts.show_report){make_btn('Report Builder','ui-icon-clipboard',function(){loadreport(me.dt,null,null,null,1);},0);}
if(!this.opts.hide_export){make_btn('Export','ui-icon-circle-arrow-e',function(){me.do_export();});}
if(!this.opts.hide_print){make_btn('Print','ui-icon-print',function(){me.do_print();});}
if(this.opts.show_calc){make_btn('Calc','ui-icon-calculator',function(){me.do_calc();});$dh(me.buttons['Calc'])}
this.loading_img=$a(this.btn_area,'img','',{display:'none',marginBottom:'-2px'});this.loading_img.src='lib/images/ui/button-load.gif';if(!keys(this.buttons).length)
$dh(this.btn_area);}
Listing.prototype.do_print=function(){this.build_query();if(!this.query){alert('No Query!');return;}
args={query:this.query,title:this.head_text,colnames:this.colnames,colwidths:this.colwidths,coltypes:this.coltypes,has_index:(this.no_index?0:1),has_headings:1,check_limit:1,is_simple:1}
wn.require('lib/js/legacy/widgets/print_query.js');_p.print_query=new _p.PrintQuery();_p.print_query.show_dialog(args);}
Listing.prototype.do_calc=function(){show_calc(this.result_tab,this.colnames,this.coltypes,0)}
Listing.prototype.add_filter=function(label,ftype,options,tname,fname,cond){if(!this.filter_area){alert('[Listing] make() must be called before add_filter');}
var me=this;if(!this.filter_set){var h=$a(this.filter_area,'div','',{fontSize:'14px',fontWeight:'bold',marginBottom:'4px'});h.innerHTML='Filter your search';this.filter_area.div=$a(this.filter_area,'div');this.perm=[[1,1],]
this.filters={};}
$ds(this.filter_wrapper);if((!this.inp_tab)||(this.cell_idx==this.filters_per_line)){this.inp_tab=$a(this.filter_area.div,'table','',{width:'100%',tableLayout:'fixed'});this.inp_tab.insertRow(0);for(var i=0;i<this.filters_per_line;i++){this.inp_tab.rows[0].insertCell(i);}
this.cell_idx=0;}
var c=this.inp_tab.rows[0].cells[this.cell_idx];this.cell_idx++;$y(c,{width:cint(100/this.filters_per_line)+'%',textAlign:'left',verticalAlign:'top'});var d1=$a(c,'div','',{fontSize:'11px',marginBottom:'2px'});d1.innerHTML=label;if(ftype=='Link')d1.innerHTML+=' <img src="lib/images/icons/link.png" style="margin-bottom:-5px" title="Link">';var d2=$a(c,'div');if(in_list(['Text','Small Text','Code','Text Editor','Read Only'],ftype))
ftype='Data';if(ftype=='Select'&&!in_list(options.split('\n'),''))options='\n'+options
var inp=make_field({fieldtype:ftype,'label':label,'options':options,no_buttons:1},'',d2,this,0,1);inp.not_in_form=1;inp.report=this;inp.df.single_select=1;inp.parent_cell=c;inp.parent_tab=this.input_tab;$y(inp.wrapper,{width:'95%'});inp.refresh();inp.tn=tname;inp.fn=fname;inp.condition=ftype=='Data'?'like':cond;var me=this;inp.onchange=function(){me.start=0;}
this.filters[label]=inp;this.filter_set=1;}
Listing.prototype.remove_filter=function(label){var inp=this.filters[label];inp.parent_tab.rows[0].deleteCell(inp.parent_cell.cellIndex);delete this.filters[label];}
Listing.prototype.remove_all_filters=function(){for(var k in this.filters)this.remove_filter(k);$dh(this.filter_wrapper);}
Listing.prototype.add_sort=function(ci,fname){this.sort_list[ci]=fname;}
Listing.prototype.has_data=function(){return this.n_records;}
Listing.prototype.set_default_sort=function(fname,sort_order){this.sort_order=sort_order;this.sort_order_dict[fname]=sort_order;this.sort_by=fname;if(this.sort_heads[fname])
this.sort_heads[fname].set_sorting_as(sort_order);}
Listing.prototype.set_sort=function(cell,ci,fname){var me=this;$y(cell.sort_cell,{width:'18px'});cell.sort_img=$a(cell.sort_cell,'img');cell.fname=fname;$dh(cell.sort_img);cell.set_sort_img=function(order){var t='images/icons/sort_desc.gif';if(order=='ASC'){t='images/icons/sort_asc.gif';}
this.sort_img.src=t;}
cell.set_sorting_as=function(order){me.sort_order=order;me.sort_by=this.fname
me.sort_order_dict[this.fname]=order;this.set_sort_img(order)
if(me.cur_sort){$y(me.cur_sort,{backgroundColor:"#FFF"});$dh(me.cur_sort.sort_img);}
me.cur_sort=this;$y(this,{backgroundColor:"#DDF"});$di(this.sort_img);}
$y(cell.label_cell,{color:'#44A',cursor:'pointer'});cell.set_sort_img(me.sort_order_dict[fname]?me.sort_order_dict[fname]:'ASC');cell.onmouseover=function(){$di(this.sort_img);}
cell.onmouseout=function(){if(this!=me.cur_sort)
$dh(this.sort_img);}
cell.onclick=function(){this.set_sorting_as((me.sort_order_dict[fname]=='ASC')?'DESC':'ASC');me.run();}
this.sort_heads[fname]=cell;}
Listing.prototype.do_export=function(){this.build_query();var me=this;me.cn=[];if(this.no_index)
me.cn=this.colnames;else{for(var i=1;i<this.colnames.length;i++)
me.cn.push(this.colnames[i]);}
var q=export_query(this.query,function(query){export_csv(query,me.head_text,null,1,null,me.cn);});}
Listing.prototype.build_query=function(){if(this.get_query)this.get_query(this);if(!this.query){alert('No Query!');return;}
if(!this.prefix)this.prefix='tab';var cond=[];for(var i in this.filters){var f=this.filters[i];var val=f.get_value();var c=f.condition;if(!c)c='=';if(val&&c.toLowerCase()=='like')val+='%';if(f.tn&&val&&!in_list(['All','Select...',''],val))
cond.push(repl(' AND `%(prefix)s%(dt)s`.%(fn)s %(condition)s "%(val)s"',{prefix:this.prefix,dt:f.tn,fn:f.fn,condition:c,val:val}));}
if(cond){this.query+=NEWLINE+cond.join(NEWLINE)
if(this.query_max)
this.query_max+=NEWLINE+cond.join(NEWLINE)}
if(this.group_by)
this.query+=' '+this.group_by+' ';if(this.sort_by&&this.sort_order){this.query+=NEWLINE+' ORDER BY `'+this.sort_by+'` '+this.sort_order;}
if(this.show_query)msgprint(this.query);}
Listing.prototype.set_rec_label=function(total,cur_page_len){if(this.opts.hide_rec_label)
return;else if(total==-1)
this.rec_label.innerHTML='Fetching...'
else if(total>0)
this.rec_label.innerHTML=repl('Total %(total)s %(keyword)s. Showing %(start)s to %(end)s',{total:total,start:cint(this.start)+1,end:cint(this.start)+cint(cur_page_len),keyword:this.keyword});else if(total==null)
this.rec_label.innerHTML=''
else if(total==0)
this.rec_label.innerHTML=this.no_rec_message;}
Listing.prototype.run=function(run_callback){this.build_query();var q=this.query;var me=this;if(this.max_len&&this.start>=this.max_len)this.start-=this.page_len;q+=' LIMIT '+this.start+','+this.page_len;var call_back=function(r,rt){$dh(me.loading_img);me.max_len=r.n_values;if(r.values&&r.values.length){me.n_records=r.values.length;var nc=r.values[0].length;if(me.colwidths)nc=me.colwidths.length-(me.no_index?0:1);if(me.opts.append_records&&me.start!=0){me.append_rows(r.values.length);}else{me.clear_tab();if(!me.show_empty_tab){me.remove_result_tab();me.make_result_tab(r.values.length);}}
me.refresh(r.values.length,nc,r.values,r.n_values);me.total_records=r.n_values;me.set_rec_label(r.n_values,r.values.length);}else{me.n_records=0;me.set_rec_label(0);me.clear_tab();if(!me.opts.append_records){if(me.show_empty_tab){me.clear_tab();}else{me.remove_result_tab();me.make_result_tab(0);if(me.opts.show_no_records_label){$ds(me.show_no_records);}}}}
$ds(me.results);if(run_callback)run_callback();if(me.onrun)me.onrun();}
$dh(me.show_no_records);this.set_rec_label(-1);$di(this.loading_img);if(this.server_call){this.server_call(this,call_back);}else{args={query_max:(this.query_max?this.query_max:'')}
if(this.is_std_query)args.query=q;else args.simple_query=q;if(this.opts.formatted)args.formatted=1;$c('webnotes.widgets.query_builder.runquery',args,call_back,null,this.no_loading);}}
Listing.prototype.remove_result_tab=function(){if(!this.result_tab)return;this.result_tab.parentNode.removeChild(this.result_tab);delete this.result_tab;}
Listing.prototype.reset_tab=function(){this.remove_result_tab();this.make_result_tab();}
Listing.prototype.make_result_tab=function(nr){if(this.result_tab)return;if(!this.colwidths)alert("Listing: Must specify column widths");var has_headrow=this.colnames?1:0;if(nr==null)nr=this.page_len;nr+=has_headrow;var nc=this.colwidths.length;var t=make_table(this.results,nr,nc,(this.opts.table_width?this.opts.table_width:'100%'),this.colwidths,{padding:'0px'});t.className='srs_result_tab';this.result_tab=t;$y(t,{borderCollapse:'collapse'});if(this.opts.table_width){$y(this.results,{overflowX:'auto'});$y(t,{tableLayout:'fixed'});}
if(has_headrow){this.make_headings(t,nr,nc);if(this.sort_by&&this.sort_heads[this.sort_by]){this.sort_heads[this.sort_by].set_sorting_as(this.sort_order);}}
this.set_table_style();if(this.opts.no_border==1){$y(t,{border:'0px'});}
this.result_tab=t;}
Listing.prototype.set_table_style=function(){var t=this.result_tab;for(var ri=(this.colnames?1:0);ri<t.rows.length;ri++){for(var ci=0;ci<t.rows[ri].cells.length;ci++){if(this.opts.cell_style)$y($td(t,ri,ci),this.opts.cell_style);if(this.opts.alt_cell_style&&(ri%2))$y($td(t,ri,ci),this.opts.alt_cell_style);if(this.opts.show_empty_tab&&!$td(t,ri,ci).innerHTML)$td(t,ri,ci).innerHTML='&nbsp;';}}}
Listing.prototype.append_rows=function(nr){for(var i=0;i<nr;i++){append_row(this.result_tab);}
this.set_table_style();}
Listing.prototype.clear_tab=function(){$dh(this.results);if(this.result_tab){var nr=this.result_tab.rows.length;var nc=this.result_tab.rows[0].cells.length;for(var ri=(this.colnames?1:0);ri<nr;ri++)
for(var ci=0;ci<nc;ci++)
$td(this.result_tab,ri,ci).innerHTML=(this.opts.show_empty_tab?'&nbsp;':'');}}
Listing.prototype.clear=function(){this.rec_label.innerHTML='';this.clear_tab();}
Listing.prototype.refresh_calc=function(){if(!this.opts.show_calc)return;if(has_common(this.coltypes,['Currency','Int','Float'])){$di(this.buttons['Calc']);}else{$dh(this.buttons['Calc']);}}
Listing.prototype.refresh=function(nr,nc,d,n_values){this.refresh_more_button(nr,n_values);this.refresh_calc();if(this.show_result)
this.show_result();else{if(nr){var start=this.result_tab.rows.length-nr;for(var ri=start;ri<start+nr;ri++){var c0=$td(this.result_tab,ri,0);if(!this.no_index){c0.innerHTML=cint(this.start)+cint(ri-start)+1;}
for(var ci=0;ci<nc;ci++){var c=$td(this.result_tab,ri,ci+(this.no_index?0:1));if(c){c.innerHTML='';if(this.show_cell)this.show_cell(c,ri-start,ci,d);else this.std_cell(c,ri-start,ci,d);}}}}}}
Listing.prototype.refresh_more_button=function(nr,n_values){var me=this;if(this.more_btn){$dh(this.more_btn);}
if((this.start+nr)==this.max_len||(!this.max_len&&nr<this.page_len)){}else if(nr){if(!this.more_btn){$y(this.bottom_div,{margin:'8px 0px 16px 0px',textAlign:'center'});this.more_btn=$btn(this.bottom_div,'Show more results...',function(){me.start=me.start+me.page_len;me.more_btn.set_working();me.run(function(){me.more_btn.done_working();});},{fontSize:'14px'},0,1);$y(this.more_btn.loading_img,{marginBottom:'0px'});}
$di(this.more_btn);}}
Listing.prototype.make_headings=function(t,nr,nc){for(var ci=0;ci<nc;ci++){var tmp=make_table($td(t,0,ci),1,2,'100%',['','0px'],this.opts.head_style);$y(tmp,{tableLayout:'fixed',borderCollapse:'collapse'});$y($td(t,0,ci),this.opts.head_main_style);$td(t,0,ci).sort_cell=$td(tmp,0,1);$td(t,0,ci).label_cell=$td(tmp,0,0);$td(tmp,0,1).style.padding='0px';$td(tmp,0,0).innerHTML=this.colnames[ci]?this.colnames[ci]:'&nbsp;';if(this.sort_list[ci])this.set_sort($td(t,0,ci),ci,this.sort_list[ci]);var div=$a($td(t,0,ci),'div');$td(t,0,ci).style.borderBottom='1px solid #CCC';if(this.coltypes&&this.coltypes[ci]&&in_list(['Currency','Float','Int'],this.coltypes[ci]))$y($td(t,0,ci).label_cell,{textAlign:'right'})}}
Listing.prototype.std_cell=function(cell,ri,ci,d){var has_headrow=this.colnames?1:0;cell.div=$a(cell,'div');$s(cell.div,d[ri][ci],this.coltypes?this.coltypes[ci+(this.no_index?0:1)]:null,this.coloptions?this.coloptions[ci+(this.no_index?0:1)]:null);}
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
 *	lib/js/legacy/widgets/tabbedpage.js
 */
function TabbedPage(parent,only_labels){this.tabs={};this.items=this.tabs
this.cur_tab=null;this.label_wrapper=$a(parent,'div','box_label_wrapper',{marginTop:'16px'});this.label_body=$a(this.label_wrapper,'div','box_label_body');this.label_area=$a(this.label_body,'ul','box_tabs');if(!only_labels)this.body_area=$a(parent,'div','',{backgroundColor:'#FFF'});else this.body_area=null;this.add_item=function(label,onclick,no_body,with_heading){this.add_tab(label,onclick,no_body,with_heading);return this.items[label];}}
TabbedPage.prototype.add_tab=function(n,onshow,no_body,with_heading){var tab=$a(this.label_area,'li');tab.label=$a(tab,'a');tab.label.innerHTML=n;if(this.body_area&&!no_body){tab.tab_body=$a(this.body_area,'div');$dh(tab.tab_body);tab.body=tab.tab_body;}else{tab.tab_body=null;}
tab.onshow=onshow;var me=this;tab.collapse=function(){if(this.tab_body)$dh(this.tab_body);this.className='';if(hide_autosuggest)
hide_autosuggest();}
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
var def_ph_style={wrapper:{marginBottom:'16px',backgroundColor:'#EEE'},main_heading:{},sub_heading:{marginBottom:'8px',color:'#555',display:'none'},separator:{borderTop:'3px solid #777'},toolbar_area:{padding:'3px 0px',display:'none',borderBottom:'1px solid #AAA'}}
function PageHeader(parent,main_text,sub_text){this.wrapper=$a(parent,'div','page_header');this.t1=make_table($a(this.wrapper,'div','',def_ph_style.wrapper.backgroundColor),1,2,'100%',[null,'100px'],{padding:'2px'});$y(this.t1,{borderCollapse:'collapse'})
this.lhs=$td(this.t1,0,0);this.main_head=$a(this.lhs,'h1','',def_ph_style.main_heading);this.sub_head=$a(this.lhs,'h4','',def_ph_style.sub_heading);this.separator=$a(this.wrapper,'div','',def_ph_style.separator);this.toolbar_area=$a(this.wrapper,'div','',def_ph_style.toolbar_area);this.padding_area=$a(this.wrapper,'div','',{padding:'3px'});$y($td(this.t1,0,1),{textAlign:'right',padding:'3px'});this.close_btn=$a($td(this.t1,0,1),'span','close',{},'&times;');this.close_btn.onclick=function(){nav_obj.show_last_open();};if(main_text)this.main_head.innerHTML=main_text;if(sub_text)this.sub_head.innerHTML=sub_text;this.buttons={};this.buttons2={};}
PageHeader.prototype.add_button=function(label,fn,bold,icon,green){var tb=this.toolbar_area;if(this.buttons[label])return;var btn=$btn(tb,label,fn,{marginRight:'4px'},(green?'btn-info':''));if(bold)$y(btn,{fontWeight:'bold'});this.buttons[label]=btn;$ds(this.toolbar_area);return btn;}
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
args.colnames=colnames.join(',');args.report_name=report_name?report_name:'';open_url_post(webnotes.request.url,args);}
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
if(!in_list(['Page/','Form/','Repor','DocBr','List/','List2'],loc.substr(0,5))){loc='Page/'+loc;}
return loc.split('/');}
function historyChange(newLocation){var t=nav_obj.get_page(newLocation)
for(var i=0;i<t.length;i++)
t[i]=decodeURIComponent(t[i]);if(nav_obj.ol.length){var c=nav_obj.ol[nav_obj.ol.length-1];if(t.length==2){if(c[0]==t[0]&&c[1]==t[1])return;}else{if(c[0]==t[0]&&c[1]==t[1]&&c[2]==t[2])return;}}
if(t[2])
var docname=history_get_name(t);if(t[0]=='Form'){_history_current=newLocation;if(docname.substr(0,3)=='New'&&!(locals[t[1]]&&locals[t[1]][docname])){newdoc(t[1]);}else{loaddoc(t[1],docname);}}else if(t[0]=='Report'){_history_current=newLocation;loadreport(t[1],docname);}else if(t[0]=='Page'){_history_current=newLocation;loadpage(t[1]);}else if(t[0]=='Application'){_history_current=newLocation;loadapp(t[1]);}else if(t[0]=='DocBrowser'||t[0]=='List'){_history_current=newLocation;loaddocbrowser(t[1]);}else if(t[0]=='List2'){_history_current=newLocation;loaddocbrowser2(t[1]);}};$(window).bind('hashchange',function(){historyChange(location.hash);});
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
var pending_req=0;var fcount=0;var dialog_back;function set_loading(){pending_req++;$('#spinner').css('visibility','visible');$('body').css('cursor','progress');}
function hide_loading(){pending_req--;if(!pending_req){$('body').css('cursor','default');$('#spinner').css('visibility','hidden');}}
function freeze(){if(!dialog_back){dialog_back=$a($i('body_div'),'div','dialog_back');$(dialog_back).css('opacity',0.6);}
$ds(dialog_back);fcount++;}
function unfreeze(){if(!fcount)return;fcount--;if(!fcount){$dh(dialog_back);}}
/*
 *	lib/js/legacy/webpage/error_console.js
 */
var err_console;var err_list=[];function errprint(t){if(!err_list)err_list=[];err_list.push('<pre style="font-family: Courier, Fixed; font-size: 11px; \
  border-bottom: 1px solid #AAA; overflow: auto; width: 90%;">'+t+'</pre>');}
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
var show_doc=function(r,rt){if(locals[doctype]&&locals[doctype][name]){var frm=frms[doctype];frm.refresh(name);if(!frm.in_dialog)
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
page_name=home_page;var fn=function(r,rt){if(wn.pages[page_name]){var p=wn.pages[page_name]
page_body.change_to(page_name);}else{var p=render_page(page_name);if(!p)return;}
cur_page=page_name;if(call_back)call_back();scroll(0,0);pscript.update_page_history(page_name,no_history)
try{if(pscript['refresh_'+page_name])pscript['refresh_'+page_name]();}catch(e){console.log(e);}}
if(get_local('Page',page_name)||wn.pages[page_name])
fn();else{args=get_url_dict();args.name=page_name;$c('webnotes.widgets.page.getpage',args,fn);}}
pscript.update_page_history=function(page_name,no_history){var arg=null;var t=null;if(window.location.hash){var t=nav_obj.get_page(window.location.hash)}else if(get_url_arg('page')){var t=nav_obj.get_page(get_url_arg('page'))}
if(t&&t[1]==page_name)arg=t[2];nav_obj.open_notify('Page',page_name,arg,no_history);}
function loadscript(src,call_back){set_loading();var script=$a('head','script');script.type='text/javascript';script.src=src;script.onload=function(){if(call_back)call_back();hide_loading();}
script.onreadystatechange=function(){if(this.readyState=='complete'||this.readyState=='loaded'){hide_loading();call_back();}}}
var doc_browser_page;function loaddocbrowser(dt,label,fields){wn.require('lib/js/legacy/webpage/docbrowser.js');dt=get_label_doctype(dt);if(!doc_browser_page)
doc_browser_page=new ItemBrowserPage();doc_browser_page.show(dt,label,fields);nav_obj.open_notify('List',dt,'');}
function loaddocbrowser2(dt,label,fields){wn.pages.doclistview.show(dt);return;}
/*
 *	lib/js/legacy/webpage/uploader.js
 */
var uploaders={};var upload_frame_count=0;Uploader=function(parent,args,callback){var id='frame'+upload_frame_count;upload_frame_count++;this.callback=callback;var div=$a(parent,'div');div.innerHTML='<iframe id="'+id+'" name="'+id+'" src="blank.html" \
  style="width:0px; height:0px; border:0px"></iframe>';var div=$a(parent,'div');div.innerHTML='<form method="POST" enctype="multipart/form-data" action="'+webnotes.request.url+'" target="'+id+'"></form>';var ul_form=div.childNodes[0];var f_list=[];var inp_fdata=$a_input($a(ul_form,'span'),'file',{name:'filedata'},{marginLeft:'7px'});if(!('cmd'in args)){var inp=$a_input($a(ul_form,'span'),'hidden',{name:'cmd'});inp.value='uploadfile';}
var inp=$a_input($a(ul_form,'span'),'hidden',{name:'uploader_id'});inp.value=id;var inp=$a_input($a(ul_form,'span'),'submit',null,{marginLeft:'7px'});inp.value='Upload';$y(inp,{width:'80px'});for(var key in args){var inp=$a_input($a(ul_form,'span'),'hidden',{name:key});inp.value=args[key];}
uploaders[id]=this;}
function upload_callback(id,fid){uploaders[id].callback(fid);}
/*
 *	lib/js/legacy/webpage/page.js
 */
var stylesheets=[];function Page(page_name,content){var me=this;this.name=page_name;this.trigger=function(event){try{if(pscript[event+'_'+this.name])
pscript[event+'_'+this.name](me.wrapper);if(me.wrapper[event]){me.wrapper[event](me.wrapper);}}catch(e){console.log(e);}}
this.page_show=function(){set_title(me.doc.title?me.doc.title:me.name);if(!me.onload_complete){me.trigger('onload');me.onload_complete=true;}
me.trigger('onshow');cur_frm=null;}
this.wrapper=page_body.add_page(page_name,this.page_show);this.cont=this.wrapper
if(content)
this.wrapper.innerHTML=content;return this;}
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
this.wrapper=$a(this.parent,'div','layout-wrapper layout-wrapper-background');this.main=$a(this.wrapper,'div','layout-main-section');this.sidebar_area=$a(this.wrapper,'div','layout-side-section');$a(this.wrapper,'div','',{clear:'both'});this.head=$a(this.main,'div');this.toolbar_area=$a(this.main,'div');this.body=$a(this.main,'div');this.footer=$a(this.main,'div');if(this.heading){this.page_head=new PageHeader(this.head,this.heading);}}
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
wn.widgets.PageSidebarSection=function(sidebar,opts){this.items=[];this.sidebar=sidebar;this.wrapper=$a(sidebar.wrapper,'div','section');this.head=$a(this.wrapper,'div','section-head','',opts.title);this.body=$a(this.wrapper,'div','section-body');$br(this.wrapper,'5px');this.opts=opts;this.make_items=function(){for(var i=0;i<this.opts.items.length;i++){var item=this.opts.items[i];if((item.display&&item.display())||!item.display){var div=$a(this.body,'div','section-item');this.make_one_item(item,div);}}}
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
this.ln=$a(this.wrapper,'span','link_type section-link',opts.style,opts.label);this.ln.onclick=function(){me.opts.onclick(me)};}
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
var locals={'DocType':{}};var fields={};var fields_list={};var LocalDB={};var READ=0;var WRITE=1;var CREATE=2;var SUBMIT=3;var CANCEL=4;var AMEND=5;LocalDB.getchildren=function(child_dt,parent,parentfield,parenttype){var l=[];for(var key in locals[child_dt]){var d=locals[child_dt][key];if((d.parent==parent)&&(d.parentfield==parentfield)){if(parenttype){if(d.parenttype==parenttype)l.push(d);}else{l.push(d);}}}
l.sort(function(a,b){return(cint(a.idx)-cint(b.idx))});return l;}
LocalDB.add=function(dt,dn){if(!locals[dt])locals[dt]={};if(locals[dt][dn])delete locals[dt][dn];locals[dt][dn]={'name':dn,'doctype':dt,'docstatus':0};return locals[dt][dn];}
LocalDB.delete_doc=function(dt,dn){var doc=get_local(dt,dn);for(var ndt in locals){if(locals[ndt]){for(var ndn in locals[ndt]){var doc=locals[ndt][ndn];if(doc&&doc.parenttype==dt&&(doc.parent==dn||doc.__oldparent==dn)){delete locals[ndt][ndn];}}}}
delete locals[dt][dn];}
function get_local(dt,dn){return locals[dt]?locals[dt][dn]:null;}
LocalDB.sync=function(list){if(list._kl)list=expand_doclist(list);for(var i=0;i<list.length;i++){var d=list[i];if(!d.name)
d.name=LocalDB.get_localname(d.doctype);LocalDB.add(d.doctype,d.name);locals[d.doctype][d.name]=d;if(d.doctype=='DocType'){fields_list[d.name]=[];}else if(d.doctype=='DocField'){if(!d.parent){alert('Error: No parent specified for field "'+d.label+'"');}
if(!fields_list[d.parent])fields_list[d.parent]=[];fields_list[d.parent][fields_list[d.parent].length]=d;if(!fields[d.parent])
fields[d.parent]={};if(d.fieldname){fields[d.parent][d.fieldname]=d;}else if(d.label){fields[d.parent][d.label]=d;}}
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
var rename_observers=[];function notify_rename_observers(dt,old_name,new_name){try{delete locals[dt][old_name];}catch(e){alert("[rename_from_local] No Document for: "+old_name);}
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
var _save=function(){$c('webnotes.widgets.form.save.savedocs',{'docs':compress_doclist(doclist),'docname':dn,'action':save_action,'user':user},function(r,rtxt){if(f){f.savingflag=false;}
if(r.saved){if(onsave)onsave(r);}else{if(onerr)onerr(r);}},function(){if(f){f.savingflag=false;}},0,(f?'Saving...':''));}
if(doc.__islocal&&(doctype&&doctype.autoname&&doctype.autoname.toLowerCase()=='prompt')){var newname=prompt('Enter the name of the new '+dt,'');if(newname){doc.__newname=strip(newname);_save();}else{msgprint('Not Saved');onerr();}}else{_save();}}
function check_required(dt,dn,parent_dt){var doc=locals[dt][dn];if(doc.docstatus>1)return true;var fl=fields_list[dt];if(!fl)return true;var all_clear=true;var errfld=[];for(var i=0;i<fl.length;i++){var key=fl[i].fieldname;var v=doc[key];if(fl[i].reqd&&is_null(v)&&fl[i].fieldname){errfld[errfld.length]=fl[i].label;if(cur_frm){var f=cur_frm.fields_dict[fl[i].fieldname];if(f){if(f.set_as_error)f.set_as_error(1);if(!cur_frm.error_in_section&&f.parent_section){cur_frm.set_section(f.parent_section.sec_id);cur_frm.error_in_section=1;}}}
if(all_clear)all_clear=false;}}
if(errfld.length)msgprint('<b>Mandatory fields required in '+
(doc.parenttype?(fields[doc.parenttype][doc.parentfield].label+' (Table)'):get_doctype_label(doc.doctype))+':</b>\n'+errfld.join('\n'));return all_clear;}
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
wn.ui.toolbar.Search=wn.ui.toolbar.SelectorDialog.extend({init:function(){this._super({title:"Search",execute:function(val){selector.set_search(val);selector.show();},});this.set_values(profile.can_read.join(',').split(','));makeselector();}});
/*
 *	lib/js/wn/ui/toolbar/report.js
 */
wn.ui.toolbar.Report=wn.ui.toolbar.SelectorDialog.extend({init:function(){this._super({title:"Start Report For",execute:function(val){loadreport(val,null,null,null,1);},});this.set_values(profile.can_get_report.join(',').split(','));}});
/*
 *	lib/js/wn/ui/toolbar/recent.js
 */
wn.ui.toolbar.RecentDocs=Class.extend({init:function(){$('.navbar .nav:first').append('<li class="dropdown">\
   <a class="dropdown-toggle" data-toggle="dropdown" href="#" \
    onclick="return false;">Recent<b class="caret"></b></a>\
   <ul class="dropdown-menu" id="toolbar-recent"></ul>\
  </li>');this.setup();this.bind_events();},bind_events:function(){rename_observers.push(this);},rename_notify:function(dt,old,name){this.remove(dt,old);this.add(dt,name,1);},add:function(dt,dn,on_top){if(this.istable(dt))return;this.remove(dt,dn);var html=repl('<li data-docref="%(dt)s/%(dn)s">\
   <a href="#Form/%(dt)s/%(dn)s">\
    %(dn)s <span style="font-size: 10px">(%(dt)s)</span>\
   </a></li>',{dt:dt,dn:dn});if(on_top){$('#toolbar-recent').prepend(html);}else{$('#toolbar-recent').append(html);}},istable:function(dt){return locals.DocType[dt]&&locals.DocType[dt].istable||false;},remove:function(dt,dn){$(repl('#toolbar-recent li[data-docref="%(dt)s/%(dn)s"]',{dt:dt,dn:dn})).remove();},setup:function(){try{var rlist=JSON.parse(profile.recent);}
catch(e){return;}
var m=rlist.length;if(m>15)m=15;for(var i=0;i<m;i++){var rd=rlist[i]
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
    <img src="lib/images/ui/spinner.gif" id="spinner"/>\
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
   </div>');},make_home:function(){$('.navbar .brand').attr('href',"#!"+home_page);},make_document:function(){wn.ui.toolbar.new_dialog=new wn.ui.toolbar.NewDialog();wn.ui.toolbar.search=new wn.ui.toolbar.Search();wn.ui.toolbar.report=new wn.ui.toolbar.Report();$('.navbar .nav:first').append('<li class="dropdown">\
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
    <li><a href="#" onclick="return err_console.show();">Error Console</a></li>\
    <li><a href="#" onclick="return wn.ui.toolbar.clear_cache();">Clear Cache</a></li>\
    <li><a href="#" onclick="return wn.ui.toolbar.show_about();">About</a></li>\
   </ul>\
  </li>');if(has_common(user_roles,['Administrator','System Manager'])){$('#toolbar-tools').append('<li><a href="#" \
    onclick="return wn.ui.toolbar.download_backup();">\
    Download Backup</a></li>');}},set_user_name:function(){var fn=user_fullname;if(fn.length>15)fn=fn.substr(0,12)+'...';$('#toolbar-user-link').html(fn+'<b class="caret"></b>');},make_logout:function(){$('#toolbar-user').append('<li><a href="#" onclick="return logout();">Logout</a></li>');}});wn.ui.toolbar.clear_cache=function(){localStorage&&localStorage.clear();$c('webnotes.session_cache.clear',{},function(r,rt){show_alert(r.message);});return false;}
wn.ui.toolbar.download_backup=function(){$c('webnotes.utils.backups.get_backup',{},function(r,rt){});return false;}
wn.ui.toolbar.show_about=function(){try{wn.require('lib/js/wn/misc/about.js');wn.ui.misc.about();}catch(e){console.log(e);}
return false;}
/*
 *	lib/js/legacy/webpage/body.js
 */
wn.provide('wn.pages');function Body(){this.left_sidebar=null;this.right_sidebar=null;this.status_area=null;var me=this;page_body=this;this.ready=function(){$dh('startup_div');$ds('body_div');}
this.setup_page_areas=function(){this.center=this.body;this.center.header=$a(this.center,'div');this.center.body=$a(this.center,'div');this.center.loading=$a(this.center,'div','',{margin:'200px 0px',fontSize:'14px',color:'#999',textAlign:'center'});this.center.loading.innerHTML='Loading...'}
this.run_startup_code=function(){$(document).trigger('startup');try{if(this.cp.custom_startup_code)
eval(this.cp.custom_startup_code);}catch(e){errprint(e);}}
this.setup=function(){this.cp=wn.control_panel;this.wrapper=$a($i('body_div'),'div');this.body=$a(this.wrapper,'div');this.setup_page_areas();if(user=='Guest')user_defaults.hide_webnotes_toolbar=1;if(!cint(user_defaults.hide_webnotes_toolbar)||user=='Administrator'){this.wntoolbar=new wn.ui.toolbar.Toolbar();}
if(this.cp.page_width)
$y(this.wrapper,{width:cint(this.cp.page_width)+'px'});}
this.cur_page=null;this.add_page=function(label,onshow,onhide){var c=$a(this.center.body,'div');if(onshow)
c.page_show=onshow;if(onhide)
c.page_hide=onhide;wn.pages[label]=c;$dh(c);return c;}
this.change_to=function(label){$dh(this.center.loading);if(me.cur_page&&wn.pages[label]!=me.cur_page){if(me.cur_page.page_hide)
me.cur_page.page_hide();$dh(me.cur_page);}
me.cur_page=wn.pages[label];me.cur_page_label=label;$(me.cur_page).fadeIn();if(me.cur_page.page_show)
me.cur_page.page_show(me.cur_page);}
this.set_session_changed=function(){if(this.session_message_set)return;var div=$a($i('body_div').parentNode,'div','',{textAlign:'center',fontSize:'14px',margin:'150px auto'});$dh('body_div');div.innerHTML='This session has been changed. Please <span class="link_type" onclick="window.location.reload()">refresh</span> to continue';this.session_message_set=1;}
this.setup();}
/*
 *	lib/js/legacy/widgets/form/fields.js
 */
var no_value_fields=['Section Break','Column Break','HTML','Table','FlexTable','Button','Image'];var codeid=0;var code_editors={};function Field(){this.with_label=1;}
Field.prototype.make_body=function(){var ischk=(this.df.fieldtype=='Check'?1:0);if(this.parent)
this.wrapper=$a(this.parent,(this.with_label?'div':'span'));else
this.wrapper=document.createElement((this.with_label?'div':'span'));this.label_area=$a(this.wrapper,'div','',{margin:'8px 0px 2px 0px'});if(ischk&&!this.in_grid){this.input_area=$a(this.label_area,'span','',{marginRight:'4px'});this.disp_area=$a(this.label_area,'span','',{marginRight:'4px'});}
if(this.with_label){this.label_span=$a(this.label_area,'span','field_label')
this.label_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 4px'});$dh(this.label_icon);this.label_icon.src='lib/images/icons/error.gif';this.label_icon.title='Mandatory value needs to be entered';this.suggest_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 0px'});$dh(this.suggest_icon);this.suggest_icon.src='lib/images/icons/bullet_arrow_down.png';this.suggest_icon.title='With suggestions';}else{this.label_span=$a(this.label_area,'span','',{marginRight:'4px'})
$dh(this.label_area);}
if(!this.input_area){this.input_area=$a(this.wrapper,(this.with_label?'div':'span'));this.disp_area=$a(this.wrapper,(this.with_label?'div':'span'));}
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
return v;};var _link_onchange_flag=null;function LinkField(){}LinkField.prototype=new Field();LinkField.prototype.make_input=function(){var me=this;if(me.df.no_buttons){this.txt=$a(this.input_area,'input');this.input=this.txt;}else{makeinput_popup(this,'icon-search','icon-play','icon-plus');me.setup_buttons();me.onrefresh=function(){if(me.can_create&&cur_frm.doc.docstatus==0)
$(me.btn2).css('display','inline-block');else $dh(me.btn2);}}
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
 *	lib/js/legacy/widgets/form/form_container.js
 */
_f.FrmContainer=function(){this.wrapper=page_body.add_page("Forms",function(){},function(){});this.last_displayed=null;$dh(this.wrapper);this.body=$a(this.wrapper,'div','frm_container');_f.frm_dialog=new _f.FrmDialog();}
_f.frm_dialog=null;_f.calling_doc_stack=[];_f.temp_access={};_f.FrmDialog=function(){var me=this;this.last_displayed=null;var d=new Dialog(640,null,'Edit Row');this.body=$a(d.body,'div','dialog_frm');$y(d.body,{backgroundColor:'#EEE'});d.done_btn_area=$a(d.body,'div','',{margin:'8px'});me.on_complete=function(){if(me.table_form){me.dialog.hide();}else{var callback=function(r){var dn=cur_frm.docname;if(!r.exc){me.dialog.hide();}
if(me.on_save_callback)
me.on_save_callback(dn);}
cur_frm.save('Save',callback);}}
d.onshow=function(){d.done_btn_area.innerHTML='';d.done_btn=$btn(d.done_btn_area,'Save',null,null,'green');d.done_btn.onclick=function(){me.on_complete()};if(me.table_form){d.set_title("Editing Row #"+(_f.cur_grid_ridx+1));d.done_btn.innerHTML='Done Editing';}else{d.set_title(cur_frm.doctype==cur_frm.doctype?(cur_frm.doctype):(cur_frm.doctype+': '+cur_frm.docname));d.done_btn.innerHTML='Save';}}
d.onhide=function(){if(_f.cur_grid)
_f.cur_grid.refresh_row(_f.cur_grid_ridx,me.dn);if(page_body.cur_page_label='Forms'){cur_frm=_f.frm_con.cur_frm;}}
this.dialog=d;}
_f.add_frm=function(doctype,onload,opt_name,from_archive){if(frms['DocType']&&frms['DocType'].opendocs[doctype]){msgprint("error:Cannot create an instance of \""+doctype+"\" when the DocType is open.");return;}
if(frms[doctype]){return frms[doctype];}
var callback=function(r,rt){if(!locals['DocType'][doctype]){if(r.exc){msgprint("Did not load "+doctype,1);}
loadpage('_home');return;}
if(r.print_access){if(!_f.temp_access[doctype])
_f.temp_access[doctype]={};_f.temp_access[doctype][opt_name]=1;}
var meta=locals['DocType'][doctype];var in_dialog=false;if(meta.istable)meta.in_dialog=1;if(cint(meta.in_dialog)){var parent=_f.frm_dialog;in_dialog=true;}else{var parent=_f.frm_con;}
var f=new _f.Frm(doctype,parent);f.in_dialog=in_dialog;if(onload)onload(r,rt);}
var is_new=0;if(opt_name&&locals[doctype]&&locals[doctype][opt_name]&&locals[doctype][opt_name].__islocal){is_new=1;}
if(opt_name&&!is_new){var args={'name':opt_name,'doctype':doctype,'getdoctype':1,'user':user};if(get_url_arg('akey'))args['akey']=get_url_arg('akey');if(from_archive)args['from_archive']=1;$c('webnotes.widgets.form.load.getdoc',args,callback);}else{$c('webnotes.widgets.form.load.getdoctype',args={'doctype':doctype},callback);}}
/*
 *	lib/js/legacy/widgets/form/form_header.js
 */
_f.FrmHeader=function(parent,frm){var me=this;this.wrapper=$a(parent,'div');if(frm.meta.in_dialog)$y(this.wrapper,{marginLeft:'8px',marginRight:'8px'});this.page_head=new PageHeader(this.wrapper);this.dt_area=$a(this.page_head.main_head,'h1','',{marginRight:'8px',display:'inline'})
var div=$a(null,'div','',{marginBottom:'4px'});this.page_head.lhs.insertBefore(div,this.page_head.sub_head);this.dn_area=$a(div,'span','',{fontSize:'14px',fontWeight:'normal',marginRight:'8px'})
this.status_area=$a(div,'span','',{marginRight:'8px',marginBottom:'2px',cursor:'pointer',textShadow:'none'})
this.timestamp_area=$a($a(div,'div','',{marginTop:'3px'}),'span','field_description',{fontSize:'11px'});}
_f.FrmHeader.prototype.show=function(){$ds(this.wrapper);}
_f.FrmHeader.prototype.hide=function(){$dh(this.wrapper);}
_f.FrmHeader.prototype.refresh=function(){var me=this;var p=cur_frm.get_doc_perms();this.page_head.clear_toolbar();if(cur_frm.meta.read_only_onload&&!cur_frm.doc.__islocal){if(!cur_frm.editable)
this.page_head.add_button('Edit',function(){cur_frm.edit_doc();},1,'ui-icon-document',1);else
this.page_head.add_button('Print View',function(){cur_frm.is_editable[cur_frm.docname]=0;cur_frm.refresh();},1,'ui-icon-document');}
if(cur_frm.editable&&cint(cur_frm.doc.docstatus)==0&&p[WRITE])
this.page_head.add_button('Save',function(){cur_frm.save('Save');},1,'ui-icon-disk',1);if(cint(cur_frm.doc.docstatus)==0&&p[SUBMIT]&&(!cur_frm.doc.__islocal))
this.page_head.add_button('Submit',function(){cur_frm.savesubmit();},0,'ui-icon-locked');if(cint(cur_frm.doc.docstatus)==1&&p[SUBMIT]){this.update_btn=this.page_head.add_button('Update',function(){cur_frm.saveupdate();},1,'ui-icon-disk',1);if(!cur_frm.doc.__unsaved)$dh(this.update_btn);}
if(cint(cur_frm.doc.docstatus)==1&&p[CANCEL])
this.page_head.add_button('Cancel',function(){cur_frm.savecancel()},0,'ui-icon-closethick');if(cint(cur_frm.doc.docstatus)==2&&p[AMEND])
this.page_head.add_button('Amend',function(){cur_frm.amend_doc()},0,'ui-icon-scissors');}
_f.FrmHeader.prototype.show_toolbar=function(){$ds(this.wrapper);this.refresh();}
_f.FrmHeader.prototype.hide_toolbar=function(){$dh(this.wrapper);}
_f.FrmHeader.prototype.refresh_toolbar=function(){var m=cur_frm.meta;if(m.hide_heading||cur_frm.in_dialog){this.hide();}else{this.show();if(m.hide_toolbar){this.hide_toolbar();}else{this.show_toolbar();}}}
_f.FrmHeader.prototype.get_timestamp=function(doc){var scrub_date=function(d){if(d)t=d.split(' ');else return'';return dateutil.str_to_user(t[0])+' '+t[1];}
return repl("Created: %(c_by)s %(c_on)s %(m_by)s %(m_on)s",{c_by:doc.owner,c_on:scrub_date(doc.creation?doc.creation:''),m_by:doc.modified_by?(' | Modified: '+doc.modified_by):'',m_on:doc.modified?('on '+scrub_date(doc.modified)):''});}
_f.FrmHeader.prototype.get_status_tags=function(doc,f){var make_tag=function(label,col){var s=$a(null,'span','',{padding:'2px',backgroundColor:col,color:'#FFF',fontWeight:'bold',marginLeft:(f.meta.issingle?'0px':'8px'),fontSize:'11px'});$(s).css('-moz-border-radius','3px').css('-webkit-border-radius','3px')
s.innerHTML=label;return s;}
var sp1=null;var sp2=null;if(doc.__islocal){label='Unsaved Draft';col='#F81';}else if(cint(doc.__unsaved)){label='Not Saved';col='#F81';if(doc.docstatus==1&&this.update_btn)$ds(this.update_btn);}else if(cint(doc.docstatus)==0){label='Saved';col='#0A1';if(f.get_doc_perms()[SUBMIT]){sp2=make_tag('To Be Submitted','#888');}}else if(cint(doc.docstatus)==1){label='Submitted';col='#44F';}else if(cint(doc.docstatus)==2){label='Cancelled';col='#F44';}
sp1=make_tag(label,col);this.set_in_recent(doc,col);return[sp1,sp2];}
_f.FrmHeader.prototype.set_in_recent=function(doc,col){var tn=$i('rec_'+doc.doctype+'-'+doc.name);if(tn)
$y(tn,{backgroundColor:col});}
_f.FrmHeader.prototype.set_save_submit_color=function(doc){var save_btn=this.page_head.buttons['Save'];var submit_btn=this.page_head.buttons['Submit'];if(cint(doc.docstatus)==0&&submit_btn&&save_btn){if(cint(doc.__unsaved)){$(save_btn).addClass('btn-info');$(submit_btn).removeClass('btn-info');}else{$(submit_btn).addClass('btn-info');$(save_btn).removeClass('btn-info');}}}
_f.FrmHeader.prototype.refresh_labels=function(f){var ph=this.page_head;var me=this;this.dt_area.innerHTML=get_doctype_label(f.doctype);this.dn_area.innerHTML='';if(!f.meta.issingle)
this.dn_area.innerHTML=f.docname;var doc=locals[f.doctype][f.docname];var sl=this.get_status_tags(doc,f);this.set_save_submit_color(doc);var t=this.status_area;t.innerHTML='';t.appendChild(sl[0]);if(sl[1])t.appendChild(sl[1]);this.timestamp_area.innerHTML=me.get_timestamp(doc);}
/*
 *	lib/js/legacy/widgets/form/form.js
 */
wn.provide('_f');_f.edit_record=function(dt,dn){d=_f.frm_dialog;var show_dialog=function(){var f=frms[dt];if(f.meta.istable){f.parent_doctype=cur_frm.doctype;f.parent_docname=cur_frm.docname;}
d.cur_frm=f;d.dn=dn;d.table_form=f.meta.istable;f.refresh(dn);}
if(!frms[dt]){_f.add_frm(dt,show_dialog,null);}else{show_dialog();}}
_f.Frm=function(doctype,parent){this.docname='';this.doctype=doctype;this.display=0;var me=this;this.is_editable={};this.opendocs={};this.cur_section={};this.sections=[];this.sections_by_label={};this.section_count;this.grids=[];this.cscript={};this.pformat={};this.fetch_dict={};this.parent=parent;this.tinymce_id_list=[];frms[doctype]=this;this.setup_meta(doctype);rename_observers.push(this);}
_f.Frm.prototype.setup=function(){var me=this;this.fields=[];this.fields_dict={};this.wrapper=$a(this.parent.body,'div');this.setup_print_layout();this.saved_wrapper=$a(this.wrapper,'div');this.setup_std_layout();this.setup_client_script();this.setup_done=true;}
_f.Frm.prototype.setup_print_layout=function(){this.print_wrapper=$a(this.wrapper,'div');this.print_head=$a(this.print_wrapper,'div');this.print_body=$a(this.print_wrapper,'div','layout_wrapper',{padding:'23px'});var t=make_table(this.print_head,1,2,'100%',[],{padding:'6px'});this.view_btn_wrapper=$a($td(t,0,0),'span','green_buttons');this.view_btn=$btn(this.view_btn_wrapper,'View Details',function(){cur_frm.edit_doc()},{marginRight:'4px'},'green');this.print_btn=$btn($td(t,0,0),'Print',function(){cur_frm.print_doc()});$y($td(t,0,1),{textAlign:'right'});this.print_close_btn=$btn($td(t,0,1),'Close',function(){nav_obj.show_last_open();});}
_f.Frm.prototype.onhide=function(){if(_f.cur_grid_cell)_f.cur_grid_cell.grid.cell_deselect();}
_f.Frm.prototype.setup_std_layout=function(){this.page_layout=new wn.PageLayout({parent:this.wrapper,main_width:this.in_dialog?'100%':'75%',sidebar_width:this.in_dialog?'0%':'25%'})
this.meta.section_style='Simple';this.layout=new Layout(this.page_layout.body,'100%');if(this.in_dialog){$(this.page_layout.wrapper).removeClass('layout-wrapper-background');$(this.page_layout.main).removeClass('layout-main-section');$(this.page_layout.sidebar_area).toggle(false);}else{this.setup_sidebar();}
this.setup_footer();if(!(this.meta.istable||user=='Guest'))this.frm_head=new _f.FrmHeader(this.page_layout.head,this);if(this.frm_head&&this.meta.in_dialog)$dh(this.frm_head.page_head.close_btn);if(this.meta.colour)
this.layout.wrapper.style.backgroundColor='#'+this.meta.colour.split(':')[1];this.setup_fields_std();if(this.meta.description)
this.add_description();}
_f.Frm.prototype.add_description=function(){if(!wn.md2html){wn.require('lib/js/lib/showdown.js');wn.md2html=new Showdown.converter();}
this.description_wrapper=$a(this.page_layout.footer.help_area,'div','info-box',{marginTop:'10px'},wn.md2html.makeHtml('#### Help\n\n'+this.meta.description));}
_f.Frm.prototype.setup_print=function(){var fl=getchildren('DocFormat',this.meta.name,'formats','DocType');var l=[];this.default_format='Standard';if(fl.length){this.default_format=fl[0].format;for(var i=0;i<fl.length;i++)
l.push(fl[i].format);}
if(this.meta.default_print_format)
this.default_format=this.meta.default_print_format;l.push('Standard');this.print_sel=$a(null,'select','',{width:'160px'});add_sel_options(this.print_sel,l);this.print_sel.value=this.default_format;}
_f.Frm.prototype.print_doc=function(){if(this.doc.docstatus==2){msgprint("Cannot Print Cancelled Documents.");return;}
_p.show_dialog();}
_f.Frm.prototype.email_doc=function(){if(!_e.dialog)_e.make();sel=this.print_sel;var c=$td(_e.dialog.rows['Format'].tab,0,1);if(c.cur_sel){c.removeChild(c.cur_sel);c.cur_sel=null;}
c.appendChild(this.print_sel);c.cur_sel=this.print_sel;_e.dialog.widgets['Send With Attachments'].checked=0;if(cur_frm.doc.file_list){$ds(_e.dialog.rows['Send With Attachments']);}else{$dh(_e.dialog.rows['Send With Attachments']);}
_e.dialog.widgets['Subject'].value=get_doctype_label(this.meta.name)+': '+this.docname;_e.dialog.show();}
_f.Frm.prototype.rename_notify=function(dt,old,name){if(this.doctype!=dt)return;this.cur_section[name]=this.cur_section[old];delete this.cur_section[old];this.is_editable[name]=this.is_editable[old];delete this.is_editable[old];if(this.docname==old)
this.docname=name;if(this&&this.opendocs[old]){local_dt[dt][name]=local_dt[dt][old];local_dt[dt][old]=null;}
this.opendocs[old]=false;this.opendocs[name]=true;}
_f.Frm.prototype.set_heading=function(){if(!this.meta.istable&&this.frm_head)this.frm_head.refresh_labels(this);}
_f.Frm.prototype.set_section=function(sec_id){if(!this.sections[sec_id]||!this.sections[sec_id].expand)
return;if(this.sections[this.cur_section[this.docname]])
this.sections[this.cur_section[this.docname]].collapse();this.sections[sec_id].expand();this.cur_section[this.docname]=sec_id;}
_f.Frm.prototype.setup_meta=function(){this.meta=get_local('DocType',this.doctype);this.perm=get_perm(this.doctype);this.setup_print();}
_f.Frm.prototype.setup_sidebar=function(){this.sidebar=new wn.widgets.form.sidebar.Sidebar(this);}
_f.Frm.prototype.setup_footer=function(){var me=this;var f=this.page_layout.footer;f.save_area=$a(this.page_layout.footer,'div','',{display:'none'});f.help_area=$a(this.page_layout.footer,'div');var b=$btn(f.save_area,'Save',function(){cur_frm.save('Save');},{marginLeft:'0px'},'green');f.show_save=function(){$ds(me.page_layout.footer.save_area);}
f.hide_save=function(){$dh(me.page_layout.footer.save_area);}}
_f.Frm.prototype.setup_fields_std=function(){var fl=fields_list[this.doctype];fl.sort(function(a,b){return a.idx-b.idx});if(fl[0]&&fl[0].fieldtype!="Section Break"||get_url_arg('embed')){this.layout.addrow();if(fl[0].fieldtype!="Column Break"){var c=this.layout.addcell();$y(c.wrapper,{padding:'8px'});}}
var sec;for(var i=0;i<fl.length;i++){var f=fl[i];if(get_url_arg('embed')&&(in_list(['Section Break','Column Break'],f.fieldtype)))continue;if(f.fieldtype=='Section Break'&&fl[i+1]&&fl[i+1].fieldtype=='Section Break')continue;var fn=f.fieldname?f.fieldname:f.label;var fld=make_field(f,this.doctype,this.layout.cur_cell,this);this.fields[this.fields.length]=fld;this.fields_dict[fn]=fld;if(this.meta.section_style!='Simple')
fld.parent_section=sec;if(f.fieldtype=='Section Break'&&f.options!='Simple')
sec=fld;if((f.fieldtype=='Section Break')&&(fl[i+1])&&(fl[i+1].fieldtype!='Column Break')&&!f.hidden){var c=this.layout.addcell();$y(c.wrapper,{padding:'8px'});}}}
_f.Frm.prototype.add_custom_button=function(label,fn,icon){this.frm_head.page_head.add_button(label,fn,1);}
_f.Frm.prototype.clear_custom_buttons=function(){}
_f.Frm.prototype.add_fetch=function(link_field,src_field,tar_field){if(!this.fetch_dict[link_field]){this.fetch_dict[link_field]={'columns':[],'fields':[]}}
this.fetch_dict[link_field].columns.push(src_field);this.fetch_dict[link_field].fields.push(tar_field);}
_f.Frm.prototype.setup_client_script=function(){if(this.meta.client_script_core||this.meta.client_script||this.meta.__js){this.runclientscript('setup',this.doctype,this.docname);}}
_f.Frm.prototype.set_parent=function(parent){if(parent){this.parent=parent;if(this.wrapper&&this.wrapper.parentNode!=parent)
parent.appendChild(this.wrapper);}}
_f.Frm.prototype.refresh_print_layout=function(){$ds(this.print_wrapper);$dh(this.page_layout.wrapper);var me=this;var print_callback=function(print_html){me.print_body.innerHTML=print_html;}
if(cur_frm.doc.select_print_heading)
cur_frm.set_print_heading(cur_frm.doc.select_print_heading)
if(user!='Guest'){$di(this.view_btn_wrapper);if(cur_frm.doc.__archived){$dh(this.view_btn_wrapper);}}else{$dh(this.view_btn_wrapper);$dh(this.print_close_btn);}
_p.build(this.default_format,print_callback,null,1);}
_f.Frm.prototype.hide=function(){$dh(this.wrapper);this.display=0;if(hide_autosuggest)
hide_autosuggest();}
_f.Frm.prototype.show_the_frm=function(){if(this.parent.last_displayed&&this.parent.last_displayed!=this){this.parent.last_displayed.defocus_rest();this.parent.last_displayed.hide();}
if(this.wrapper&&this.wrapper.style.display.toLowerCase()=='none'){$ds(this.wrapper);this.display=1;}
if(this.meta.in_dialog&&!this.parent.dialog.display){if(!this.meta.istable)
this.parent.table_form=false;this.parent.dialog.show();}
this.parent.last_displayed=this;}
_f.Frm.prototype.set_print_heading=function(txt){this.pformat[cur_frm.docname]=txt;}
_f.Frm.prototype.defocus_rest=function(){if(_f.cur_grid_cell)_f.cur_grid_cell.grid.cell_deselect();cur_page=null;}
_f.Frm.prototype.get_doc_perms=function(){var p=[0,0,0,0,0,0];for(var i=0;i<this.perm.length;i++){if(this.perm[i]){if(this.perm[i][READ])p[READ]=1;if(this.perm[i][WRITE])p[WRITE]=1;if(this.perm[i][SUBMIT])p[SUBMIT]=1;if(this.perm[i][CANCEL])p[CANCEL]=1;if(this.perm[i][AMEND])p[AMEND]=1;}}
return p;}
_f.Frm.prototype.refresh_header=function(){if(!this.meta.in_dialog){set_title(this.meta.issingle?this.doctype:this.docname);}
if(this.frm_head)this.frm_head.refresh_toolbar();if(wn.ui.toolbar.recent)wn.ui.toolbar.recent.add(this.doctype,this.docname,1);this.set_heading();}
_f.Frm.prototype.check_doc_perm=function(){var dt=this.parent_doctype?this.parent_doctype:this.doctype;var dn=this.parent_docname?this.parent_docname:this.docname;this.perm=get_perm(dt,dn);this.orig_perm=get_perm(dt,dn,1);if(!this.perm[0][READ]){if(user=='Guest'){if(_f.temp_access[dt]&&_f.temp_access[dt][dn]){this.perm=[[1,0,0]]
return 1;}}
nav_obj.show_last_open();return 0;}
return 1}
_f.Frm.prototype.refresh=function(docname){if(docname){if(this.docname!=docname&&!this.meta.in_dialog&&!this.meta.istable)scroll(0,0);this.docname=docname;}
if(!this.meta.istable){cur_frm=this;this.parent.cur_frm=this;}
if(this.docname){if(!this.check_doc_perm())return;if(!this.setup_done)this.setup();this.runclientscript('set_perm',this.doctype,this.docname);this.doc=get_local(this.doctype,this.docname);cur_frm.cscript.is_onload=false;if(!this.opendocs[this.docname]){cur_frm.cscript.is_onload=true;this.setnewdoc(this.docname);}
if(this.doc.__islocal)
this.is_editable[this.docname]=1;this.editable=this.is_editable[this.docname];if(!this.doc.__archived&&(this.editable||(!this.editable&&this.meta.istable))){if(this.print_wrapper){$dh(this.print_wrapper);$ds(this.page_layout.wrapper);}
if(!this.meta.istable){this.refresh_header();this.sidebar&&this.sidebar.refresh();}
this.runclientscript('refresh');$(document).trigger('form_refresh')
this.refresh_tabs();this.refresh_fields();this.refresh_dependency();this.refresh_footer();if(this.layout)this.layout.show();if(cur_frm.cscript.is_onload)
this.runclientscript('onload_post_render',this.doctype,this.docname);}else{this.refresh_header();if(this.print_wrapper){this.refresh_print_layout();}
this.runclientscript('edit_status_changed');}
if(!this.display)this.show_the_frm();if(!this.meta.in_dialog)page_body.change_to('Forms');$(cur_frm.wrapper).trigger('render_complete');}}
_f.Frm.prototype.refresh_tabs=function(){var me=this;if(me.meta.section_style=='Tray'||me.meta.section_style=='Tabbed'){for(var i in me.sections){me.sections[i].collapse();}
me.set_section(me.cur_section[me.docname]);}}
_f.Frm.prototype.refresh_footer=function(){var f=this.page_layout.footer;if(f.save_area){if(get_url_arg('embed')||(this.editable&&!this.meta.in_dialog&&this.doc.docstatus==0&&!this.meta.istable&&this.get_doc_perms()[WRITE])){f.show_save();}else{f.hide_save();}}}
_f.Frm.prototype.refresh_fields=function(){for(var i=0;i<this.fields.length;i++){var f=this.fields[i];f.perm=this.perm;f.docname=this.docname;if(f.refresh)f.refresh();}
this.cleanup_refresh(this);}
_f.Frm.prototype.cleanup_refresh=function(){var me=this;if(me.fields_dict['amended_from']){if(me.doc.amended_from){unhide_field('amended_from');unhide_field('amendment_date');}else{hide_field('amended_from');hide_field('amendment_date');}}
if(me.fields_dict['trash_reason']){if(me.doc.trash_reason&&me.doc.docstatus==2){unhide_field('trash_reason');}else{hide_field('trash_reason');}}
if(me.meta.autoname&&me.meta.autoname.substr(0,6)=='field:'&&!me.doc.__islocal){var fn=me.meta.autoname.substr(6);set_field_permlevel(fn,1);}}
_f.Frm.prototype.refresh_dependency=function(){var me=this;var doc=locals[this.doctype][this.docname];var dep_dict={};var has_dep=false;for(fkey in me.fields){var f=me.fields[fkey];f.dependencies_clear=true;var guardian=f.df.depends_on;if(guardian){if(!dep_dict[guardian])
dep_dict[guardian]=[];dep_dict[guardian][dep_dict[guardian].length]=f;has_dep=true;}}
if(!has_dep)return;for(var i=me.fields.length-1;i>=0;i--){var f=me.fields[i];f.guardian_has_value=true;if(f.df.depends_on){var v=doc[f.df.depends_on];if(f.df.depends_on.substr(0,5)=='eval:'){f.guardian_has_value=eval(f.df.depends_on.substr(5));}else if(f.df.depends_on.substr(0,3)=='fn:'){f.guardian_has_value=me.runclientscript(f.df.depends_on.substr(3),me.doctype,me.docname);}else{if(v||(v==0&&!v.substr)){}else{f.guardian_has_value=false;}}
if(f.guardian_has_value){if(f.grid)f.grid.show();else $ds(f.wrapper);}else{if(f.grid)f.grid.hide();else $dh(f.wrapper);}}}}
_f.Frm.prototype.setnewdoc=function(docname){if(this.opendocs[docname]){this.docname=docname;return;}
Meta.make_local_dt(this.doctype,docname);this.docname=docname;var me=this;var viewname=docname;if(this.meta.issingle)viewname=this.doctype;this.runclientscript('onload',this.doctype,this.docname);this.is_editable[docname]=1;if(this.meta.read_only_onload)this.is_editable[docname]=0;if(this.meta.section_style=='Tray'||this.meta.section_style=='Tabbed'){this.cur_section[docname]=0;}
this.opendocs[docname]=true;}
_f.Frm.prototype.edit_doc=function(){this.is_editable[this.docname]=true;this.refresh();}
_f.Frm.prototype.show_doc=function(dn){this.refresh(dn);}
var validated;_f.Frm.prototype.save=function(save_action,call_back){if(!save_action)save_action='Save';var me=this;if(this.savingflag){msgprint("Document is currently saving....");return;}
if(save_action=='Submit'){locals[this.doctype][this.docname].submitted_on=dateutil.full_str();locals[this.doctype][this.docname].submitted_by=user;}
if(save_action=='Trash'){var reason=prompt('Reason for trash (mandatory)','');if(!strip(reason)){msgprint('Reason is mandatory, not trashed');return;}
locals[this.doctype][this.docname].trash_reason=reason;}
if(save_action=='Cancel'){var reason=prompt('Reason for cancellation (mandatory)','');if(!strip(reason)){msgprint('Reason is mandatory, not cancelled');return;}
locals[this.doctype][this.docname].cancel_reason=reason;locals[this.doctype][this.docname].cancelled_on=dateutil.full_str();locals[this.doctype][this.docname].cancelled_by=user;}else if(save_action=='Update'){}else{validated=true;if(this.cscript.validate)
this.runclientscript('validate',this.doctype,this.docname);if(!validated){this.savingflag=false;return'Error';}}
var ret_fn=function(r){if(user=='Guest'&&!r.exc){$dh(me.page_layout.wrapper);$ds(me.saved_wrapper);me.saved_wrapper.innerHTML='<div style="padding: 150px 16px; text-align: center; font-size: 14px;">'
+(cur_frm.message_after_save?cur_frm.message_after_save:'Your information has been sent. Thank you!')
+'</div>';return;}
if(!me.meta.istable){me.refresh();}
if(call_back){if(call_back=='home'){loadpage('_home');return;}
call_back(r);}}
var me=this;var ret_fn_err=function(r){var doc=locals[me.doctype][me.docname];me.savingflag=false;ret_fn(r);}
this.savingflag=true;if(this.docname&&validated){scroll(0,0);return this.savedoc(save_action,ret_fn,ret_fn_err);}}
_f.Frm.prototype.runscript=function(scriptname,callingfield,onrefresh){var me=this;if(this.docname){var doclist=compress_doclist(make_doclist(this.doctype,this.docname));if(callingfield)callingfield.input.disabled=true;$c('runserverobj',{'docs':doclist,'method':scriptname},function(r,rtxt){if(onrefresh)
onrefresh(r,rtxt);me.refresh_fields();me.refresh_dependency();if(callingfield)callingfield.input.done_working();});}}
_f.Frm.prototype.runclientscript=function(caller,cdt,cdn){var _dt=this.parent_doctype?this.parent_doctype:this.doctype;var _dn=this.parent_docname?this.parent_docname:this.docname;var doc=get_local(_dt,_dn);if(!cdt)cdt=this.doctype;if(!cdn)cdn=this.docname;var ret=null;try{if(this.cscript[caller])
ret=this.cscript[caller](doc,cdt,cdn);if(this.cscript['custom_'+caller])
ret+=this.cscript['custom_'+caller](doc,cdt,cdn);}catch(e){console.log(e);}
if(caller&&caller.toLowerCase()=='setup'){var doctype=get_local('DocType',this.doctype);var cs=doctype.__js||(doctype.client_script_core+doctype.client_script);if(cs){try{var tmp=eval(cs);}catch(e){console.log(e);}}
if(doctype.__css)set_style(doctype.__css)
if(doctype.client_string){this.cstring={};var elist=doctype.client_string.split('---');for(var i=1;i<elist.length;i=i+2){this.cstring[strip(elist[i])]=elist[i+1];}}}
return ret;}
_f.Frm.prototype.copy_doc=function(onload,from_amend){if(!this.perm[0][CREATE]){msgprint('You are not allowed to create '+this.meta.name);return;}
var dn=this.docname;var newdoc=LocalDB.copy(this.doctype,dn,from_amend);if(this.meta.allow_attach&&newdoc.file_list)
newdoc.file_list=null;var dl=make_doclist(this.doctype,dn);var tf_dict={};for(var d in dl){d1=dl[d];if(!tf_dict[d1.parentfield]){tf_dict[d1.parentfield]=get_field(d1.parenttype,d1.parentfield);}
if(d1.parent==dn&&cint(tf_dict[d1.parentfield].no_copy)!=1){var ch=LocalDB.copy(d1.doctype,d1.name,from_amend);ch.parent=newdoc.name;ch.docstatus=0;ch.owner=user;ch.creation='';ch.modified_by=user;ch.modified='';}}
newdoc.__islocal=1;newdoc.docstatus=0;newdoc.owner=user;newdoc.creation='';newdoc.modified_by=user;newdoc.modified='';if(onload)onload(newdoc);loaddoc(newdoc.doctype,newdoc.name);}
_f.Frm.prototype.reload_doc=function(){var me=this;if(frms['DocType']&&frms['DocType'].opendocs[me.doctype]){msgprint("error:Cannot refresh an instance of \""+me.doctype+"\" when the DocType is open.");return;}
var ret_fn=function(r,rtxt){me.runclientscript('setup',me.doctype,me.docname);me.refresh();}
if(me.doc.__islocal){$c('webnotes.widgets.form.load.getdoctype',{'doctype':me.doctype},ret_fn,null,null,'Refreshing '+me.doctype+'...');}else{var gl=me.grids;for(var i=0;i<gl.length;i++){var dt=gl[i].df.options;for(var dn in locals[dt]){if(locals[dt][dn].__islocal&&locals[dt][dn].parent==me.docname){var d=locals[dt][dn];d.parent='';d.docstatus=2;d.__deleted=1;}}}
$c('webnotes.widgets.form.load.getdoc',{'name':me.docname,'doctype':me.doctype,'getdoctype':1,'user':user},ret_fn,null,null,'Refreshing '+me.docname+'...');}}
_f.Frm.prototype.savedoc=function(save_action,onsave,onerr){this.error_in_section=0;save_doclist(this.doctype,this.docname,save_action,onsave,onerr);}
_f.Frm.prototype.saveupdate=function(){this.save('Update');}
_f.Frm.prototype.savesubmit=function(){var answer=confirm("Permanently Submit "+this.docname+"?");var me=this;if(answer){this.save('Submit',function(r){if(!r.exc&&me.cscript.on_submit){me.runclientscript('on_submit',me.doctype,me.docname);}});}}
_f.Frm.prototype.savecancel=function(){var answer=confirm("Permanently Cancel "+this.docname+"?");if(answer)this.save('Cancel');}
_f.Frm.prototype.savetrash=function(){var me=this;var answer=confirm("Permanently Delete "+this.docname+"? This action cannot be reversed");if(answer){$c('webnotes.model.delete_doc',{dt:this.doctype,dn:this.docname},function(r,rt){if(r.message=='okay'){LocalDB.delete_doc(me.doctype,me.docname);if(wn.ui.toolbar.recent)wn.ui.toolbar.recent.remove(me.doctype,me.docname);nav_obj.show_last_open();}})}}
_f.Frm.prototype.amend_doc=function(){if(!this.fields_dict['amended_from']){alert('"amended_from" field must be present to do an amendment.');return;}
var me=this;var fn=function(newdoc){newdoc.amended_from=me.docname;if(me.fields_dict&&me.fields_dict['amendment_date'])
newdoc.amendment_date=dateutil.obj_to_str(new Date());}
this.copy_doc(fn,1);}
_f.get_value=function(dt,dn,fn){if(locals[dt]&&locals[dt][dn])
return locals[dt][dn][fn];}
_f.set_value=function(dt,dn,fn,v){var d=locals[dt][dn];if(!d){errprint('error:Trying to set a value for "'+dt+','+dn+'" which is not found');return;}
var changed=d[fn]!=v;if(changed&&(d[fn]==null||v==null)&&(cstr(d[fn])==cstr(v)))changed=0;if(changed){d[fn]=v;d.__unsaved=1;var frm=frms[d.doctype];try{if(d.parent&&d.parenttype){locals[d.parenttype][d.parent].__unsaved=1;frm=frms[d.parenttype];}}catch(e){if(d.parent&&d.parenttype)
errprint('Setting __unsaved error:'+d.name+','+d.parent+','+d.parenttype);}
if(frm&&frm==cur_frm){frm.set_heading();}}}
_f.Frm.prototype.show_comments=function(){if(!cur_frm.comments){cur_frm.comments=new Dialog(540,400,'Comments');cur_frm.comments.comment_body=$a(cur_frm.comments.body,'div','dialog_frm');$y(cur_frm.comments.body,{backgroundColor:'#EEE'});cur_frm.comments.list=new CommentList(cur_frm.comments.comment_body);}
cur_frm.comments.list.dt=cur_frm.doctype;cur_frm.comments.list.dn=cur_frm.docname;cur_frm.comments.show();cur_frm.comments.list.run();}
/*
 *	lib/js/legacy/widgets/form/form_fields.js
 */
_f.ColumnBreak=function(){this.set_input=function(){};}
_f.ColumnBreak.prototype.make_body=function(){if((!this.perm[this.df.permlevel])||(!this.perm[this.df.permlevel][READ])||this.df.hidden){return;}
this.cell=this.frm.layout.addcell(this.df.width);$y(this.cell.wrapper,{padding:'8px'});_f.cur_col_break_width=this.df.width;var fn=this.df.fieldname?this.df.fieldname:this.df.label;if(this.df&&this.df.label){this.label=$a(this.cell.wrapper,'div','','',this.df.label);}}
_f.ColumnBreak.prototype.refresh=function(layout){if(!this.cell)return;var fn=this.df.fieldname?this.df.fieldname:this.df.label;if(fn){this.df=get_field(this.doctype,fn,this.docname);if(this.set_hidden!=this.df.hidden){if(this.df.hidden)
this.cell.hide();else
this.cell.show();this.set_hidden=this.df.hidden;}}}
_f.SectionBreak=function(){this.set_input=function(){};}
_f.SectionBreak.prototype.make_row=function(){this.row=this.df.label?this.frm.layout.addrow():this.frm.layout.addsubrow();}
_f.SectionBreak.prototype.make_collapsible=function(head){var me=this;var div=$a(head,'div','',{paddingBottom:'3px',borderBottom:'1px solid #AAA'});if(cur_frm.meta.in_dialog)$y(div,{marginLeft:'8px'});this.chk=$a_input(div,'checkbox',null,{marginRight:'8px'})
if(this.df.label){this.label=$a(div,'h3','',{display:'inline'},this.df.label);}
var d=this.df.description;if(d){this.desc_area=$a(div,'span','field_description',{marginLeft:'8px'});this.desc_area.innerHTML=d.substr(0,50)+(d.length>50?'...':'');}
var span=$a(div,'i','icon-arrow-up',{cssFloat:'right',marginRight:'8px',cursor:'pointer',verticalAlign:'middle',marginTop:'7px'})
span.title='Go to top';span.onclick=function(){scroll(0,0);}
this.chk.onclick=function(){if(this.checked)me.expand();else me.collapse();}
this.expand=function(){$(me.row.main_body).slideDown();}
this.collapse=function(){$(me.row.main_body).slideUp();}
if(me.frm.section_count){$dh(this.row.main_body);}else{this.chk.checked=true;}}
_f.SectionBreak.prototype.make_simple_section=function(with_header){this.wrapper=$a(this.row.main_head,'div','',{margin:'8px 8px 0px 0px'});var me=this;if(this.df.colour){var col=this.df.colour.split(':')[1];if(col!='FFF'){$y(this.row.sub_wrapper,{margin:'8px',padding:'0px',backgroundColor:('#'+col)});}}
if(with_header){if(this.df.label&&this.df.options!='Simple'){this.make_collapsible(this.wrapper);}else{$y(this.wrapper,{paddingBottom:'4px'});if(this.df.label){$a(this.wrapper,'h3','',{},this.df.label);}}}
$y(this.row.body,{marginLeft:'17px'});}
_f.SectionBreak.prototype.add_to_sections=function(){this.sec_id=this.frm.sections.length;this.frm.sections[this.sec_id]=this;this.frm.sections_by_label[this.df.label]=this;}
_f.cur_sec_header=null;_f.SectionBreak.prototype.make_body=function(){if((!this.perm[this.df.permlevel])||(!this.perm[this.df.permlevel][READ])||this.df.hidden){return;}
var me=this;if(this.df){this.make_row();this.make_simple_section(1,1);}}
_f.SectionBreak.prototype.refresh=function(layout){var fn=this.df.fieldname?this.df.fieldname:this.df.label;if(fn)
this.df=get_field(this.doctype,fn,this.docname);if(this.set_hidden!=this.df.hidden){if(this.df.hidden){if(this.frm.meta.section_style=='Tabbed'){$dh(this.mytab);}else if(this.tray_item)
this.tray_item.hide();if(this.row)this.row.hide();}else{if(this.frm.meta.section_style=='Tabbed'){$di(this.mytab);}else if(this.tray_item)
this.tray_item.show();if(this.expanded)this.row.show();}
this.set_hidden=this.df.hidden;}}
_f.ImageField=function(){this.images={};}
_f.ImageField.prototype=new Field();_f.ImageField.prototype.onmake=function(){this.no_img=$a(this.wrapper,'div','no_img');this.no_img.innerHTML="No Image";$dh(this.no_img);}
_f.ImageField.prototype.get_image_src=function(doc){if(doc.file_list){file=doc.file_list.split(',');extn=file[0].split('.');extn=extn[extn.length-1].toLowerCase();var img_extn_list=['gif','jpg','bmp','jpeg','jp2','cgm','ief','jpm','jpx','png','tiff','jpe','tif'];if(in_list(img_extn_list,extn)){var src=webnotes.request.url+"?cmd=downloadfile&file_id="+file[1];}}else{var src="";}
return src;}
_f.ImageField.prototype.onrefresh=function(){var me=this;if(!this.images[this.docname])this.images[this.docname]=$a(this.wrapper,'img');else $di(this.images[this.docname]);var img=this.images[this.docname]
for(var dn in this.images)if(dn!=this.docname)$dh(this.images[dn]);var doc=locals[this.frm.doctype][this.frm.docname];if(!this.df.options)var src=this.get_image_src(doc);else var src=webnotes.request.url+'?cmd=get_file&fname='+this.df.options+"&__account="+account_id+(__sid150?("&sid150="+__sid150):'');if(src){$dh(this.no_img);if(img.getAttribute('src')!=src)img.setAttribute('src',src);canvas=this.wrapper;canvas.img=this.images[this.docname];canvas.style.overflow="auto";$w(canvas,"100%");if(!this.col_break_width)this.col_break_width='100%';var allow_width=cint(1000*(cint(this.col_break_width)-10)/100);if((!img.naturalWidth)||cint(img.naturalWidth)>allow_width)
$w(img,allow_width+'px');}else{$ds(this.no_img);}}
_f.ImageField.prototype.set_disp=function(val){}
_f.ImageField.prototype.set=function(val){}
_f.TableField=function(){};_f.TableField.prototype=new Field();_f.TableField.prototype.with_label=0;_f.TableField.prototype.make_body=function(){if(this.perm[this.df.permlevel]&&this.perm[this.df.permlevel][READ]){if(this.df.description){this.desc_area=$a(this.parent,'div','field_description','',this.df.description)}
this.grid=new _f.FormGrid(this);if(this.frm)this.frm.grids[this.frm.grids.length]=this;this.grid.make_buttons();}}
_f.TableField.prototype.refresh=function(){if(!this.grid)return;var st=this.get_status();if(!this.df['default'])
this.df['default']='';this.grid.can_add_rows=false;this.grid.can_edit=false
if(st=='Write'){if(cur_frm.editable&&this.perm[this.df.permlevel]&&this.perm[this.df.permlevel][WRITE]){this.grid.can_edit=true;if(this.df['default'].toLowerCase()!='no toolbar')
this.grid.can_add_rows=true;}
if(cur_frm.editable&&cur_frm.doc.docstatus>0){if(this.df.allow_on_submit&&cur_frm.doc.docstatus==1){this.grid.can_edit=true;if(this.df['default'].toLowerCase()=='no toolbar'){this.grid.can_add_rows=false;}else{this.grid.can_add_rows=true;}}else{this.grid.can_add_rows=false;this.grid.can_edit=false;}}
if(this.df['default'].toLowerCase()=='no add rows'){this.grid.can_add_rows=false;}}
if(st=='Write'){this.grid.show();}else if(st=='Read'){this.grid.show();}else{this.grid.hide();}
this.grid.refresh();}
_f.TableField.prototype.set=function(v){};_f.TableField.prototype.set_input=function(v){};_f.CodeField=function(){};_f.CodeField.prototype=new Field();_f.CodeField.prototype.make_input=function(){var me=this;this.label_span.innerHTML=this.df.label;this.input=$a(this.input_area,'textarea','code_text',{fontSize:'12px'});this.myid=wn.dom.set_unique_id(this.input);this.input.set_input=function(v){if(me.editor){me.editor.setContent(v);}else{me.input.value=v;me.input.innerHTML=v;}}
this.input.onchange=function(){if(me.editor){}else{me.set(me.input.value);}
me.run_trigger();}
this.get_value=function(){if(me.editor){return me.editor.getContent();}else{return this.input.value;}}
if(this.df.fieldtype=='Text Editor'){$(me.input).tinymce({script_url:'lib/js/legacy/tiny_mce_33/tiny_mce.js',theme:"advanced",plugins:"style,inlinepopups,table",extended_valid_elements:"div[id|dir|class|align|style]",width:'100%',height:'360px',theme_advanced_buttons1:"bold,italic,underline,strikethrough,hr,|,justifyleft,justifycenter,justifyright,|,formatselect,fontselect,fontsizeselect",theme_advanced_buttons2:"bullist,numlist,|,outdent,indent,|,undo,redo,|,link,unlink,code,|,forecolor,backcolor,|,tablecontrols",theme_advanced_buttons3:"",theme_advanced_toolbar_location:"top",theme_advanced_toolbar_align:"left",content_css:"js/tiny_mce_33/custom_content.css",oninit:function(){me.init_editor();}});}else{$y(me.input,{fontFamily:'Courier, Fixed'});}}
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
_f.Grid.prototype.reset_table_width=function(){var w=0;for(var i=0,len=this.head_row.cells.length;i<len;i++){w+=cint(this.head_row.cells[i].style.width);}
this.head_tab.style.width=w+'px';this.tab.style.width=w+'px';}
_f.Grid.prototype.set_column_disp=function(fieldname,show){var cidx=this.col_idx_by_name[fieldname];if(!cidx){msgprint('Trying to hide unknown column: '+fieldname);return;}
var disp=show?'table-cell':'none';this.head_row.cells[cidx].style.display=disp;for(var i=0,len=this.tab.rows.length;i<len;i++){var cell=this.tab.rows[i].cells[cidx];cell.style.display=disp;}
this.reset_table_width();}
_f.Grid.prototype.append_row=function(idx,docname){if(!idx)idx=this.tab.rows.length;var row=this.tab.insertRow(idx);row.docname=docname;if(idx%2)var odd=true;else var odd=false;var me=this;for(var i=0;i<this.head_row.cells.length;i++){var cell=row.insertCell(i);var hc=this.head_row.cells[i];cell.style.width=hc.style.width;cell.style.display=hc.style.display;cell.row=row;cell.grid=this;cell.className='grid_cell';cell.div=$a(cell,'div','grid_cell_div');if(this.row_height){cell.div.style.height=this.row_height;}
cell.div.cell=cell;cell.div.onclick=function(e){me.cell_select(this.cell);}
if(odd){$bg(cell,this.alt_row_bg);cell.is_odd=1;cell.div.style.border='2px solid '+this.alt_row_bg;}else $bg(cell,'#FFF');if(!hc.fieldname)cell.div.style.cursor='default';}
this.set_ht();return row;}
_f.Grid.prototype.refresh_cell=function(docname,fieldname){for(var r=0;r<this.tab.rows.length;r++){if(this.tab.rows[r].docname==docname){for(var c=0;c<this.head_row.cells.length;c++){var hc=this.head_row.cells[c];if(hc.fieldname==fieldname){this.set_cell_value(this.tab.rows[r].cells[c]);}}}}}
_f.cur_grid;_f.cur_grid_ridx;_f.Grid.prototype.set_cell_value=function(cell){if(cell.row.is_newrow)return;var hc=this.head_row.cells[cell.cellIndex];if(hc.fieldname){var v=locals[hc.doctype][cell.row.docname][hc.fieldname];}else{var v=(cell.row.rowIndex+1);}
if(v==null){v='';}
var me=this;if(cell.cellIndex){var ft=hc.fieldtype;if(ft=='Link'&&cur_frm.doc.docstatus<1)ft='Data';$s(cell.div,v,ft,hc.options);}else{cell.div.style.padding='2px';cell.div.style.textAlign='left';cell.innerHTML='';var t=make_table(cell,1,3,'60px',['20px','20px','20px'],{verticalAlign:'middle',padding:'2px'});$y($td(t,0,0),{paddingLeft:'4px'});$td(t,0,0).innerHTML=cell.row.rowIndex+1;if(cur_frm.editable&&this.can_edit){var ed=$a($td(t,0,1),'i','icon-edit',{cursor:'pointer'});ed.cell=cell;ed.title='Edit Row';ed.onclick=function(){_f.cur_grid=me;_f.cur_grid_ridx=this.cell.row.rowIndex;_f.edit_record(me.doctype,this.cell.row.docname,1);}}else{cell.div.innerHTML=(cell.row.rowIndex+1);cell.div.style.cursor='default';cell.div.onclick=function(){}}}}
$(document).bind('click',function(e){var is_target_toolbar=function(){return $(e.target).parents('.grid_tbarlinks').length;}
var is_target_input=function(){return $(e.target).parents().get().indexOf(_f.cur_grid_cell)!=-1;}
if(_f.cur_grid_cell&&!is_target_input()&&!is_target_toolbar()){if(!(text_dialog&&text_dialog.display)&&!datepicker_active&&!(selector&&selector.display)&&!(cur_autosug)){_f.cur_grid_cell.grid.cell_deselect();}}});_f.Grid.prototype.cell_deselect=function(){if(_f.cur_grid_cell){var c=_f.cur_grid_cell;c.grid.remove_template(c);c.div.className='grid_cell_div';if(c.is_odd)c.div.style.border='2px solid '+c.grid.alt_row_bg;else c.div.style.border='2px solid #FFF';_f.cur_grid_cell=null;_f.cur_grid=null;}}
_f.Grid.prototype.cell_select=function(cell,ri,ci){if(ri!=null&&ci!=null)
cell=this.tab.rows[ri].cells[ci];var hc=this.head_row.cells[cell.cellIndex];if(!hc.template){this.make_template(hc);}
hc.template.perm=this.field?this.field.perm:hc.perm;if(hc.fieldname&&hc.template.get_status()=='Write'){this.cell_deselect();cell.div.style.border='2px solid #88F';_f.cur_grid_cell=cell;this.add_template(cell);}}
_f.Grid.prototype.add_template=function(cell){if(!cell.row.docname&&this.add_newrow){this.add_newrow();this.cell_select(cell);}else{var hc=this.head_row.cells[cell.cellIndex];cell.div.innerHTML='';cell.div.appendChild(hc.template.wrapper);hc.template.activate(cell.row.docname);hc.template.activated=1;if(hc.template.input&&hc.template.input.set_width){hc.template.input.set_width($(cell).width());}}}
_f.Grid.prototype.get_field=function(fieldname){for(var i=0;i<this.head_row.cells.length;i++){var hc=this.head_row.cells[i];if(hc.fieldname==fieldname){if(!hc.template){this.make_template(hc);}
return hc.template;}}
return{}}
_f.grid_date_cell='';_f.grid_refresh_date=function(){_f.grid_date_cell.grid.set_cell_value(_f.grid_date_cell);}
_f.grid_refresh_field=function(temp,input){if(input.value!=_f.get_value(temp.doctype,temp.docname,temp.df.fieldname))
if(input.onchange)input.onchange();}
_f.Grid.prototype.remove_template=function(cell){var hc=this.head_row.cells[cell.cellIndex];if(!hc.template)return;if(!hc.template.activated)return;if(hc.template.txt){if(hc.template.df.fieldtype=='Date'){_f.grid_date_cell=cell;setTimeout('_f.grid_refresh_date()',100);}
if(hc.template.txt.value)
_f.grid_refresh_field(hc.template,hc.template.txt);}else if(hc.template.input){_f.grid_refresh_field(hc.template,hc.template.input);}
if(hc.template&&hc.template.wrapper.parentNode)
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
_f.FormGrid.prototype.make_columns=function(){var gl=fields_list[this.field.df.options];if(!gl){alert('Table details not found "'+this.field.df.options+'"');}
gl.sort(function(a,b){return a.idx-b.idx});var p=this.field.perm;for(var i=0;i<gl.length;i++){if(p[this.field.df.permlevel]&&p[this.field.df.permlevel][READ]){this.insert_column(this.field.df.options,gl[i].fieldname,gl[i].fieldtype,gl[i].label,gl[i].width,gl[i].options,this.field.perm,gl[i].reqd);if(gl[i].hidden){this.set_column_disp(gl[i].fieldname,false);}}}}
_f.FormGrid.prototype.set_column_label=function(fieldname,label){for(var i=0;i<this.head_row.cells.length;i++){var c=this.head_row.cells[i];if(c.fieldname==fieldname){c.innerHTML='<div class="grid_head_div">'+label+'</div>';c.cur_label=label;break;}}}
_f.FormGrid.prototype.refresh=function(){var docset=getchildren(this.doctype,this.field.frm.docname,this.field.df.fieldname,this.field.frm.doctype);var data=[];for(var i=0;i<docset.length;i++){locals[this.doctype][docset[i].name].idx=i+1;data[data.length]=docset[i].name;}
this.set_data(data);if(_f.frm_dialog&&_f.frm_dialog.dialog.display&&_f.frm_dialog.cur_frm){_f.frm_dialog.cur_frm.refresh();}}
_f.FormGrid.prototype.set_unsaved=function(){locals[cur_frm.doctype][cur_frm.docname].__unsaved=1;cur_frm.set_heading();}
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
+footer;return finished;},get_letter_head:function(){var cp=wn.control_panel;var lh='';if(cur_frm.doc.letter_head){lh=cstr(_p.letter_heads[cur_frm.doc.letter_head]);}else if(cp.letter_head){lh=cp.letter_head;}
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
   }",print_std:function(no_letterhead){var docname=cur_frm.docname;var doctype=cur_frm.doctype;var data=getchildren('DocField',doctype,'fields','DocType');var layout=_p.add_layout(doctype);this.pf_list=[layout];var me=this;me.layout=layout;$.extend(this,{build_head:function(doctype,docname){var h1_style={fontSize:'22px',marginBottom:'8px'}
var h1=$a(me.layout.cur_row.header,'h1','',h1_style);h1.innerHTML=cur_frm.pformat[docname]?cur_frm.pformat[docname]:get_doctype_label(doctype);var h2_style={fontSize:'16px',color:'#888',marginBottom:'8px',paddingBottom:'8px',borderBottom:(me.layout.with_border?'0px':'1px solid #000')}
var h2=$a(me.layout.cur_row.header,'div','',h2_style);h2.innerHTML=docname;},build_data:function(data,doctype,docname){if(data[0]&&data[0].fieldtype!="Section Break"){me.layout.addrow();if(data[0].fieldtype!="Column Break"){me.layout.addcell();}}
$.extend(this,{generate_custom_html:function(field,doctype,docname){var container=$a(me.layout.cur_cell,'div');container.innerHTML=cur_frm.pformat[field.fieldname](locals[doctype][docname]);},render_normal:function(field,data,i){switch(field.fieldtype){case'Section Break':me.layout.addrow();if(data[i+1]&&data[i+1].fieldtype!='Column Break'){me.layout.addcell();}
break;case'Column Break':me.layout.addcell(field.width,field.label);break;case'Table':var table=print_table(doctype,docname,field.fieldname,field.options,null,null,null,null);me.layout=_p.print_std_add_table(table,me.layout,me.pf_list,doctype,no_letterhead);break;case'HTML':var div=$a(me.layout.cur_cell,'div');div.innerHTML=field.options;break;case'Code':var div=$a(me.layout.cur_cell,'div');var val=_f.get_value(doctype,docname,field.fieldname);div.innerHTML='<div>'+field.label+': </div><pre style="font-family: Courier, Fixed;">'+(val?val:'')+'</pre>';break;case'Text Editor':var div=$a(me.layout.cur_cell,'div');var val=_f.get_value(doctype,docname,field.fieldname);div.innerHTML=val?val:'';break;default:_p.print_std_add_field(doctype,docname,field,me.layout);break;}}});for(var i=0;i<data.length;i++){var fieldname=data[i].fieldname?data[i].fieldname:data[i].label;var field=fieldname?get_field(doctype,fieldname,docname):data[i];if(!field.print_hide){if(cur_frm.pformat[field.fieldname]){this.generate_custom_html(field,doctype,docname);}else{this.render_normal(field,data,i);}}}
me.layout.close_borders();},build_html:function(){var html='';for(var i=0;i<me.pf_list.length;i++){if(me.pf_list[i].wrapper){html+=me.pf_list[i].wrapper.innerHTML;}else if(me.pf_list[i].innerHTML){html+=me.pf_list[i].innerHTML;}else{html+=me.pf_list[i];}}
this.pf_list=[];return html;}});this.build_head(doctype,docname);this.build_data(data,doctype,docname);var html=this.build_html();return html;},add_layout:function(doctype){var layout=new Layout();layout.addrow();if(locals['DocType'][doctype].print_outline=='Yes'){layout.with_border=1}
return layout;},print_std_add_table:function(t,layout,pf_list,dt,no_letterhead){if(t.appendChild){layout.cur_cell.appendChild(t);}else{page_break='\n\
    <div style = "page-break-after: always;" \
    class = "page_break"></div><div class="page-settings"></div>';for(var i=0;i<t.length-1;i++){layout.cur_cell.appendChild(t[i]);layout.close_borders();pf_list.push(page_break);layout=_p.add_layout(dt,no_letterhead);pf_list.push(layout);layout.addrow();layout.addcell();var div=$a(layout.cur_cell,'div');div.innerHTML='Continued from previous page...';div.style.padding='4px';}
layout.cur_cell.appendChild(t[t.length-1]);}
return layout;},print_std_add_field:function(dt,dn,f,layout){var val=_f.get_value(dt,dn,f.fieldname);if(f.fieldtype!='Button'){if(val||in_list(['Float','Int','Currency'],f.fieldtype)){row=_p.field_tab(layout.cur_cell);row.cells[0].innerHTML=f.label?f.label:f.fieldname;$s(row.cells[1],val,f.fieldtype);if(f.fieldtype=='Currency'){$y(row.cells[1],{textAlign:'left'});}}}},field_tab:function(layout_cell){var tab=$a(layout_cell,'table','',{width:'100%'});var row=tab.insertRow(0);_p.row=row;row.insertCell(0);row.insertCell(1);row.cells[0].className='datalabelcell';row.cells[1].className='datainputcell';return row;}});print_table=function(dt,dn,fieldname,tabletype,cols,head_labels,widths,condition,cssClass,modifier,hide_empty){var me=this;$.extend(this,{flist:(function(){var f_list=[];var fl=fields_list[tabletype];if(fl){for(var i=0;i<fl.length;i++){f_list.push(copy_dict(fl[i]));}}
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
_e.email_as_field='email_id';_e.email_as_dt='Contact';_e.email_as_in='email_id,contact_name';sendmail=function(emailto,emailfrom,cc,subject,message,fmt,with_attachments){var fn=function(html){$c('webnotes.utils.email_lib.send_form',{'sendto':emailto,'sendfrom':emailfrom?emailfrom:'','cc':cc?cc:'','subject':subject,'message':replace_newlines(message),'body':html,'full_domain':wn.urllib.get_base_url(),'with_attachments':with_attachments?1:0,'dt':cur_frm.doctype,'dn':cur_frm.docname},function(r,rtxt){});}
_p.build(fmt,fn);}
_e.make=function(){var d=new Dialog(440,440,"Send Email");var email_go=function(){var emailfrom=d.widgets['From'].value;var emailto=d.widgets['To'].value;if(!emailfrom)
emailfrom=user_email;var email_list=emailto.split(/[,|;]/);var valid=1;for(var i=0;i<email_list.length;i++){if(!validate_email(email_list[i])){msgprint('error:'+email_list[i]+' is not a valid email id');valid=0;}}
if(emailfrom&&!validate_email(emailfrom)){msgprint('error:'+emailfrom+' is not a valid email id. To change the default please click on Profile on the top right of the screen and change it.');return;}
if(!valid)return;var cc=emailfrom;if(!emailfrom){emailfrom=wn.control_panel.auto_email_id;cc='';}
sendmail(emailto,emailfrom,emailfrom,d.widgets['Subject'].value,d.widgets['Message'].value,sel_val(cur_frm.print_sel),d.widgets['Send With Attachments'].checked);_e.dialog.hide();}
d.onhide=function(){hide_autosuggest();}
d.make_body([['Data','To','Example: abc@hotmail.com, xyz@yahoo.com'],['Select','Format'],['Data','Subject'],['Data','From','Optional'],['Check','Send With Attachments','Will send all attached documents (if any)'],['Text','Message'],['Button','Send',email_go]]);d.widgets['From'].value=(user_email?user_email:'');$td(d.rows['Format'].tab,0,1).cur_sel=d.widgets['Format'];var opts={script:'',json:true,maxresults:10};wn.require('lib/js/legacy/widgets/autosuggest.js');var as=new AutoSuggest(d.widgets['To'],opts);as.custom_select=function(txt,sel){var r='';var tl=txt.split(',');for(var i=0;i<tl.length-1;i++)r=r+tl[i]+',';r=r+(r?' ':'')+sel;if(r[r.length-1]==NEWLINE)r=substr(0,r.length-1);return r;}
var emailto=d.widgets['To']
as.set_input_value=function(new_txt){if(emailto.value&&emailto.value.indexOf(',')!=-1){var txt=emailto.value.split(',');txt.splice(txt.length-1,1,new_txt);for(var i=0;i<txt.length-1;i++)txt[i]=strip(txt[i]);emailto.value=txt.join(', ');}else{emailto.value=new_txt;}}
as.doAjaxRequest=function(txt){var pointer=as;var q='';var last_txt=txt.split(',');last_txt=last_txt[last_txt.length-1];var call_back=function(r,rt){as.aSug=[];if(!r.cl)return;for(var i=0;i<r.cl.length;i++){as.aSug.push({'id':r.cl[i],'value':r.cl[i],'info':''});}
as.createList(as.aSug);}
$c('webnotes.utils.email_lib.get_contact_list',{'select':_e.email_as_field,'from':_e.email_as_dt,'where':_e.email_as_in,'txt':(last_txt?strip(last_txt):'%')},call_back);return;}
var sel;_e.dialog=d;}
/*
 *	lib/js/legacy/widgets/form/clientscriptAPI.js
 */
$c_get_values=function(args,doc,dt,dn,user_callback){var call_back=function(r,rt){if(!r.message)return;if(user_callback)user_callback(r.message);var fl=args.fields.split(',');for(var i in fl){locals[dt][dn][fl[i]]=r.message[fl[i]];if(args.table_field)
refresh_field(fl[i],dn,args.table_field);else
refresh_field(fl[i]);}}
$c('webnotes.widgets.form.utils.get_fields',args,call_back);}
get_server_fields=function(method,arg,table_field,doc,dt,dn,allow_edit,call_back){if(!allow_edit)freeze('Fetching Data...');$c('runserverobj',args={'method':method,'docs':compress_doclist([doc]),'arg':arg},function(r,rt){if(r.message){var d=locals[dt][dn];var field_dict=r.message;for(var key in field_dict){d[key]=field_dict[key];if(table_field)refresh_field(key,d.name,table_field);else refresh_field(key);}}
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
hide_field=function(n){function _hide_field(n,hidden){var df=get_field(cur_frm.doctype,n,cur_frm.docname);if(df)df.hidden=hidden;refresh_field(n);}
if(cur_frm){if(n.substr)_hide_field(n,1);else{for(var i in n)_hide_field(n[i],1)}}}
unhide_field=function(n){function _hide_field(n,hidden){var df=get_field(cur_frm.doctype,n,cur_frm.docname);if(df)df.hidden=hidden;refresh_field(n);}
if(cur_frm){if(n.substr)_hide_field(n,0);else{for(var i in n)_hide_field(n[i],0)}}}
get_field_obj=function(fn){return cur_frm.fields_dict[fn];}
/*
 *	lib/js/legacy/widgets/form/form_comments.js
 */
wn.widgets.form.comments={n_comments:{},comment_list:{},sync:function(dt,dn,r){var f=wn.widgets.form.comments;f.n_comments[dn]=r.n_comments;f.comment_list[dn]=r.comment_list;},add:function(input,dt,dn,callback){$c('webnotes.widgets.form.comments.add_comment',wn.widgets.form.comments.get_args(input,dt,dn),function(r,rt){wn.widgets.form.comments.update_comment_list(input,dt,dn);input.value='';callback(input,dt,dn);});},remove:function(dt,dn,comment_id,callback){$c('webnotes.widgets.form.comments.remove_comment',{id:comment_id,dt:dt,dn:dn},callback);},get_args:function(input,dt,dn){return{comment:input.value,comment_by:user,comment_by_fullname:user_fullname,comment_doctype:dt,comment_docname:dn}},update_comment_list:function(input,dt,dn){var f=wn.widgets.form.comments;f.n_comments[dn]=cint(f.n_comments[dn])+1;f.comment_list[dn]=add_lists([f.get_args(input,dt,dn)],f.comment_list[dn]);}}
CommentList=function(parent,dt,dn){this.wrapper=$a(parent,'div','',{margin:'16px'});this.input_area=$a(this.wrapper,'div','',{margin:'2px'});this.lst_area=$a(this.wrapper,'div','',{margin:'2px'});this.make_input();this.make_lst();this.dt;this.dn;}
CommentList.prototype.run=function(){this.lst.run();}
CommentList.prototype.make_input=function(){var me=this;this.input=$a(this.input_area,'textarea','',{height:'60px',width:'300px',fontSize:'14px'});this.btn=$btn($a(this.input_area,'div'),'Post',function(){me.add_comment();},{marginTop:'8px'});}
CommentList.prototype.add_comment=function(){var me=this;var callback=function(input,dt,dn){me.lst.run();}
wn.widgets.form.comments.add(this.input,cur_frm.docname,cur_frm.doctype,callback)}
CommentList.prototype.make_lst=function(){if(!this.lst){var l=new Listing('Comments',1);var me=this;l.colwidths=['100%'];l.opts.hide_export=1;l.opts.hide_print=1;l.opts.hide_refresh=1;l.opts.no_border=1;l.opts.hide_rec_label=0;l.opts.show_calc=0;l.opts.round_corners=0;l.opts.alt_cell_style={};l.opts.cell_style={padding:'3px'};l.no_rec_message='No comments yet. Be the first one to comment!';l.get_query=function(){this.query=repl("select t1.name, t1.comment, t1.comment_by, '', \
   t1.creation, t1.comment_doctype, t1.comment_docname, \
   ifnull(concat_ws(' ',ifnull(t2.first_name,''),ifnull(t2.middle_name,''),\
   ifnull(t2.last_name,'')),''), '', \
   DAYOFMONTH(t1.creation), MONTHNAME(t1.creation), YEAR(t1.creation), \
   hour(t1.creation), minute(t1.creation), second(t1.creation) \
   from `tabComment Widget Record` t1, `tabProfile` t2 \
   where t1.comment_doctype = '%(dt)s' and t1.comment_docname = '%(dn)s' \
   and t1.comment_by = t2.name order by t1.creation desc",{dt:me.dt,dn:me.dn});this.query_max=repl("select count(name) from `tabComment Widget Record` where \
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
wn.widgets.form.sidebar={Sidebar:function(form){var me=this;this.form=form;this.opts={sections:[{title:'Actions',items:[{type:'link',label:'New',icon:'icon-plus',display:function(){return in_list(profile.can_create,form.doctype)},onclick:function(){new_doc(me.form.doctype)}},{type:'link',label:'Refresh',icon:'icon-refresh',onclick:function(){me.form.reload_doc()}},{type:'link',label:'Print',display:function(){return!(me.form.doc.__islocal||me.form.meta.allow_print);},icon:'icon-print',onclick:function(){me.form.print_doc()}},{type:'link',label:'Email',display:function(){return!(me.form.doc.__islocal||me.form.meta.allow_email);},icon:'icon-envelope',onclick:function(){me.form.email_doc()}},{type:'link',label:'Copy',display:function(){return in_list(profile.can_create,me.form.doctype)&&!me.form.meta.allow_copy},icon:'icon-file',onclick:function(){me.form.copy_doc()}},{type:'link',label:'Delete',display:function(){return me.form.meta.allow_trash&&cint(me.form.doc.docstatus)!=2&&(!me.form.doc.__islocal)&&me.form.perm[0][CANCEL]},icon:'icon-remove-sign',onclick:function(){me.form.savetrash()}}]},{title:'Assign To',render:function(wrapper){me.form.assign_to=new wn.widgets.form.sidebar.AssignTo(wrapper,me,me.form.doctype,me.form.docname);},display:function(){if(me.form.doc.__local)return false;else return true;}},{title:'Attachments',render:function(wrapper){me.form.attachments=new wn.widgets.form.sidebar.Attachments(wrapper,me,me.form.doctype,me.form.docname);},display:function(){return me.form.meta.allow_attach}},{title:'Comments',render:function(wrapper){new wn.widgets.form.sidebar.Comments(wrapper,me,me.form.doctype,me.form.docname);},display:function(){return!me.form.doc.__islocal}},{title:'Tags',render:function(wrapper){me.form.taglist=new TagList(wrapper,me.form.doc._user_tags?me.form.doc._user_tags.split(','):[],me.form.doctype,me.form.docname,0,function(){});},display:function(){return!me.form.doc.__islocal}}]}
this.refresh=function(){var parent=this.form.page_layout.sidebar_area;if(!this.sidebar){this.sidebar=new wn.widgets.PageSidebar(parent,this.opts);}else{this.sidebar.refresh();}}}}
/*
 *	lib/js/legacy/wn/widgets/form/comments.js
 */
wn.widgets.form.sidebar.Comments=function(parent,sidebar,doctype,docname){var me=this;this.sidebar=sidebar;this.doctype=doctype;this.docname=docname;this.refresh=function(){$c('webnotes.widgets.form.comments.get_comments',{dt:me.doctype,dn:me.docname,limit:5},function(r,rt){wn.widgets.form.comments.sync(me.doctype,me.docname,r);me.make_body();});}
this.make_body=function(){if(this.wrapper)this.wrapper.innerHTML='';else this.wrapper=$a(parent,'div','sidebar-comment-wrapper');this.input=$a_input(this.wrapper,'text');this.btn=$btn(this.wrapper,'Post',function(){me.add_comment()},{marginLeft:'8px'});this.render_comments()}
this.render_comments=function(){var f=wn.widgets.form.comments;var cl=f.comment_list[me.docname]
this.msg=$a(this.wrapper,'div','sidebar-comment-message');if(cl){this.msg.innerHTML=cl.length+' out of '+f.n_comments[me.docname]+' comments';if(f.n_comments[me.docname]>cl.length){this.msg.innerHTML+=' <span class="link_type" onclick="cur_frm.show_comments()">Show all</span>'}
for(var i=0;i<cl.length;i++){this.render_one_comment(cl[i]);}}else{this.msg.innerHTML='Be the first one to comment.'}}
this.render_one_comment=function(det){$a(this.wrapper,'div','social sidebar-comment-text','',det.comment);$a(this.wrapper,'div','sidebar-comment-info','',comment_when(det.creation)+' by '+det.comment_by_fullname);}
this.add_comment=function(){if(!this.input.value)return;this.btn.set_working();wn.widgets.form.comments.add(this.input,me.doctype,me.docname,function(){me.btn.done_working();me.make_body();});}
this.refresh();}
/*
 *	lib/js/legacy/wn/widgets/form/attachments.js
 */
wn.widgets.form.sidebar.Attachments=function(parent,sidebar,doctype,docname){var me=this;this.frm=sidebar.form;this.make=function(){if(this.wrapper)this.wrapper.innerHTML='';else this.wrapper=$a(parent,'div','sidebar-comment-wrapper');this.attach_wrapper=$a(this.wrapper,'div');if(this.frm.doc.__islocal){this.attach_wrapper.innerHTML='Attachments can be uploaded after saving'
return;}
var n=this.frm.doc.file_list?this.frm.doc.file_list.split('\n').length:0;if(n<this.frm.meta.max_attachments||!this.frm.meta.max_attachments){this.btn=$btn($a(this.wrapper,'div','sidebar-comment-message'),'Add',function(){me.add_attachment()});}
this.render();}
this.render=function(){this.attach_wrapper.innerHTML=''
var doc=locals[me.frm.doctype][me.frm.docname];var fl=doc.file_list?doc.file_list.split('\n'):[];for(var i=0;i<fl.length;i++){new wn.widgets.form.sidebar.Attachment(this.attach_wrapper,fl[i],me.frm)}}
this.add_attachment=function(){if(!this.dialog){this.dialog=new wn.widgets.Dialog({title:'Add Attachment',width:400})
$y(this.dialog.body,{margin:'13px'})
this.dialog.make();}
this.dialog.body.innerHTML='';this.dialog.show();this.uploader=new Uploader(this.dialog.body,{from_form:1,doctype:doctype,docname:docname,at_id:this.at_id},wn.widgets.form.file_upload_done);}
this.make();}
wn.widgets.form.sidebar.Attachment=function(parent,filedet,frm){filedet=filedet.split(',')
this.filename=filedet[0];this.fileid=filedet[1];this.frm=frm;var me=this;this.wrapper=$a(parent,'div','sidebar-comment-message');this.remove_fileid=function(){var doc=locals[me.frm.doctype][me.frm.docname];var fl=doc.file_list.split('\n');new_fl=[];for(var i=0;i<fl.length;i++){if(fl[i].split(',')[1]!=me.fileid)new_fl.push(fl[i]);}
doc.file_list=new_fl.join('\n');}
var display_name=this.fileid;if(this.fileid.substr(0,8)=='FileData')
display_name=this.filename;this.ln=$a(this.wrapper,'a','link_type',{fontSize:'11px'},display_name);this.ln.href='files/'+this.fileid;this.ln.target='_blank';this.del=$a(this.wrapper,'span','close','','&#215;');this.del.onclick=function(){var yn=confirm("Are you sure you want to delete the attachment?")
if(yn){var callback=function(r,rt){locals[me.frm.doctype][me.frm.docname].modified=r.message;$dh(me.wrapper);me.remove_fileid();frm.refresh();}
$c('webnotes.widgets.form.utils.remove_attach',args={'fid':me.fileid,dt:me.frm.doctype,dn:me.frm.docname},callback);}}}
wn.widgets.form.file_upload_done=function(doctype,docname,fileid,filename,at_id,new_timestamp){var at_id=cint(at_id);var doc=locals[doctype][docname];if(doc.file_list){var fl=doc.file_list.split('\n')
fl.push(filename+','+fileid)
doc.file_list=fl.join('\n');}
else
doc.file_list=filename+','+fileid;doc.modified=new_timestamp;var frm=frms[doctype];frm.attachments.dialog.hide();msgprint('File Uploaded Sucessfully.');frm.refresh();}
/*
 *	lib/js/legacy/wn/widgets/form/assign_to.js
 */
wn.widgets.form.sidebar.AssignTo=Class.extend({init:function(parent,sidebar,doctype,docname){var me=this;this.doctype=doctype;this.name=docname;this.wrapper=$a(parent,'div','sidebar-comment-wrapper');this.body=$a(this.wrapper,'div');this.add_btn=$btn($a(this.wrapper,'div','sidebar-comment-message'),'Assign',function(){me.add();})
this.refresh();},refresh:function(){var me=this;$c('webnotes.widgets.form.assign_to.get',{doctype:me.doctype,name:me.name},function(r,rt){me.render(r.message)})},render:function(d){var me=this;$(this.body).empty();if(this.dialog){this.dialog.hide();}
for(var i=0;i<d.length;i++){$(this.body).append(repl('<div>%(owner)s \
    <a class="close" href="#" data-owner="%(owner)s">&#215</a></div>',d[i]))}
$(this.body).find('a.close').click(function(){$c('webnotes.widgets.form.assign_to.remove',{doctype:me.doctype,name:me.name,assign_to:$(this).attr('data-owner')},function(r,rt){me.render(r.message);});return false;});},add:function(){var me=this;if(!me.dialog){me.dialog=new wn.widgets.Dialog({title:'Add to To Do',width:350,fields:[{fieldtype:'Link',fieldname:'assign_to',options:'Profile',label:'Assign To',description:'Add to To Do List of',reqd:true},{fieldtype:'Data',fieldname:'description',label:'Comment','default':'Assigned by '+user},{fieldtype:'Date',fieldname:'date',label:'Complete By'},{fieldtype:'Select',fieldname:'priority',label:'Priority',options:'Low\nMedium\nHigh','default':'Medium'},{fieldtype:'Check',fieldname:'notify',label:'Notify By Email'},{fieldtype:'Button',label:'Add',fieldname:'add_btn'}]});me.dialog.fields_dict.add_btn.input.onclick=function(){var assign_to=me.dialog.fields_dict.assign_to.get_value();if(assign_to){$c('webnotes.widgets.form.assign_to.add',{doctype:me.doctype,name:me.name,assign_to:assign_to,description:me.dialog.fields_dict.description.get_value(),priority:me.dialog.fields_dict.priority.get_value(),date:me.dialog.fields_dict.date.get_value(),notify:me.dialog.fields_dict.notify.get_value()},function(r,rt){me.render(r.message);});}}}
me.dialog.clear();me.dialog.show();}});
/*
 *	lib/js/legacy/app.js
 */
var popup_cont;var session={};if(!wn)var wn={};function startup(){popup_cont=$a(document.getElementsByTagName('body')[0],'div');var setup_globals=function(r){wn.boot=r;profile=r.profile;user=r.profile.name;user_fullname=wn.user_info(user).fullname;user_defaults=profile.defaults;user_roles=profile.roles;user_email=profile.email;home_page=r.home_page;_p.letter_heads=r.letter_heads;sys_defaults=r.sysdefaults;session.rt=profile.can_read;if(r.ipinfo)session.ipinfo=r.ipinfo;session.dt_labels=r.dt_labels;session.rev_dt_labels={}
if(r.dt_labels){for(key in r.dt_labels)session.rev_dt_labels[r.dt_labels[key]]=key;}
wn.control_panel=r.control_panel;}
var setup_history=function(r){rename_observers.push(nav_obj);}
var callback=function(r,rt){if(r.exc)console.log(r.exc);setup_globals(r);setup_history();var a=new Body();page_body.run_startup_code();for(var i=0;i<startup_list.length;i++){startup_list[i]();}
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
var resize_observers=[]
function set_resize_observer(fn){if(resize_observers.indexOf(fn)==-1)resize_observers.push(fn);}
window.onresize=function(){return;var ht=get_window_height();for(var i=0;i<resize_observers.length;i++){resize_observers[i](ht);}}
get_window_height=function(){var ht=window.innerHeight?window.innerHeight:document.documentElement.offsetHeight?document.documentElement.offsetHeight:document.body.offsetHeight;return ht;}
/*
 *	js/app.js
 */
wn.app={name:'ERPNext',license:'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',source:'https://github.com/webnotes/erpnext',publisher:'Web Notes Technologies Pvt Ltd, Mumbai',copyright:'&copy; Web Notes Technologies Pvt Ltd',version:'2.'+window._version_number}
wn.modules_path='erpnext';wn.settings.no_history=true;$(document).bind('ready',function(){startup();});$(document).bind('toolbar_setup',function(){$('.brand').html('<b>erp</b>next\
  <i class="icon-home icon-white navbar-icon-home" ></i>').hover(function(){$(this).find('.icon-home').addClass('navbar-icon-home-hover');},function(){$(this).find('.icon-home').removeClass('navbar-icon-home-hover');});})
/*
 *	erpnext/startup/startup.js
 */
var current_module;var is_system_manager=0;wn.provide('erpnext.startup');erpnext.modules={'Selling':'selling-home','Accounts':'accounts-home','Stock':'stock-home','Buying':'buying-home','Support':'support-home','Projects':'projects-home','Production':'production-home','Website':'website-home','HR':'hr-home','Setup':'Setup','Activity':'activity','To Do':'todo','Calendar':'calendar','Messages':'messages','Knowledge Base':'questions','Dashboard':'dashboard'}
erpnext.startup.set_globals=function(){pscript.is_erpnext_saas=cint(wn.control_panel.sync_with_gateway)
if(inList(user_roles,'System Manager'))is_system_manager=1;}
erpnext.startup.start=function(){$('#startup_div').html('Starting up...').toggle(true);erpnext.startup.set_globals();if(wn.boot.custom_css){set_style(wn.boot.custom_css);}
if(wn.boot.user_background){erpnext.set_user_background(wn.boot.user_background);}
if(user=='Guest'){if(wn.boot.website_settings.title_prefix){wn.title_prefix=wn.boot.website_settings.title_prefix;}}else{wn.boot.profile.allow_modules=wn.boot.profile.allow_modules.concat(['To Do','Knowledge Base','Calendar','Activity','Messages'])
erpnext.toolbar.setup();erpnext.startup.set_periodic_updates();$('footer').html('<div class="web-footer erpnext-footer">\
   <a href="#!attributions">ERPNext | Attributions and License</a></div>');if(in_list(user_roles,'System Manager')&&(wn.boot.setup_complete=='No')){wn.require("erpnext/startup/js/complete_setup.js");erpnext.complete_setup();}}
$('#startup_div').toggle(false);}
show_chart_browser=function(nm,chart_type){var call_back=function(){if(nm=='Sales Browser'){var sb_obj=new SalesBrowser();sb_obj.set_val(chart_type);}
else if(nm=='Accounts Browser')
pscript.make_chart(chart_type);}
loadpage(nm,call_back);}
var update_messages=function(reset){if(inList(['Guest'],user)){return;}
if(!reset){$c_page('home','event_updates','get_unread_messages',null,function(r,rt){if(!r.exc){page_body.wntoolbar.set_new_comments(r.message);var circle=$('#msg_count')
if(circle){if(r.message.length){circle.find('span:first').text(r.message.length);circle.toggle(true);}else{circle.toggle(false);}}}else{clearInterval(wn.updates.id);}});}else{page_body.wntoolbar.set_new_comments(0);$('#msg_count').toggle(false);}}
erpnext.startup.set_periodic_updates=function(){wn.updates={};if(wn.updates.id){clearInterval(wn.updates.id);}
wn.updates.id=setInterval(update_messages,60000);}
erpnext.set_user_background=function(src){set_style(repl('body { background: url("files/%(src)s") repeat;}',{src:src}))}
$(document).bind('startup',function(){erpnext.startup.start();});
/*
 *	erpnext/startup/js/modules.js
 */
wn.provide('erpnext.module_page');erpnext.module_page.setup_page=function(module,wrapper){erpnext.module_page.hide_links(wrapper);erpnext.module_page.make_list(module,wrapper);$(wrapper).find("a[title]").tooltip({delay:{show:500,hide:100}});}
erpnext.module_page.hide_links=function(wrapper){$(wrapper).find('[href*="List/"]').each(function(){var href=$(this).attr('href');var dt=href.split('/')[1];if(wn.boot.profile.all_read.indexOf(get_label_doctype(dt))==-1){var txt=$(this).text();$(this).parent().css('color','#999').html(txt);}});$(wrapper).find('[data-doctype]').each(function(){var dt=$(this).attr('data-doctype');if(wn.boot.profile.all_read.indexOf(dt)==-1){var txt=$(this).text();$(this).parent().css('color','#999').html(txt);}});$(wrapper).find('[href*="Form/"]').each(function(){var href=$(this).attr('href');var dt=href.split('/')[1];if(wn.boot.profile.all_read.indexOf(get_label_doctype(dt))==-1){var txt=$(this).text();$(this).parent().css('color','#999').html(txt);}});}
erpnext.module_page.make_list=function(module,wrapper){wrapper.list=new wn.ui.Listing({parent:$(wrapper).find('.reports-list').get(0),method:'utilities.get_report_list',render_row:function(row,data){if(!data.parent_doc_type)data.parent_doc_type=data.doc_type;$(row).html(repl('<a href="#!Report/%(doc_type)s/%(criteria_name)s" \
    data-doctype="%(parent_doc_type)s">\
    %(criteria_name)s</a>',data))},args:{module:module},no_refresh:true,callback:function(r){erpnext.module_page.hide_links(wrapper)}});wrapper.list.run();}
/*
 *	erpnext/startup/js/toolbar.js
 */
wn.provide('erpnext.toolbar');erpnext.toolbar.setup=function(){erpnext.toolbar.add_modules();$('#toolbar-user').append('<li><a href="#!profile-settings">Profile Settings</a></li>');$('.navbar .pull-right').append('\
  <li><a href="#!messages" title="Unread Messages"><span class="navbar-new-comments"></span></a></li>');$('.navbar .pull-right').prepend('<li class="dropdown">\
  <a class="dropdown-toggle" data-toggle="dropdown" href="#" \
   onclick="return false;">Help<b class="caret"></b></a>\
  <ul class="dropdown-menu" id="toolbar-help">\
  </ul></li>')
$('#toolbar-help').append('<li><a href="http://erpnext.blogspot.com/2011/03/erpnext-help.html" target="_blank">\
  Documentation</a></li>')
$('#toolbar-help').append('<li><a href="http://groups.google.com/group/erpnext-user-forum" target="_blank">\
  Forum</a></li>')
$('#toolbar-help').append('<li><a href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">\
  Live Chat (Office Hours)</a></li>')
if(pscript.is_erpnext_saas&&is_system_manager){$('#toolbar-user').append('<li><a href="#billing">Billing</a></li>')}
$.extend(page_body.wntoolbar,{set_new_comments:function(new_comments){var navbar_nc=$('.navbar-new-comments');if(new_comments&&new_comments.length>0){navbar_nc.text(new_comments.length);navbar_nc.addClass('navbar-new-comments-true')
$.each(new_comments,function(i,v){var msg='New Message: '+(v[1].length<=100?v[1]:(v[1].substr(0,100)+"..."));var id=v[0].replace('/','-');if(!$('#'+id)[0]){show_alert(msg,id);}})}else{navbar_nc.removeClass('navbar-new-comments-true');navbar_nc.text(0);}}});page_body.wntoolbar.set_new_comments();}
erpnext.toolbar.add_modules=function(){$('<li class="dropdown">\
  <a class="dropdown-toggle" data-toggle="dropdown" href="#"\
   onclick="return false;">Modules<b class="caret"></b></a>\
  <ul class="dropdown-menu modules">\
  </ul>\
  </li>').prependTo('.navbar .nav:first');if(wn.boot.modules_list)
wn.boot.modules_list=JSON.parse(wn.boot.modules_list);else
wn.boot.modules_list=keys(erpnext.modules).sort();for(var i in wn.boot.modules_list){var m=wn.boot.modules_list[i]
if(m!='Setup'&&wn.boot.profile.allow_modules.indexOf(m)!=-1){args={module:m,module_page:erpnext.modules[m],module_label:m=='HR'?'Human Resources':m}
$('.navbar .modules').append(repl('<li><a href="#!%(module_page)s" \
    data-module="%(module)s">%(module_label)s</a></li>',args));}}
if(user_roles.indexOf("Accounts Manager")!=-1){$('.navbar .modules').append('<li><a href="#!dashboard" \
   data-module="Dashboard">Dashboard</a></li>');}
if(user_roles.indexOf("System Manager")!=-1){$('.navbar .modules').append('<li class="divider"></li>\
  <li><a href="#!Setup" data-module="Setup">Setup</a></li>');}}
/*
 *	erpnext/startup/js/feature_setup.js
 */
pscript.feature_dict={'fs_projects':{'Bill Of Materials':{'fields':['project_name']},'Delivery Note':{'fields':['project_name']},'Payable Voucher':{'fields':['project_name']},'Production Order':{'fields':['project_name']},'Purchase Order':{'fields':['project_name']},'Purchase Receipt':{'fields':['project_name']},'Receivable Voucher':{'fields':['project_name']},'Sales Order':{'fields':['project_name']},'Stock Entry':{'fields':['project_name']},'Timesheet':{'timesheet_details':['project_name']}},'fs_packing_details':{},'fs_discounts':{'Delivery Note':{'delivery_note_details':['adj_rate']},'Quotation':{'quotation_details':['adj_rate']},'Receivable Voucher':{'entries':['adj_rate']},'Sales Order':{'sales_order_details':['adj_rate','ref_rate']}},'fs_purchase_discounts':{'Purchase Order':{'po_details':['purchase_ref_rate','discount_rate','import_ref_rate']},'Purchase Receipt':{'purchase_receipt_details':['purchase_ref_rate','discount_rate','import_ref_rate']},'Payable Voucher':{'entries':['purchase_ref_rate','discount_rate','import_ref_rate']}},'fs_brands':{'Delivery Note':{'delivery_note_details':['brand']},'Indent':{'indent_details':['brand']},'Item':{'fields':['brand']},'Purchase Order':{'po_details':['brand']},'Payable Voucher':{'entries':['brand']},'Quotation':{'quotation_details':['brand']},'Receivable Voucher':{'entries':['brand']},'Sales BOM':{'fields':['new_item_brand']},'Sales Order':{'sales_order_details':['brand']},'Serial No':{'fields':['brand']}},'fs_after_sales_installations':{'Delivery Note':{'fields':['installation_status','per_installed'],'delivery_note_details':['installed_qty']}},'fs_item_batch_nos':{'Delivery Note':{'delivery_note_details':['batch_no']},'Item':{'fields':['has_batch_no']},'Purchase Receipt':{'purchase_receipt_details':['batch_no']},'QA Inspection Report':{'fields':['batch_no']},'Sales and Pruchase Return Wizard':{'return_details':['batch_no']},'Receivable Voucher':{'entries':['batch_no']},'Stock Entry':{'mtn_details':['batch_no']},'Stock Ledger Entry':{'fields':['batch_no']}},'fs_item_serial_nos':{'Customer Issue':{'fields':['serial_no']},'Delivery Note':{'delivery_note_details':['serial_no'],'packing_details':['serial_no']},'Installation Note':{'installed_item_details':['serial_no']},'Item':{'fields':['has_serial_no']},'Maintenance Schedule':{'item_maintenance_details':['serial_no'],'maintenance_schedule_details':['serial_no']},'Maintenance Visit':{'maintenance_visit_details':['serial_no']},'Purchase Receipt':{'purchase_receipt_details':['serial_no']},'QA Inspection Report':{'fields':['item_serial_no']},'Sales and Pruchase Return Wizard':{'return_details':['serial_no']},'Receivable Voucher':{'entries':['serial_no']},'Stock Entry':{'mtn_details':['serial_no']},'Stock Ledger Entry':{'fields':['serial_no']}},'fs_item_group_in_details':{'Delivery Note':{'delivery_note_details':['item_group']},'Enquiry':{'enquiry_details':['item_group']},'Indent':{'indent_details':['item_group']},'Item':{'fields':['item_group']},'Manage Account':{'fields':['default_item_group']},'Purchase Order':{'po_details':['item_group']},'Purchase Receipt':{'purchase_receipt_details':['item_group']},'Purchase Voucher':{'entries':['item_group']},'Quotation':{'quotation_details':['item_group']},'Receivable Voucher':{'entries':['item_group']},'Sales BOM':{'fields':['serial_no']},'Sales Order':{'sales_order_details':['item_group']},'Serial No':{'fields':['item_group']},'Sales Partner':{'partner_target_details':['item_group']},'Sales Person':{'target_details':['item_group']},'Territory':{'target_details':['item_group']}},'fs_page_break':{'Delivery Note':{'delivery_note_details':['page_break'],'packing_details':['page_break']},'Indent':{'indent_details':['page_break']},'Purchase Order':{'po_details':['page_break']},'Purchase Receipt':{'purchase_receipt_details':['page_break']},'Purchase Voucher':{'entries':['page_break']},'Quotation':{'quotation_details':['page_break']},'Receivable Voucher':{'entries':['page_break']},'Sales Order':{'sales_order_details':['page_break']}},'fs_exports':{'Delivery Note':{'fields':['Note','conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'delivery_note_details':['base_ref_rate','amount','basic_rate']},'POS Setting':{'fields':['conversion_rate','currency']},'Quotation':{'fields':['Note HTML','OT Notes','conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'quotation_details':['base_ref_rate','amount','basic_rate']},'Receivable Voucher':{'fields':['conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'entries':['base_ref_rate','amount','basic_rate']},'Item':{'ref_rate_details':['ref_currency']},'Sales BOM':{'fields':['currency']},'Sales Order':{'fields':['Note1','OT Notes','conversion_rate','currency','grand_total_export','in_words_export','rounded_total_export'],'sales_order_details':['base_ref_rate','amount','basic_rate']}},'fs_imports':{'Payable Voucher':{'fields':['conversion_rate','currency','grand_total_import','in_words_import','net_total_import','other_charges_added_import','other_charges_deducted_import'],'entries':['purchase_ref_rate','amount','rate']},'Purchase Order':{'fields':['Note HTML','conversion_rate','currency','grand_total_import','in_words_import','net_total_import','other_charges_added_import','other_charges_deducted_import'],'po_details':['purchase_ref_rate','amount','purchase_rate']},'Purchase Receipt':{'fields':['conversion_rate','currency','grand_total_import','in_words_import','net_total_import','other_charges_added_import','other_charges_deducted_import'],'purchase_receipt_details':['purchase_ref_rate','amount','purchase_rate']},'Supplier Quotation':{'fields':['conversion_rate','currency']}},'fs_item_advanced':{'Item':{'fields':['item_customer_details']}},'fs_sales_extras':{'Address':{'fields':['sales_partner']},'Contact':{'fields':['sales_partner']},'Customer':{'fields':['sales_team']},'Delivery Note':{'fields':['sales_team','Packing List']},'Item':{'fields':['item_customer_details']},'Receivable Voucher':{'fields':['sales_team']},'Sales Order':{'fields':['sales_team','Packing List']}},'fs_more_info':{'Delivery Note':{'fields':['More Info']},'Enquiry':{'fields':['More Info']},'Indent':{'fields':['More Info']},'Lead':{'fields':['More Info']},'Payable Voucher':{'fields':['More Info']},'Purchase Order':{'fields':['More Info']},'Purchase Receipt':{'fields':['More Info']},'Quotation':{'fields':['More Info']},'Receivable Voucher':{'fields':['More Info']},'Sales Order':{'fields':['More Info']},},'fs_quality':{'Item':{'fields':['Item Inspection Criteria','inspection_required']},'Purchase Receipt':{'purchase_receipt_details':['qa_no']}},'fs_manufacturing':{'Item':{'fields':['Manufacturing']}},'fs_pos':{'Receivable Voucher':{'fields':['is_pos']}},'fs_recurring_invoice':{'Receivable Voucher':{'fields':['Recurring Invoice']}}}
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