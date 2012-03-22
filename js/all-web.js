
/*
 *	lib/js/lib/history/history.min.js
 */
/*
 * jQuery hashchange event - v1.3 - 7/21/2010
 * http://benalman.com/projects/jquery-hashchange-plugin/
 * 
 * Copyright (c) 2010 "Cowboy" Ben Alman
 * Dual licensed under the MIT and GPL licenses.
 * http://benalman.com/about/license/
 */
(function($,e,b){var c="hashchange",h=document,f,g=$.event.special,i=h.documentMode,d="on"+c in e&&(i===b||i>7);function a(j){j=j||location.href;return"#"+j.replace(/^[^#]*#?(.*)$/,"$1")}$.fn[c]=function(j){return j?this.bind(c,j):this.trigger(c)};$.fn[c].delay=50;g[c]=$.extend(g[c],{setup:function(){if(d){return false}$(f.start)},teardown:function(){if(d){return false}$(f.stop)}});f=(function(){var j={},p,m=a(),k=function(q){return q},l=k,o=k;j.start=function(){p||n()};j.stop=function(){p&&clearTimeout(p);p=b};function n(){var r=a(),q=o(m);if(r!==m){l(m=r,q);$(e).trigger(c)}else{if(q!==m){location.href=location.href.replace(/#.*/,"")+q}}p=setTimeout(n,$.fn[c].delay)}$.browser.msie&&!d&&(function(){var q,r;j.start=function(){if(!q){r=$.fn[c].src;r=r&&r+a();q=$('<iframe tabindex="-1" title="empty"/>').hide().one("load",function(){r||l(a());n()}).attr("src",r||"javascript:0").insertAfter("body")[0].contentWindow;h.onpropertychange=function(){try{if(event.propertyName==="title"){q.document.title=h.title}}catch(s){}}}};j.stop=k;o=function(){return a(q.location.href)};l=function(v,s){var u=q.document,t=$.fn[c].domain;if(v!==s){u.title=h.title;u.open();t&&u.write('<script>document.domain="'+t+'"<\/script>');u.close();q.location.hash=v}}})();return j})()})(jQuery,this);



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
wn.versions={check:function(){if(window.localStorage){if(window._version_number==-1||parseInt(localStorage._version_number)!=parseInt(window._version_number)){var localversion=localStorage._version_number;localStorage.clear();console.log("Cache cleared - version: "+localversion
+' to '+_version_number)}
localStorage.setItem('_version_number',window._version_number);}}}
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
var l=items.length;for(var i=0;i<l;i++){var src=items[i];if(!(src in wn.assets.executed_)){wn.assets.execute(src);}}}
/*
 *	lib/js/wn/dom.js
 */
wn.provide('wn.dom');wn.dom.by_id=function(id){return document.getElementById(id);}
wn.dom.eval=function(txt){if(!txt)return;var el=document.createElement('script');el.appendChild(document.createTextNode(txt));document.getElementsByTagName('head')[0].appendChild(el);}
wn.dom.set_style=function(txt){if(!txt)return;var se=document.createElement('style');se.type="text/css";if(se.styleSheet){se.styleSheet.cssText=txt;}else{se.appendChild(document.createTextNode(txt));}
document.getElementsByTagName('head')[0].appendChild(se);}
wn.dom.add=function(parent,newtag,className,cs,innerHTML,onclick){if(parent&&parent.substr)parent=wn.dom.by_id(parent);var c=document.createElement(newtag);if(parent)
parent.appendChild(c);if(className){if(newtag.toLowerCase()=='img')
c.src=className
else
c.className=className;}
if(cs)wn.dom.css(c,cs);if(innerHTML)c.innerHTML=innerHTML;if(onclick)c.onclick=onclick;return c;}
wn.dom.css=function(ele,s){if(ele&&s){for(var i in s)ele.style[i]=s[i];};return ele;}
wn.get_cookie=function(c){var t=""+document.cookie;var ind=t.indexOf(c);if(ind==-1||c=="")return"";var ind1=t.indexOf(';',ind);if(ind1==-1)ind1=t.length;return unescape(t.substring(ind+c.length+1,ind1));}
wn.dom.set_box_shadow=function(ele,spread){$(ele).css('-moz-box-shadow','0px 0px '+spread+'px rgba(0,0,0,0.3);')
$(ele).css('-webkit-box-shadow','0px 0px '+spread+'px rgba(0,0,0,0.3);')
$(ele).css('-box-shadow','0px 0px '+spread+'px rgba(0,0,0,0.3);')}
/*
 *	lib/js/wn/model.js
 */
wn.provide('wn.model');wn.model={no_value_type:['Section Break','Column Break','HTML','Table','Button','Image'],new_names:{},with_doctype:function(doctype,callback){if(locals.DocType[doctype]){callback();}else{wn.call({method:'webnotes.widgets.form.load.getdoctype',args:{doctype:doctype},callback:callback});}},with_doc:function(doctype,name,callback){if(!name)name=doctype;if(locals[doctype]&&locals[doctype][name]){callback(name);}else{if(name&&name.indexOf('New '+doctype)!=-1){name=LocalDB.create(doctype);callback(name);}else{wn.call({method:'webnotes.widgets.form.load.getdoc',args:{doctype:doctype,name:name},callback:function(r){callback(name);}});}}},can_delete:function(doctype){if(!doctype)return false;return locals.DocType[doctype].allow_trash&&wn.boot.profile.can_cancel.indexOf(doctype)!=-1;}}
/*
 *	lib/js/wn/misc/tools.js
 */
wn.markdown=function(txt){if(!wn.md2html){wn.require('lib/js/lib/showdown.js');wn.md2html=new Showdown.converter();}
return wn.md2html.makeHtml(txt);}
/*
 *	lib/js/wn/misc/user.js
 */
wn.user_info=function(uid){var def={'fullname':uid,'image':'lib/images/ui/no_img_m.gif'}
if(!wn.boot.user_info)return def
if(!wn.boot.user_info[uid])return def
if(!wn.boot.user_info[uid].fullname)
wn.boot.user_info[uid].fullname=uid;if(!wn.boot.user_info[uid].image)
wn.boot.user_info[uid].image=def.image;return wn.boot.user_info[uid];}
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
wn.route=function(){wn._cur_route=window.location.hash;route=wn.get_route();switch(route[0]){case"List":wn.views.doclistview.show(route[1]);break;case"Form":if(route.length>3){route[2]=route.splice(2).join('/');}
wn.views.formview.show(route[1],route[2]);break;case"Report":wn.views.reportview.show(route[1],route[2]);break;default:wn.views.pageview.show(route[0]);}}
wn.get_route=function(route){if(!route)
route=window.location.hash;if(route.substr(0,1)=='#')route=route.substr(1);if(route.substr(0,1)=='!')route=route.substr(1);return $.map(route.split('/'),function(r){return decodeURIComponent(r);});}
wn.set_route=function(){route=$.map(arguments,function(a){return encodeURIComponent(a)}).join('/');window.location.hash=route;}
wn._cur_route=null;$(window).bind('hashchange',function(){if(location.hash==wn._cur_route)
return;wn.route();if(wn.boot.analytics_code){try{eval(wn.boot.analytics_code);}catch(e){console.log(e);}}});
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
      <div>\
       <button class="btn btn-small add-filter-btn">\
        <i class="icon-plus"></i> Add Filter</button>\
      </div>\
      <div class="filter_area"></div>\
     </div>\
    </div>\
    \
    <div style="height: 37px; margin-bottom:9px" class="list-toolbar-wrapper">\
     <div class="list-toolbar" style="float: left">\
      <a class="btn btn-small btn-refresh btn-info">\
       <i class="icon-refresh icon-white"></i> Refresh</a>\
      <a class="btn btn-small btn-new">\
       <i class="icon-plus"></i> New</a>\
      <a class="btn btn-small btn-filter">\
       <i class="icon-search"></i> Filter</a>\
     </div>\
     <img src="lib/images/ui/button-load.gif" \
      class="img-load" style="float: left"/>\
    </div><div style="clear:both"></div>\
    \
    <div class="no-result help hide">\
     %(no_result_message)s\
    </div>\
    \
    <div class="result">\
     <div class="result-list"></div>\
     <div class="result-grid hide"></div>\
    </div>\
    \
    <div class="paging-button">\
     <button class="btn btn-small btn-more hide">More...</div>\
    </div>\
   </div>\
  ',this.opts));this.$w=$(this.parent).find('.wnlist');this.set_events();if(this.show_filters){this.make_filters();}},add_button:function(html,onclick,before){$(html).click(onclick).insertBefore(this.$w.find('.list-toolbar '+before));this.btn_groupify();},show_view:function($btn,$div,$btn_unsel,$div_unsel){$btn_unsel.removeClass('btn-info');$btn_unsel.find('i').removeClass('icon-white');$div_unsel.toggle(false);$btn.addClass('btn-info');$btn.find('i').addClass('icon-white');$div.toggle(true);},set_events:function(){var me=this;this.$w.find('.btn-refresh').click(function(){me.run();});this.$w.find('.btn-more').click(function(){me.run({append:true});});if(this.title){this.$w.find('h3').html(this.title).toggle(true);}
if(this.new_doctype){this.$w.find('.btn-new').toggle(true).click(function(){newdoc(me.new_doctype);})}else{this.$w.find('.btn-new').remove();}
if(!me.show_filters){this.$w.find('.btn-filter').remove();}
if(this.hide_refresh||this.no_refresh){this.$w.find('.btn-refresh').remove();}
this.btn_groupify();},btn_groupify:function(){var nbtns=this.$w.find('.list-toolbar a').length;if(nbtns>1){this.$w.find('.list-toolbar').addClass('btn-group')}
if(nbtns==0){this.$w.find('.list-toolbar-wrapper').toggle(false);}},make_filters:function(){this.filter_list=new wn.ui.FilterList({listobj:this,$parent:this.$w.find('.list-filters').toggle(true),doctype:this.doctype,filter_fields:this.filter_fields});},clear:function(){this.data=[];this.$w.find('.result-list').empty();this.$w.find('.result').toggle(true);this.$w.find('.no-result').toggle(false);this.start=0;},run:function(){var me=this;var a0=arguments[0];var a1=arguments[1];if(a0&&typeof a0=='function')
this.onrun=a0;if(a0&&a0.callback)
this.onrun=a0.callback;if(!a1&&!(a0&&a0.append))
this.start=0;me.set_working(true);wn.call({method:this.opts.method||'webnotes.widgets.query_builder.runquery',args:this.get_call_args(),callback:function(r){me.set_working(false);me.render_results(r)},no_spinner:this.opts.no_loading});},set_working:function(flag){this.$w.find('.img-load').toggle(flag);},get_call_args:function(){if(!this.method){this.query=this.get_query?this.get_query():this.query;this.add_limits();var args={query_max:this.query_max,as_dict:1}
args.simple_query=this.query;}else{var args={limit_start:this.start,limit_page_length:this.page_length}}
if(this.args)
$.extend(args,this.args)
if(this.get_args){$.extend(args,this.get_args());}
return args;},render_results:function(r){if(this.start==0)this.clear();this.$w.find('.btn-more').toggle(false);if(r.message)r.values=r.message;if(r.values&&r.values.length){this.data=this.data.concat(r.values);this.render_list(r.values);}else{if(this.start==0){this.$w.find('.result').toggle(false);this.$w.find('.no-result').toggle(true);}}
if(this.onrun)this.onrun();if(this.callback)this.callback(r);},render_list:function(values){var m=Math.min(values.length,this.page_length);for(var i=0;i<m;i++){this.render_row(this.add_row(),values[i],this,i);}
this.start+=m;if(values.length>=this.page_length)
this.$w.find('.btn-more').toggle(true);},add_row:function(){return this.$w.find('.result-list').append('<div class="list-row">').find('.list-row:last').get(0);},refresh:function(){this.run();},add_limits:function(){this.query+=' LIMIT '+this.start+','+(this.page_length+1);}});wn.ui.FilterList=Class.extend({init:function(opts){wn.require('lib/js/legacy/widgets/form/fields.js');$.extend(this,opts);this.filters=[];this.$w=this.$parent;this.set_events();},set_events:function(){var me=this;this.listobj.$w.find('.btn-filter').bind('click',function(){me.$w.find('.show_filters').slideToggle();if(!me.filters.length)
me.add_filter();});this.$w.find('.add-filter-btn').bind('click',function(){me.add_filter();});},add_filter:function(fieldname,condition,value){this.filters.push(new wn.ui.Filter({flist:this,fieldname:fieldname,condition:condition,value:value}));if(fieldname){this.$w.find('.show_filters').slideDown();}},get_filters:function(){var values=[];$.each(this.filters,function(i,f){if(f.field)
values.push(f.get_value());})
return values;},update_filters:function(){var fl=[];$.each(this.filters,function(i,f){if(f.field)fl.push(f);})
this.filters=fl;},get_filter:function(fieldname){for(var i in this.filters){if(this.filters[i].field.df.fieldname==fieldname)
return this.filters[i];}}});wn.ui.Filter=Class.extend({init:function(opts){$.extend(this,opts);this.doctype=this.flist.doctype;this.fields_by_name={};this.make();this.make_options();this.set_events();},make:function(){this.flist.$w.find('.filter_area').append('<div class="list_filter">\
  <select class="fieldname_select"></select>\
  <select class="condition">\
   <option value="=">Equals</option>\
   <option value="like">Like</option>\
   <option value=">=">Greater or equals</option>\
   <option value=">=">Less or equals</option>\
   <option value=">">Greater than</option>\
   <option value="<">Less than</option>\
   <option value="in">In</option>\
   <option value="!=">Not equals</option>\
  </select>\
  <span class="filter_field"></span>\
  <a class="close">&times;</a>\
  </div>');this.$w=this.flist.$w.find('.list_filter:last-child');this.$select=this.$w.find('.fieldname_select');},make_options:function(){if(this.filter_fields){for(var i in this.filter_fields)
this.add_field_option(this.filter_fields[i])}else{this.render_field_select();}},set_events:function(){var me=this;this.$w.find('.fieldname_select').bind('change',function(){me.set_field(this.value);});this.$w.find('a.close').bind('click',function(){me.$w.css('display','none');var value=me.field.get_value();me.field=null;if(!me.flist.get_filters().length){me.flist.$w.find('.set_filters').toggle(true);me.flist.$w.find('.show_filters').toggle(false);}
if(value){me.flist.listobj.run();}
me.flist.update_filters();return false;});me.$w.find('.condition').change(function(){if($(this).val()=='in'){me.set_field(me.field.df.fieldname,'Data');if(!me.field.desc_area)
me.field.desc_area=$a(me.field.wrapper,'span','help',null,'values separated by comma');}else{me.set_field(me.field.df.fieldname);}});if(me.fieldname){this.set_values(me.fieldname,me.condition,me.value);}else{me.set_field('name');}},set_values:function(fieldname,condition,value){this.set_field(fieldname);if(condition)this.$w.find('.condition').val(condition).change();if(value)this.field.set_input(value)},render_field_select:function(){var me=this;me.table_fields=[];var std_filters=[{fieldname:'name',fieldtype:'Data',label:'ID',parent:me.doctype},{fieldname:'modified',fieldtype:'Date',label:'Last Modified',parent:me.doctype},{fieldname:'owner',fieldtype:'Data',label:'Created By',parent:me.doctype},{fieldname:'_user_tags',fieldtype:'Data',label:'Tags',parent:me.doctype}];$.each(std_filters.concat(fields_list[me.doctype]),function(i,df){me.add_field_option(df);});$.each(me.table_fields,function(i,table_df){if(table_df.options){$.each(fields_list[table_df.options],function(i,df){me.add_field_option(df);});}})},add_field_option:function(df){var me=this;if(me.doctype&&df.parent==me.doctype){var label=df.label;var table=get_label_doctype(me.doctype);if(df.fieldtype=='Table')me.table_fields.push(df);}else{var label=df.label+' ('+df.parent+')';var table=df.parent;}
if(wn.model.no_value_type.indexOf(df.fieldtype)==-1&&!me.fields_by_name[df.fieldname]){this.$select.append($('<option>',{value:df.fieldname,table:table}).text(label));me.fields_by_name[df.fieldname]=df;}},set_field:function(fieldname,fieldtype){var me=this;var cur=me.field?{fieldname:me.field.df.fieldname,fieldtype:me.field.df.fieldtype}:{}
var df=me.fields_by_name[fieldname];this.set_fieldtype(df,fieldtype);if(me.field&&cur.fieldname==fieldname&&df.fieldtype==cur.fieldtype){return;}
me.$w.find('.fieldname_select').val(fieldname);var field_area=me.$w.find('.filter_field').empty().get(0);f=make_field(df,null,field_area,null,0,1);f.df.single_select=1;f.not_in_form=1;f.with_label=0;f.refresh();me.field=f;this.set_default_condition(df,fieldtype);$(me.field.wrapper).find(':input').keydown(function(ev){if(ev.which==13){me.flist.listobj.run();}})},set_fieldtype:function(df,fieldtype){if(df.original_type)
df.fieldtype=df.original_type;else
df.original_type=df.fieldtype;df.description='';df.reqd=0;if(fieldtype){df.fieldtype=fieldtype;return;}
if(df.fieldtype=='Check'){df.fieldtype='Select';df.options='No\nYes';}else if(['Text','Text Editor','Code','Link'].indexOf(df.fieldtype)!=-1){df.fieldtype='Data';}},set_default_condition:function(df,fieldtype){if(!fieldtype){if(df.fieldtype=='Data'){this.$w.find('.condition').val('like');}else{this.$w.find('.condition').val('=');}}},get_value:function(){var me=this;var val=me.field.get_value();var cond=me.$w.find('.condition').val();if(me.field.df.original_type=='Check'){val=(val=='Yes'?1:0);}
if(cond=='like'){val=val+'%';}
return[me.$w.find('.fieldname_select option:selected').attr('table'),me.field.df.fieldname,me.$w.find('.condition').val(),val];}});
/*
 *	lib/js/wn/views/container.js
 */
wn.provide('wn.pages');wn.provide('wn.views');wn.views.Container=Class.extend({init:function(){this.container=$('#body_div').get(0);this.page=null;this.pagewidth=$('#body_div').width();this.pagemargin=50;},add_page:function(label,onshow,onhide){var page=$('<div class="content"></div>').appendTo(this.container).get(0);if(onshow)
$(page).bind('show',onshow);if(onshow)
$(page).bind('hide',onhide);page.label=label;wn.pages[label]=page;return page;},change_to:function(label){if(this.page&&this.page.label==label){return;}
var me=this;if(label.tagName){var page=label;}else{var page=wn.pages[label];}
if(!page){console.log('Page not found '+label);return;}
if(this.page){$(this.page).toggle(false);$(this.page).trigger('hide');}
this.page=page;$(this.page).fadeIn();$(this.page).trigger('show');this.page._route=window.location.hash;document.title=this.page.label;return this.page;}})
/*
 *	lib/js/wn/views/doclistview.js
 */
wn.provide('wn.views.doclistview');wn.provide('wn.doclistviews');wn.views.doclistview.pages={};wn.views.doclistview.show=function(doctype){var pagename=doctype+' List';var doctype=get_label_doctype(doctype);wn.model.with_doctype(doctype,function(){var page=wn.views.doclistview.pages[pagename];if(!page){var page=wn.container.add_page(pagename);page.doclistview=new wn.views.DocListView(doctype,page);wn.views.doclistview.pages[pagename]=page;}
document.title=page.doclistview.label;wn.container.change_to(pagename);})}
wn.views.DocListView=wn.ui.Listing.extend({init:function(doctype,page){this.doctype=doctype;this.$page=$(page);this.label=get_doctype_label(doctype);this.label=(this.label.toLowerCase().substr(-4)=='list')?this.label:(this.label+' List');this.make_page();this.setup();},make_page:function(){var me=this;this.$page.html(repl('<div class="layout-wrapper layout-wrapper-background">\
   <div class="layout-main-section">\
    <a class="close" onclick="window.history.back();">&times;</a>\
    <h1>%(label)s</h1>\
    <hr>\
    <div class="wnlist-area"><div class="help">Loading...</div></div>\
   </div>\
   <div class="layout-side-section">\
    <div class="stat-wrapper show-docstatus hide">\
     <h4>Show</h4>\
     <div><input data-docstatus="0" type="checkbox" checked="checked" /> Drafts</div>\
     <div><input data-docstatus="1" type="checkbox" checked="checked" /> Submitted</div>\
     <div><input data-docstatus="2" type="checkbox" /> Cancelled</div>\
    </div>\
   </div>\
   <div style="clear: both"></div>\
  </div>',{label:this.label}));},setup:function(){var me=this;me.can_delete=wn.model.can_delete(me.doctype);me.meta=locals.DocType[me.doctype];me.$page.find('.wnlist-area').empty(),me.setup_docstatus_filter();me.setup_listview();me.init_list();me.init_stats();me.add_delete_option();},setup_docstatus_filter:function(){var me=this;this.can_submit=$.map(locals.DocPerm,function(d){if(d.parent==me.meta.name&&d.submit)return 1
else return null;}).length;if(this.can_submit){this.$page.find('.show-docstatus').removeClass('hide');this.$page.find('.show-docstatus input').click(function(){me.run();})}},setup_listview:function(){if(this.meta.__listjs){eval(this.meta.__listjs);this.listview=new wn.doclistviews[this.doctype](this);}else{this.listview=new wn.views.ListView(this);}
this.listview.parent=this;},init_list:function(){this.make({method:'webnotes.widgets.doclistview.get',get_args:this.get_args,parent:this.$page.find('.wnlist-area'),start:0,page_length:20,show_filters:true,show_grid:true,new_doctype:this.doctype,allow_delete:true,no_result_message:this.make_no_result(),columns:this.listview.fields});this.run();},make_no_result:function(){return repl('<div class="well"><p>No %(doctype_label)s found</p>\
  %(description)s\
  <hr>\
  <p><button class="btn btn-info btn-small"\
    onclick="wn.set_route(\'Form\', \'%(doctype)s\', \'New %(doctype)s\');"\
    >Make a new %(doctype_label)s</button>\
  </p></div>',{doctype_label:get_doctype_label(this.doctype),doctype:this.doctype,description:wn.markdown(locals.DocType[this.doctype].description||'')});},render_row:function(row,data){data.doctype=this.doctype;this.listview.render(row,data,this);},get_query_fields:function(){return this.listview.fields;},get_args:function(){return{doctype:this.doctype,fields:this.get_query_fields(),filters:this.filter_list.get_filters(),docstatus:this.can_submit?$.map(this.$page.find('.show-docstatus :checked'),function(inp){return $(inp).attr('data-docstatus')}):[]}},add_delete_option:function(){var me=this;if(this.can_delete){this.add_button('<a class="btn btn-small btn-delete">\
    <i class="icon-remove"></i> Delete</a>',function(){me.delete_items();},'.btn-filter')}},delete_items:function(){var me=this;var dl=$.map(me.$page.find('.list-delete:checked'),function(e){return $(e).data('name');});if(!dl.length)
return;if(!confirm('This is PERMANENT action and you cannot undo. Continue?')){return;}
me.set_working(true);wn.call({method:'webnotes.widgets.doclistview.delete_items',args:{items:dl,doctype:me.doctype},callback:function(){me.set_working(false);me.refresh();}})},init_stats:function(){var me=this
wn.call({method:'webnotes.widgets.doclistview.get_stats',args:{stats:me.listview.stats,doctype:me.doctype},callback:function(r){$.each(r.message,function(field,stat){me.render_stat(field,stat);});}});},render_stat:function(field,stat){var me=this;if(!stat||!stat.length){if(field=='_user_tags'){this.$page.find('.layout-side-section').append('<div class="stat-wrapper"><h4>Tags</h4>\
      <div class="help small"><i>No records tagged.</i><br><br> \
      To add a tag, open the document and click on \
      "Add Tag" on the sidebar</div></div>');}
return;}
var label=fields[this.doctype][field]?fields[this.doctype][field].label:field;if(label=='_user_tags')label='Tags';var $w=$('<div class="stat-wrapper">\
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
  </div>',args));this.setup_stat_item_click($item);return $item;},setup_stat_item_click:function($item){var me=this;$item.find('a').click(function(){var fieldname=$(this).attr('data-field');var label=$(this).attr('data-label');me.set_filter(fieldname,label);return false;});},set_filter:function(fieldname,label){var filter=this.filter_list.get_filter(fieldname);if(filter){var v=filter.field.get_value();if(v.indexOf(label)!=-1){return false;}else{if(fieldname=='_user_tags'){this.filter_list.add_filter(fieldname,'like','%'+label);}else{filter.set_values(fieldname,'in',v+', '+label);}}}else{if(fieldname=='_user_tags'){this.filter_list.add_filter(fieldname,'like','%'+label);}else{this.filter_list.add_filter(fieldname,'=',label);}}
this.run();}});wn.views.ListView=Class.extend({init:function(doclistview){this.doclistview=doclistview;this.doctype=doclistview.doctype;var t="`tab"+this.doctype+"`.";this.fields=[t+'name',t+'owner',t+'docstatus',t+'_user_tags',t+'modified'];this.stats=['_user_tags'];if(!this.doclistview.can_delete){this.columns=$.map(this.columns,function(v,i){if(v.content!='check')return v});}},columns:[{width:'3%',content:'check'},{width:'4%',content:'avatar'},{width:'3%',content:'docstatus',css:{"text-align":"center"}},{width:'35%',content:'name'},{width:'40%',content:'tags',css:{'color':'#aaa'}},{width:'15%',content:'modified',css:{'text-align':'right','color':'#777'}}],render_column:function(data,parent,opts){var me=this;if(opts.css){$.each(opts.css,function(k,v){$(parent).css(k,v)});}
if(opts.content.indexOf&&opts.content.indexOf('+')!=-1){$.map(opts.content.split('+'),function(v){me.render_column(data,parent,{content:v});});return;}
if(typeof opts.content=='function'){opts.content(parent,data);}
else if(opts.content=='name'){$(parent).html(repl('<a href="#!Form/%(doctype)s/%(name)s">%(name)s</a>',data));}
else if(opts.content=='avatar'){$(parent).html(repl('<span class="avatar-small"><img src="%(avatar)s" \
    title="%(fullname)s"/></span>',data));}
else if(opts.content=='check'){$(parent).html('<input class="list-delete" type="checkbox">');$(parent).find('input').data('name',data.name);}
else if(opts.content=='docstatus'){$(parent).html(repl('<span class="docstatus"><i class="%(docstatus_icon)s" \
    title="%(docstatus_title)s"></i></span>',data));}
else if(opts.content=='tags'){this.add_user_tags(parent,data);}
else if(opts.content=='modified'){$(parent).append(data.when);}
else if(opts.type=='bar-graph'){args={percent:data[opts.content],fully_delivered:(data[opts.content]>99?'bar-complete':''),label:opts.label}
$(parent).html(repl('<span class="bar-outer" style="width: 30px; float: right" \
    title="%(percent)s% %(label)s">\
    <span class="bar-inner %(fully_delivered)s" \
     style="width: %(percent)s%;"></span>\
   </span>',args));}
else if(data[opts.content]){$(parent).append(' '+data[opts.content]);}},render:function(row,data){var me=this;this.prepare_data(data);rowhtml='';$.each(this.columns,function(i,v){rowhtml+=repl('<td style="width: %(width)s"></td>',v);});var tr=$(row).html('<table><tbody><tr>'+rowhtml+'</tr></tbody></table>').find('tr').get(0);$.each(this.columns,function(i,v){me.render_column(data,tr.cells[i],v);});},prepare_data:function(data){data.fullname=wn.user_info(data.owner).fullname;data.avatar=wn.user_info(data.owner).image;data.when=dateutil.str_to_user(data.modified).split(' ')[0];var diff=dateutil.get_diff(dateutil.get_today(),data.modified.split(' ')[0]);if(diff==0){data.when='Today'}
if(diff==-1){data.when='Yesterday'}
if(diff==-2){data.when='2 days ago'}
if(data.docstatus==0||data.docstatus==null){data.docstatus_icon='icon-pencil';data.docstatus_title='Editable';}else if(data.docstatus==1){data.docstatus_icon='icon-lock';data.docstatus_title='Submitted';}else if(data.docstatus==2){data.docstatus_icon='icon-remove';data.docstatus_title='Cancelled';}},add_user_tags:function(parent,data){var me=this;if(data._user_tags){$.each(data._user_tags.split(','),function(i,t){if(t){$('<span class="label label-info" style="cursor: pointer">'
+strip(t)+'</span>').click(function(){me.doclistview.set_filter('_user_tags',$(this).text())}).appendTo(parent);}});}}})
/*
 *	lib/js/wn/views/pageview.js
 */
wn.provide('wn.views.pageview');wn.views.pageview={pages:{},with_page:function(name,callback){if(!locals.Page[name]){wn.call({method:'webnotes.widgets.page.getpage',args:{'name':name},callback:callback});}else{callback();}},show:function(name){wn.views.pageview.with_page(name,function(){if(!wn.pages[name]){wn.views.pageview.pages[name]=new wn.views.Page(name);}
wn.container.change_to(name);});}}
wn.views.Page=Class.extend({init:function(name){this.name=name;var me=this;this.pagedoc=locals.Page[this.name];this.wrapper=wn.container.add_page(this.name);this.wrapper.label=this.pagedoc.title||this.pagedoc.name;this.wrapper.innerHTML=this.pagedoc.content;wn.dom.eval(this.pagedoc.__script||this.pagedoc.script||'');wn.dom.set_style(this.pagedoc.style);this.trigger('onload');$(this.wrapper).bind('show',function(){cur_frm=null;me.trigger('onshow');});},trigger:function(eventname){var me=this;try{if(pscript[eventname+'_'+this.name]){pscript[eventname+'_'+this.name](me.wrapper);}else if(me.wrapper[eventname]){me.wrapper[eventname](me.wrapper);}}catch(e){console.log(e);}}})
/*
 *	lib/js/wn/views/formview.js
 */
wn.provide('wn.views.formview');wn.views.formview={show:function(dt,dn){if(wn.model.new_names[dn])
dn=wn.model.new_names[dn];wn.model.with_doctype(dt,function(){wn.model.with_doc(dt,dn,function(dn){if(!wn.views.formview[dt]){wn.views.formview[dt]=wn.container.add_page('Form - '+dt);wn.views.formview[dt].frm=new _f.Frm(dt,wn.views.formview[dt]);}
wn.container.change_to('Form - '+dt);wn.views.formview[dt].frm.refresh(dn);});})}}
/*
 *	lib/js/wn/views/reportview.js
 */
wn.views.reportview={show:function(dt,rep_name){wn.require('lib/js/legacy/report.compressed.js');dt=get_label_doctype(dt);if(!_r.rb_con){_r.rb_con=new _r.ReportContainer();}
_r.rb_con.set_dt(dt,function(rb){if(rep_name){var t=rb.current_loaded;rb.load_criteria(rep_name);if(onload)
onload(rb);if((rb.dt)&&(!rb.dt.has_data()||rb.current_loaded!=t))
rb.dt.run();}
if(!rb.forbidden){wn.container.change_to('Report Builder');}});}}
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
wn.call=function(opts){var args=$.extend({},opts.args)
if(opts.module&&opts.page){args.cmd=opts.module+'.page.'+opts.page+'.'+opts.page+'.'+opts.method}else if(opts.method){args.cmd=opts.method;}
for(key in args){if(args[key]&&typeof args[key]!='string'){args[key]=JSON.stringify(args[key]);}}
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
wn.settings.no_history=1;var NEWLINE='\n';var login_file='';var version='v170';var profile=null;var session={};var is_testing=false;var user=null;var user_defaults=null;var user_roles=null;var user_fullname=null;var user_email=null;var user_img={};var home_page=null;var pscript={};var selector=null;var top_index=91;var _f={};var _p={};var _e={};var _r={};var FILTER_SEP='\1';var frms={};var cur_frm=null;var pscript={};var validated=true;var validation_message='';var tinymce_loaded=null;
/*
 *	lib/js/legacy/utils/datatype.js
 */
wn.utils.full_name=function(fn,ln){return fn+(ln?' ':'')+(ln?ln:'')}
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
return parseFloat(v.toFixed(decimals));return v;}
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
if(d.search('-')!=-1){var t=d.split('-');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else if(d.search('/')!=-1){var t=d.split('/');return new Date(t[0],t[1]-1,t[2],tm[0],tm[1]);}else{return new Date();}},obj_to_str:function(d){return d.getFullYear()+'-'+int_to_str(d.getMonth()+1,2)+'-'+int_to_str(d.getDate(),2);},obj_to_user:function(d){return dateutil.str_to_user(dateutil.obj_to_str(d));},get_diff:function(d1,d2){if(typeof d1=='string')d1=dateutil.str_to_obj(d1);if(typeof d2=='string')d2=dateutil.str_to_obj(d2);return((d1-d2)/86400000);},get_day_diff:function(d1,d2){return dateutil.get_diff(new Date(d1.getYear(),d1.getMonth(),d1.getDate(),0,0),new Date(d2.getYear(),d2.getMonth(),d2.getDate(),0,0))},add_days:function(d,days){d.setTime(d.getTime()+(days*24*60*60*1000));return d},add_months:function(d,months){dt=dateutil.str_to_obj(d)
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
ele.myid=wn.dom.set_unique_id(ele);$(ele).tinymce({script_url:'lib/js/lib/tiny_mce_33/tiny_mce.js',height:height?height:'200px',theme:"advanced",theme_advanced_buttons1:"bold,italic,underline,separator,strikethrough,justifyleft,justifycenter,justifyright,justifyfull,bullist,numlist,outdent,indent,link,unlink,forecolor,backcolor,code,",theme_advanced_buttons2:"",theme_advanced_buttons3:"",theme_advanced_toolbar_location:"top",theme_advanced_toolbar_align:"left",theme_advanced_path:false,theme_advanced_resizing:false});},remove:function(ele){tinyMCE.execCommand('mceRemoveControl',true,ele.myid);},get_value:function(ele){return tinymce.get(ele.myid).getContent();}}
wn.ele={link:function(args){var span=$a(args.parent,'span','link_type',args.style);span.loading_img=$a(args.parent,'img','',{margin:'0px 4px -2px 4px',display:'none'});span.loading_img.src='lib/images/ui/button-load.gif';span.innerHTML=args.label;span.user_onclick=args.onclick;span.onclick=function(){if(!this.disabled)this.user_onclick(this);}
span.set_working=function(){this.disabled=1;$di(this.loading_img);}
span.done_working=function(){this.disabled=0;$dh(this.loading_img);}
return span;}}
function $ln(parent,label,onclick,style){return wn.ele.link({parent:parent,label:label,onclick:onclick,style:style})}
function $btn(parent,label,onclick,style,css_class,is_ajax){if(css_class==='green')css_class='btn-info';return new wn.ui.Button({parent:parent,label:label,onclick:onclick,style:style,is_ajax:is_ajax,css_class:css_class}).btn;}
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
function set_style(txt){wn.dom.set_style(txt);}
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
args.docs=compress_doclist(doclist);open_url_post(wn.request.url,args);}
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
 *	lib/js/legacy/widgets/form/fields.js
 */
var no_value_fields=['Section Break','Column Break','HTML','Table','FlexTable','Button','Image'];var codeid=0;var code_editors={};function Field(){this.with_label=1;}
Field.prototype.make_body=function(){var ischk=(this.df.fieldtype=='Check'?1:0);if(this.parent)
this.wrapper=$a(this.parent,(this.with_label?'div':'span'));else
this.wrapper=document.createElement((this.with_label?'div':'span'));this.label_area=$a(this.wrapper,'div','',{margin:'0px 0px 2px 0px'});if(ischk&&!this.in_grid){this.input_area=$a(this.label_area,'span','',{marginRight:'4px'});this.disp_area=$a(this.label_area,'span','',{marginRight:'4px'});}
if(this.with_label){this.label_span=$a(this.label_area,'span','small')
this.label_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 4px'});$dh(this.label_icon);this.label_icon.src='lib/images/icons/error.gif';this.label_icon.title='Mandatory value needs to be entered';this.suggest_icon=$a(this.label_area,'img','',{margin:'-3px 4px -3px 0px'});$dh(this.suggest_icon);this.suggest_icon.src='lib/images/icons/bullet_arrow_down.png';this.suggest_icon.title='With suggestions';}else{this.label_span=$a(this.label_area,'span','',{marginRight:'4px'})
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
this.input.name=this.df.fieldname;$(this.input).change(function(){me.set_value($(this).val());});this.set_value=function(val){if(!me.last_value)me.last_value='';if(me.validate){val=me.validate(val);me.input.value=val;}
me.set(val);if(me.format_input)
me.format_input();if(in_list(['Currency','Float','Int'],me.df.fieldtype)){if(flt(me.last_value)==flt(val)){me.last_value=val;return;}}
me.last_value=val;me.run_trigger();}
this.input.set_input=function(val){if(val==null)val='';me.input.value=val;if(me.format_input)me.format_input();}
if(this.df.options=='Suggest'){if(this.suggest_icon)$di(this.suggest_icon);$(me.input).autocomplete({source:function(request,response){wn.call({method:'webnotes.widgets.search.search_link',args:{'txt':request.term,'dt':me.df.options,'query':repl('SELECT DISTINCT `%(fieldname)s` FROM \
       `tab%(dt)s` WHERE `%(fieldname)s` LIKE "%s" LIMIT 50',{fieldname:me.df.fieldname,dt:me.df.parent})},callback:function(r){response(r.results);}});},select:function(event,ui){me.set_input_value(ui.item.value);return false;}});}}
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
var datepicker_active=0;function DateField(){}DateField.prototype=new Field();DateField.prototype.make_input=function(){var me=this;this.user_fmt=wn.control_panel.date_format;if(!this.user_fmt)this.user_fmt='dd-mm-yy';this.input=$a(this.input_area,'input');$(this.input).datepicker({dateFormat:me.user_fmt.replace('yyyy','yy'),altFormat:'yy-mm-dd',changeYear:true,beforeShow:function(input,inst){datepicker_active=1},onClose:function(dateText,inst){datepicker_active=0;if(_f.cur_grid_cell)
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
$(me.txt).autocomplete({source:function(request,response){wn.call({method:'webnotes.widgets.search.search_link',args:{'txt':request.term,'dt':me.df.options,'query':me.get_custom_query()},callback:function(r){response(r.results);},});},select:function(event,ui){me.set_input_value(ui.item.value);return false;}}).data('autocomplete')._renderItem=function(ul,item){return $('<li></li>').data('item.autocomplete',item).append(repl('<a>%(label)s<br><span style="font-size:10px">%(info)s</span></a>',item)).appendTo(ul);};}
LinkField.prototype.get_custom_query=function(){this.set_get_query();if(this.get_query){if(cur_frm)
var doc=locals[cur_frm.doctype][cur_frm.docname];return this.get_query(doc,this.doctype,this.docname);}}
LinkField.prototype.setup_buttons=function(){var me=this;me.btn.onclick=function(){selector.set(me,me.df.options,me.df.label);selector.show(me.txt);}
if(me.btn1)me.btn1.onclick=function(){if(me.txt.value&&me.df.options){loaddoc(me.df.options,me.txt.value);}}
me.can_create=0;if((!me.not_in_form)&&in_list(profile.can_create,me.df.options)){me.can_create=1;me.btn2.onclick=function(){var on_save_callback=function(new_rec){if(new_rec){var d=_f.calling_doc_stack.pop();locals[d[0]][d[1]][me.df.fieldname]=new_rec;me.refresh();if(me.grid)me.grid.refresh();me.run_trigger();}}
_f.calling_doc_stack.push([me.doctype,me.docname]);new_doc(me.df.options,me.on_new,1,on_save_callback,me.doctype,me.docname,me.frm.not_in_container);}}else{$dh(me.btn2);$y($td(me.tab,0,2),{width:'0px'});}}
LinkField.prototype.set_input_value=function(val){var me=this;me.refresh_label_icon();if(me.not_in_form){$(this.txt).val(val);return;}
if(cur_frm){if(val==locals[me.doctype][me.docname][me.df.fieldname]){me.set(val);me.run_trigger();return;}}
me.set(val);if(_f.cur_grid_cell)
_f.cur_grid_cell.grid.cell_deselect();if(!val){me.run_trigger();return;}
var fetch='';if(cur_frm.fetch_dict[me.df.fieldname])
fetch=cur_frm.fetch_dict[me.df.fieldname].columns.join(', ');$c('webnotes.widgets.form.utils.validate_link',{'value':val,'options':me.df.options,'fetch':fetch},function(r,rt){if(selector&&selector.display)return;if(r.message=='Ok'){if($(me.txt).val()!=val){me.set_input(val);}
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
this.set_attach_options();me.options_list=me.df.options?me.df.options.split('\n'):[];empty_select(this.input);if(me.in_filter&&me.options_list[0]!=''){me.options_list=add_lists([''],me.options_list);}
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
this.hide=function(){if(this.onhide)this.onhide();unfreeze();$dh(this.wrapper);this.display=false;cur_dialog=null;}
this.no_cancel=function(){$dh(this.cancel_img);}
if(opts)this.make();}
wn.widgets.Dialog.prototype=new wn.widgets.FieldGroup();$(document).bind('keydown',function(e){if(cur_dialog&&!cur_dialog.no_cancel_flag&&e.which==27){cur_dialog.hide();}});
/*
 *	lib/js/wn/ui/button.js
 */
wn.ui.Button=function(args){var me=this;$.extend(this,{make:function(){me.btn=wn.dom.add(args.parent,'button','btn btn-small '+(args.css_class||''));me.btn.args=args;me.loading_img=wn.dom.add(me.btn.args.parent,'img','',{margin:'0px 4px -2px 4px',display:'none'});me.loading_img.src='lib/images/ui/button-load.gif';if(args.is_ajax)wn.dom.css(me.btn,{marginRight:'24px'});me.btn.innerHTML=args.label;me.btn.user_onclick=args.onclick;$(me.btn).bind('click',function(){if(!this.disabled&&this.user_onclick)
this.user_onclick(this);})
me.btn.set_working=me.set_working;me.btn.done_working=me.done_working;if(me.btn.args.style)
wn.dom.css(me.btn,args.style);},set_working:function(){me.btn.disabled='disabled';if(me.btn.args.is_ajax){$(me.btn).css('margin-right','0px');}
$(me.loading_img).css('display','inline');},done_working:function(){me.btn.disabled=false;if(me.btn.args.is_ajax){$(me.btn).css('margin-right','24px');}
$(me.loading_img).toggle(false);}});this.make();}
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
      <div>\
       <button class="btn btn-small add-filter-btn">\
        <i class="icon-plus"></i> Add Filter</button>\
      </div>\
      <div class="filter_area"></div>\
     </div>\
    </div>\
    \
    <div style="height: 37px; margin-bottom:9px" class="list-toolbar-wrapper">\
     <div class="list-toolbar" style="float: left">\
      <a class="btn btn-small btn-refresh btn-info">\
       <i class="icon-refresh icon-white"></i> Refresh</a>\
      <a class="btn btn-small btn-new">\
       <i class="icon-plus"></i> New</a>\
      <a class="btn btn-small btn-filter">\
       <i class="icon-search"></i> Filter</a>\
     </div>\
     <img src="lib/images/ui/button-load.gif" \
      class="img-load" style="float: left"/>\
    </div><div style="clear:both"></div>\
    \
    <div class="no-result help hide">\
     %(no_result_message)s\
    </div>\
    \
    <div class="result">\
     <div class="result-list"></div>\
     <div class="result-grid hide"></div>\
    </div>\
    \
    <div class="paging-button">\
     <button class="btn btn-small btn-more hide">More...</div>\
    </div>\
   </div>\
  ',this.opts));this.$w=$(this.parent).find('.wnlist');this.set_events();if(this.show_filters){this.make_filters();}},add_button:function(html,onclick,before){$(html).click(onclick).insertBefore(this.$w.find('.list-toolbar '+before));this.btn_groupify();},show_view:function($btn,$div,$btn_unsel,$div_unsel){$btn_unsel.removeClass('btn-info');$btn_unsel.find('i').removeClass('icon-white');$div_unsel.toggle(false);$btn.addClass('btn-info');$btn.find('i').addClass('icon-white');$div.toggle(true);},set_events:function(){var me=this;this.$w.find('.btn-refresh').click(function(){me.run();});this.$w.find('.btn-more').click(function(){me.run({append:true});});if(this.title){this.$w.find('h3').html(this.title).toggle(true);}
if(this.new_doctype){this.$w.find('.btn-new').toggle(true).click(function(){newdoc(me.new_doctype);})}else{this.$w.find('.btn-new').remove();}
if(!me.show_filters){this.$w.find('.btn-filter').remove();}
if(this.hide_refresh||this.no_refresh){this.$w.find('.btn-refresh').remove();}
this.btn_groupify();},btn_groupify:function(){var nbtns=this.$w.find('.list-toolbar a').length;if(nbtns>1){this.$w.find('.list-toolbar').addClass('btn-group')}
if(nbtns==0){this.$w.find('.list-toolbar-wrapper').toggle(false);}},make_filters:function(){this.filter_list=new wn.ui.FilterList({listobj:this,$parent:this.$w.find('.list-filters').toggle(true),doctype:this.doctype,filter_fields:this.filter_fields});},clear:function(){this.data=[];this.$w.find('.result-list').empty();this.$w.find('.result').toggle(true);this.$w.find('.no-result').toggle(false);this.start=0;},run:function(){var me=this;var a0=arguments[0];var a1=arguments[1];if(a0&&typeof a0=='function')
this.onrun=a0;if(a0&&a0.callback)
this.onrun=a0.callback;if(!a1&&!(a0&&a0.append))
this.start=0;me.set_working(true);wn.call({method:this.opts.method||'webnotes.widgets.query_builder.runquery',args:this.get_call_args(),callback:function(r){me.set_working(false);me.render_results(r)},no_spinner:this.opts.no_loading});},set_working:function(flag){this.$w.find('.img-load').toggle(flag);},get_call_args:function(){if(!this.method){this.query=this.get_query?this.get_query():this.query;this.add_limits();var args={query_max:this.query_max,as_dict:1}
args.simple_query=this.query;}else{var args={limit_start:this.start,limit_page_length:this.page_length}}
if(this.args)
$.extend(args,this.args)
if(this.get_args){$.extend(args,this.get_args());}
return args;},render_results:function(r){if(this.start==0)this.clear();this.$w.find('.btn-more').toggle(false);if(r.message)r.values=r.message;if(r.values&&r.values.length){this.data=this.data.concat(r.values);this.render_list(r.values);}else{if(this.start==0){this.$w.find('.result').toggle(false);this.$w.find('.no-result').toggle(true);}}
if(this.onrun)this.onrun();if(this.callback)this.callback(r);},render_list:function(values){var m=Math.min(values.length,this.page_length);for(var i=0;i<m;i++){this.render_row(this.add_row(),values[i],this,i);}
this.start+=m;if(values.length>=this.page_length)
this.$w.find('.btn-more').toggle(true);},add_row:function(){return this.$w.find('.result-list').append('<div class="list-row">').find('.list-row:last').get(0);},refresh:function(){this.run();},add_limits:function(){this.query+=' LIMIT '+this.start+','+(this.page_length+1);}});wn.ui.FilterList=Class.extend({init:function(opts){wn.require('lib/js/legacy/widgets/form/fields.js');$.extend(this,opts);this.filters=[];this.$w=this.$parent;this.set_events();},set_events:function(){var me=this;this.listobj.$w.find('.btn-filter').bind('click',function(){me.$w.find('.show_filters').slideToggle();if(!me.filters.length)
me.add_filter();});this.$w.find('.add-filter-btn').bind('click',function(){me.add_filter();});},add_filter:function(fieldname,condition,value){this.filters.push(new wn.ui.Filter({flist:this,fieldname:fieldname,condition:condition,value:value}));if(fieldname){this.$w.find('.show_filters').slideDown();}},get_filters:function(){var values=[];$.each(this.filters,function(i,f){if(f.field)
values.push(f.get_value());})
return values;},update_filters:function(){var fl=[];$.each(this.filters,function(i,f){if(f.field)fl.push(f);})
this.filters=fl;},get_filter:function(fieldname){for(var i in this.filters){if(this.filters[i].field.df.fieldname==fieldname)
return this.filters[i];}}});wn.ui.Filter=Class.extend({init:function(opts){$.extend(this,opts);this.doctype=this.flist.doctype;this.fields_by_name={};this.make();this.make_options();this.set_events();},make:function(){this.flist.$w.find('.filter_area').append('<div class="list_filter">\
  <select class="fieldname_select"></select>\
  <select class="condition">\
   <option value="=">Equals</option>\
   <option value="like">Like</option>\
   <option value=">=">Greater or equals</option>\
   <option value=">=">Less or equals</option>\
   <option value=">">Greater than</option>\
   <option value="<">Less than</option>\
   <option value="in">In</option>\
   <option value="!=">Not equals</option>\
  </select>\
  <span class="filter_field"></span>\
  <a class="close">&times;</a>\
  </div>');this.$w=this.flist.$w.find('.list_filter:last-child');this.$select=this.$w.find('.fieldname_select');},make_options:function(){if(this.filter_fields){for(var i in this.filter_fields)
this.add_field_option(this.filter_fields[i])}else{this.render_field_select();}},set_events:function(){var me=this;this.$w.find('.fieldname_select').bind('change',function(){me.set_field(this.value);});this.$w.find('a.close').bind('click',function(){me.$w.css('display','none');var value=me.field.get_value();me.field=null;if(!me.flist.get_filters().length){me.flist.$w.find('.set_filters').toggle(true);me.flist.$w.find('.show_filters').toggle(false);}
if(value){me.flist.listobj.run();}
me.flist.update_filters();return false;});me.$w.find('.condition').change(function(){if($(this).val()=='in'){me.set_field(me.field.df.fieldname,'Data');if(!me.field.desc_area)
me.field.desc_area=$a(me.field.wrapper,'span','help',null,'values separated by comma');}else{me.set_field(me.field.df.fieldname);}});if(me.fieldname){this.set_values(me.fieldname,me.condition,me.value);}else{me.set_field('name');}},set_values:function(fieldname,condition,value){this.set_field(fieldname);if(condition)this.$w.find('.condition').val(condition).change();if(value)this.field.set_input(value)},render_field_select:function(){var me=this;me.table_fields=[];var std_filters=[{fieldname:'name',fieldtype:'Data',label:'ID',parent:me.doctype},{fieldname:'modified',fieldtype:'Date',label:'Last Modified',parent:me.doctype},{fieldname:'owner',fieldtype:'Data',label:'Created By',parent:me.doctype},{fieldname:'_user_tags',fieldtype:'Data',label:'Tags',parent:me.doctype}];$.each(std_filters.concat(fields_list[me.doctype]),function(i,df){me.add_field_option(df);});$.each(me.table_fields,function(i,table_df){if(table_df.options){$.each(fields_list[table_df.options],function(i,df){me.add_field_option(df);});}})},add_field_option:function(df){var me=this;if(me.doctype&&df.parent==me.doctype){var label=df.label;var table=get_label_doctype(me.doctype);if(df.fieldtype=='Table')me.table_fields.push(df);}else{var label=df.label+' ('+df.parent+')';var table=df.parent;}
if(wn.model.no_value_type.indexOf(df.fieldtype)==-1&&!me.fields_by_name[df.fieldname]){this.$select.append($('<option>',{value:df.fieldname,table:table}).text(label));me.fields_by_name[df.fieldname]=df;}},set_field:function(fieldname,fieldtype){var me=this;var cur=me.field?{fieldname:me.field.df.fieldname,fieldtype:me.field.df.fieldtype}:{}
var df=me.fields_by_name[fieldname];this.set_fieldtype(df,fieldtype);if(me.field&&cur.fieldname==fieldname&&df.fieldtype==cur.fieldtype){return;}
me.$w.find('.fieldname_select').val(fieldname);var field_area=me.$w.find('.filter_field').empty().get(0);f=make_field(df,null,field_area,null,0,1);f.df.single_select=1;f.not_in_form=1;f.with_label=0;f.refresh();me.field=f;this.set_default_condition(df,fieldtype);$(me.field.wrapper).find(':input').keydown(function(ev){if(ev.which==13){me.flist.listobj.run();}})},set_fieldtype:function(df,fieldtype){if(df.original_type)
df.fieldtype=df.original_type;else
df.original_type=df.fieldtype;df.description='';df.reqd=0;if(fieldtype){df.fieldtype=fieldtype;return;}
if(df.fieldtype=='Check'){df.fieldtype='Select';df.options='No\nYes';}else if(['Text','Text Editor','Code','Link'].indexOf(df.fieldtype)!=-1){df.fieldtype='Data';}},set_default_condition:function(df,fieldtype){if(!fieldtype){if(df.fieldtype=='Data'){this.$w.find('.condition').val('like');}else{this.$w.find('.condition').val('=');}}},get_value:function(){var me=this;var val=me.field.get_value();var cond=me.$w.find('.condition').val();if(me.field.df.original_type=='Check'){val=(val=='Yes'?1:0);}
if(cond=='like'){val=val+'%';}
return[me.$w.find('.fieldname_select option:selected').attr('table'),me.field.df.fieldname,me.$w.find('.condition').val(),val];}});
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
 *	lib/js/legacy/webpage/page_header.js
 */
var def_ph_style={wrapper:{marginBottom:'16px',backgroundColor:'#EEE'},main_heading:{},sub_heading:{marginBottom:'8px',color:'#555',display:'none'},separator:{borderTop:'1px solid #ddd'},toolbar_area:{padding:'3px 0px',display:'none',borderBottom:'1px solid #ddd'}}
function PageHeader(parent,main_text,sub_text){this.wrapper=$a(parent,'div','page_header');this.t1=make_table($a(this.wrapper,'div','',def_ph_style.wrapper.backgroundColor),1,2,'100%',[null,'100px'],{padding:'2px'});$y(this.t1,{borderCollapse:'collapse'})
this.lhs=$td(this.t1,0,0);this.main_head=$a(this.lhs,'h1','',def_ph_style.main_heading);this.sub_head=$a(this.lhs,'h4','',def_ph_style.sub_heading);this.separator=$a(this.wrapper,'div','',def_ph_style.separator);this.toolbar_area=$a(this.wrapper,'div','',def_ph_style.toolbar_area);this.padding_area=$a(this.wrapper,'div','',{padding:'3px'});$y($td(this.t1,0,1),{textAlign:'right',padding:'3px'});this.close_btn=$a($td(this.t1,0,1),'span','close',{},'&times;');this.close_btn.onclick=function(){window.history.back();};if(main_text)this.main_head.innerHTML=main_text;if(sub_text)this.sub_head.innerHTML=sub_text;this.buttons={};this.buttons2={};}
PageHeader.prototype.add_button=function(label,fn,bold,icon,green){var tb=this.toolbar_area;if(this.buttons[label])return;iconhtml=icon?('<i class="'+icon+'"></i> '):'';var $button=$('<button class="btn btn-small">'+iconhtml+label+'</button>').click(fn).appendTo(tb);if(green){$button.addClass('btn-info');$button.find('i').addClass('icon-white');}
if(bold)$button.css('font-weight','bold');this.buttons[label]=$button.get(0);$ds(this.toolbar_area);return this.buttons[label];}
PageHeader.prototype.clear_toolbar=function(){this.toolbar_area.innerHTML='';this.buttons={};}
PageHeader.prototype.make_buttonset=function(){$(this.toolbar_area).buttonset();}
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
 *	lib/js/legacy/webpage/error_console.js
 */
var err_console;var err_list=[];function errprint(t){if(!err_list)err_list=[];err_list.push('<pre style="font-family: Courier, Fixed; font-size: 11px; \
  border-bottom: 1px solid #AAA; overflow: auto; width: 90%;">'+t+'</pre>');}
$(document).bind('startup',function(){err_console=new Dialog(640,480,'Error Console')
err_console.make_body([['HTML','Error List'],['Button','Clear'],['HTML','Error Report']]);var span=$a(err_console.widgets['Error Report'],'span','link_type');span.innerHTML='Send Error Report';span.onclick=function(){msg=prompt('How / where did you get the error [optional]')
var call_back=function(r,rt){err_console.hide();msgprint("Error Report Sent")}
$c('webnotes.utils.send_error_report',{'err_msg':err_console.rows['Error List'].innerHTML,'msg':msg},call_back);}
err_console.widgets['Clear'].onclick=function(){err_list=[];err_console.rows['Error List'].innerHTML='';err_console.hide();}
err_console.onshow=function(){err_console.rows['Error List'].innerHTML='<div style="padding: 16px; height: 360px; width: 90%; overflow: auto;">'
+err_list.join('<div style="height: 10px; margin-bottom: 10px; border-bottom: 1px solid #AAA"></div>')+'</div>';}});
/*
 *	lib/js/legacy/webpage/loaders.js
 */
function loadreport(dt,rep_name,onload){if(rep_name)
wn.set_route('Report',dt,rep_name);else
wn.set_route('Report',dt);}
function loaddoc(doctype,name,onload){doctype=get_label_doctype(doctype);wn.model.with_doctype(doctype,function(){if(locals.DocType[doctype].in_dialog){console.log(1)
_f.edit_record(doctype,name);}else{wn.set_route('Form',doctype,name);}})}
var load_doc=loaddoc;function new_doc(doctype,onload,in_dialog,on_save_callback,cdt,cdn,cnic){doctype=get_label_doctype(doctype);wn.model.with_doctype(doctype,function(){if(locals.DocType[doctype].in_dialog){_f.edit_record(doctype,'New '+doctype);}else{wn.set_route('Form',doctype,'New '+doctype);}})}
var newdoc=new_doc;var pscript={};function loadpage(page_name,call_back,no_history){wn.set_route(page_name);}
function loaddocbrowser(dt){wn.set_route('List',dt);}
/*
 *	lib/js/legacy/webpage/uploader.js
 */
var uploaders={};var upload_frame_count=0;Uploader=function(parent,args,callback){var id='frame'+upload_frame_count;upload_frame_count++;this.callback=callback;var div=$a(parent,'div');div.innerHTML='<iframe id="'+id+'" name="'+id+'" src="blank.html" \
  style="width:0px; height:0px; border:0px"></iframe>';var div=$a(parent,'div');div.innerHTML='<form method="POST" enctype="multipart/form-data" action="'+wn.request.url+'" target="'+id+'"></form>';var ul_form=div.childNodes[0];var f_list=[];var inp_fdata=$a_input($a(ul_form,'span'),'file',{name:'filedata'},{marginLeft:'7px'});if(!('cmd'in args)){var inp=$a_input($a(ul_form,'span'),'hidden',{name:'cmd'});inp.value='uploadfile';}
var inp=$a_input($a(ul_form,'span'),'hidden',{name:'uploader_id'});inp.value=id;var inp=$a_input($a(ul_form,'span'),'submit',null,{marginLeft:'7px'});inp.value='Upload';$y(inp,{width:'80px'});for(var key in args){var inp=$a_input($a(ul_form,'span'),'hidden',{name:key});inp.value=args[key];}
uploaders[id]=this;}
function upload_callback(id,fid){uploaders[id].callback(fid);}
/*
 *	lib/js/legacy/webpage/page.js
 */
function Page(page_name,content){var me=this;this.name=page_name;this.trigger=function(event){try{if(pscript[event+'_'+this.name])
pscript[event+'_'+this.name](me.wrapper);if(me.wrapper[event]){me.wrapper[event](me.wrapper);}}catch(e){console.log(e);}}
this.page_show=function(){set_title(me.doc.title?me.doc.title:me.name);if(!me.onload_complete){me.trigger('onload');me.onload_complete=true;}
me.trigger('onshow');cur_frm=null;}
this.wrapper=wn.container.add_page(page_name,this.page_show);this.cont=this.wrapper
if(content)
this.wrapper.innerHTML=content;return this;}
function render_page(page_name,menuitem){if(!page_name)return;if((!locals['Page'])||(!locals['Page'][page_name])){loadpage('_home');return;}
var pdoc=locals['Page'][page_name];if(pdoc.style)set_style(pdoc.style)
var p=new Page(page_name,pdoc._Page__content?pdoc._Page__content:pdoc.content);var script=pdoc.__script?pdoc.__script:pdoc.script;p.doc=pdoc;if(script){eval(script);}
wn.container.change_to(page_name);return p;}
function refresh_page(page_name){var fn=function(r,rt){render_page(page_name)}
$c('webnotes.widgets.page.getpage',{'name':page_name},fn);}
/*
 *	lib/js/legacy/wn/page_layout.js
 */
wn.PageLayout=function(args){$.extend(this,args)
this.wrapper=$a(this.parent,'div','layout-wrapper layout-wrapper-background');this.main=$a(this.wrapper,'div','layout-main-section');this.sidebar_area=$a(this.wrapper,'div','layout-side-section');$a(this.wrapper,'div','',{clear:'both'});this.head=$a(this.main,'div');this.toolbar_area=$a(this.main,'div');this.body=$a(this.main,'div');this.footer=$a(this.main,'div');if(this.heading){this.page_head=new PageHeader(this.head,this.heading);}}
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
if(d.localname){wn.model.new_names[d.localname]=d.name;$(document).trigger('rename',[d.doctype,d.localname,d.name]);delete locals[d.doctype][d.localname];}}}
local_name_idx={};LocalDB.get_localname=function(doctype){if(!local_name_idx[doctype])local_name_idx[doctype]=1;var n='New '+get_doctype_label(doctype)+' '+local_name_idx[doctype];local_name_idx[doctype]++;return n;}
LocalDB.set_default_values=function(doc){var doctype=doc.doctype;var docfields=fields_list[doctype];if(!docfields){return;}
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
var _save=function(){$c('webnotes.widgets.form.save.savedocs',{'docs':compress_doclist(doclist),'docname':dn,'action':save_action,'user':user},function(r,rtxt){if(f){f.savingflag=false;}
if(r.saved){if(onsave)onsave(r);}else{if(onerr)onerr(r);}},function(){if(f){f.savingflag=false;}},0,(f?'Saving...':''));}
if(doc.__islocal&&(doctype&&doctype.autoname&&doctype.autoname.toLowerCase()=='prompt')){var newname=prompt('Enter the name of the new '+dt,'');if(newname){doc.__newname=strip(newname);_save();}else{msgprint('Not Saved');onerr();}}else{_save();}}
function check_required(dt,dn,parent_dt){var doc=locals[dt][dn];if(doc.docstatus>1)return true;var fl=fields_list[dt];if(!fl)return true;var all_clear=true;var errfld=[];for(var i=0;i<fl.length;i++){var key=fl[i].fieldname;var v=doc[key];if(fl[i].reqd&&is_null(v)&&fl[i].fieldname){errfld[errfld.length]=fl[i].label;if(cur_frm){var f=cur_frm.fields_dict[fl[i].fieldname];if(f){if(f.set_as_error)f.set_as_error(1);if(!cur_frm.error_in_section&&f.parent_section){cur_frm.set_section(f.parent_section.sec_id);cur_frm.error_in_section=1;}}}
if(all_clear)all_clear=false;}}
if(errfld.length)msgprint('<b>Mandatory fields required in '+
(doc.parenttype?(fields[doc.parenttype][doc.parentfield].label+' (Table)'):get_doctype_label(doc.doctype))+':</b>\n'+errfld.join('\n'));return all_clear;}
/*
 *	lib/js/legacy/app.js
 */
var popup_cont;var session={};if(!wn)var wn={};function startup(){popup_cont=$a(document.getElementsByTagName('body')[0],'div');var setup_globals=function(r){wn.boot=r;profile=r.profile;user=r.profile.name;user_fullname=wn.user_info(user).fullname;user_defaults=profile.defaults;user_roles=profile.roles;user_email=profile.email;home_page=r.home_page;_p.letter_heads=r.letter_heads;sys_defaults=r.sysdefaults;session.rt=profile.can_read;if(r.ipinfo)session.ipinfo=r.ipinfo;session.dt_labels=r.dt_labels;session.rev_dt_labels={}
if(r.dt_labels){for(key in r.dt_labels)session.rev_dt_labels[r.dt_labels[key]]=key;}
wn.control_panel=r.control_panel;}
var setup_viewport=function(){wn.container=new wn.views.Container();if(user=='Guest')
user_defaults.hide_webnotes_toolbar=1;if(!cint(user_defaults.hide_webnotes_toolbar)||user=='Administrator'){wn.container.wntoolbar=new wn.ui.toolbar.Toolbar();}
$(document).trigger('startup');try{if(wn.control_panel.custom_startup_code)
eval(wn.control_panel.custom_startup_code);}catch(e){errprint(e);}
var t=to_open();if(t){window.location.hash=t;}else if(home_page){loadpage(home_page);}
wn.route();$dh('startup_div');$ds('body_div');}
var callback=function(r,rt){if(r.exc)console.log(r.exc);setup_globals(r);setup_viewport();}
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
erpnext.startup.start=function(){$('#startup_div').html('Starting up...').toggle(true);erpnext.startup.set_globals();if(wn.boot.user_background){erpnext.set_user_background(wn.boot.user_background);}
if(user=='Guest'){if(wn.boot.custom_css){set_style(wn.boot.custom_css);}
if(wn.boot.website_settings.title_prefix){wn.title_prefix=wn.boot.website_settings.title_prefix;}}else{wn.boot.profile.allow_modules=wn.boot.profile.allow_modules.concat(['To Do','Knowledge Base','Calendar','Activity','Messages'])
erpnext.toolbar.setup();erpnext.startup.set_periodic_updates();if(in_list(user_roles,'System Manager')&&(wn.boot.setup_complete=='No')){wn.require("erpnext/startup/js/complete_setup.js");erpnext.complete_setup();}}
$('#startup_div').toggle(false);}
show_chart_browser=function(nm,chart_type){var call_back=function(){if(nm=='Sales Browser'){var sb_obj=new SalesBrowser();sb_obj.set_val(chart_type);}
else if(nm=='Accounts Browser')
pscript.make_chart(chart_type);}
loadpage(nm,call_back);}
var update_messages=function(reset){if(inList(['Guest'],user)||!wn.session_alive){return;}
if(!reset){$c_page('home','event_updates','get_global_status_messages',null,function(r,rt){if(!r.exc){wn.container.wntoolbar.set_new_comments(r.message.unread_messages);var show_in_circle=function(parent_id,msg){var parent=$('#'+parent_id);if(parent){if(msg){parent.find('span:first').text(msg);parent.toggle(true);}else{parent.toggle(false);}}}
show_in_circle('unread_messages',r.message.unread_messages.length);show_in_circle('open_support_tickets',r.message.open_support_tickets);show_in_circle('things_todo',r.message.things_todo);show_in_circle('todays_events',r.message.todays_events);}else{clearInterval(wn.updates.id);}});}else{wn.container.wntoolbar.set_new_comments(0);$('#unread_messages').toggle(false);}}
erpnext.startup.set_periodic_updates=function(){wn.updates={};if(wn.updates.id){clearInterval(wn.updates.id);}
wn.updates.id=setInterval(update_messages,60000);}
erpnext.set_user_background=function(src){set_style(repl('body { background: url("files/%(src)s") repeat;}',{src:src}))}
$(document).bind('startup',function(){erpnext.startup.start();});
/*
 *	erpnext/website/js/topbar.js
 */
wn.provide('erpnext.navbar');erpnext.navbar.Navbar=Class.extend({init:function(){this.make();$('.brand').html(wn.boot.website_settings.brand_html);this.make_items();$('.dropdown-toggle').dropdown();},make:function(){$('header').append('<div class="navbar navbar-fixed-top">\
   <div class="navbar-inner">\
   <div class="container">\
    <a class="brand">[brand]</a>\
    <ul class="nav">\
    </ul>\
    <img src="lib/images/ui/spinner.gif" id="spinner"/>\
    <ul class="nav pull-right">\
     <li><a href="#!Login Page">Login</a></li>\
    </ul>\
   </div>\
   </div>\
   </div>');$('.brand').attr('href','#!'+(wn.boot.website_settings.home_page||'Login Page'))},make_items:function(){var items=wn.boot.website_menus;for(var i=0;i<items.length;i++){var item=items[i];if(!item.parent_label&&item.parentfield=='top_bar_items'){item.route=item.url||item.custom_page;$('header .nav:first').append(repl('<li data-label="%(label)s">\
     <a href="#!%(route)s">%(label)s</a></li>',item))}}
for(var i=0;i<items.length;i++){var item=items[i];if(item.parent_label&&item.parentfield=='top_bar_items'){$parent_li=$(repl('header li[data-label="%(parent_label)s"]',item));if(!$parent_li.hasClass('dropdown')){$parent_li.addClass('dropdown');$parent_li.find('a:first').addClass('dropdown-toggle').attr('data-toggle','dropdown').attr('href','').append('<b class="caret"></b>').click(function(){return false;});$parent_li.append('<ul class="dropdown-menu"></ul>');}
item.route=item.url||item.custom_page;$parent_li.find('.dropdown-menu').append(repl('<li data-label="%(label)s">\
     <a href="#!%(route)s">%(label)s</a></li>',item))}}}});erpnext.Footer=Class.extend({init:function(){$('footer').html(repl('<div class="web-footer">\
   <div class="web-footer-menu"><ul></ul></div>\
   <div class="web-footer-address">%(address)s</div>\
   <div class="web-footer-copyright">&copy; %(copyright)s</div>\
   <div class="web-footer-powered">Powered by \
    <a href="https://erpnext.com">erpnext.com</a></div>\
  </div>',wn.boot.website_settings));this.make_items();},make_items:function(){var items=wn.boot.website_menus
for(var i=0;i<items.length;i++){var item=items[i];if(!item.parent_label&&item.parentfield=='footer_items'){item.route=item.url||item.custom_page;$('.web-footer-menu ul').append(repl('<li><a href="#!%(route)s" \
     data-label="%(label)s">%(label)s</a></li>',item))}}}});$(document).bind('startup',function(){erpnext.navbar.navbar=new erpnext.navbar.Navbar();})