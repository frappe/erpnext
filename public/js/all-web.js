
/*
 *	lib/js/lib/bootstrap.min.js
 */
!function(a){a(function(){"use strict",a.support.transition=function(){var b=document.body||document.documentElement,c=b.style,d=c.transition!==undefined||c.WebkitTransition!==undefined||c.MozTransition!==undefined||c.MsTransition!==undefined||c.OTransition!==undefined;return d&&{end:function(){var b="TransitionEnd";return a.browser.webkit?b="webkitTransitionEnd":a.browser.mozilla?b="transitionend":a.browser.opera&&(b="oTransitionEnd"),b}()}}()})}(window.jQuery),!function(a){"use strict";var b='[data-dismiss="alert"]',c=function(c){a(c).on("click",b,this.close)};c.prototype={constructor:c,close:function(b){function f(){e.remove(),e.trigger("closed")}var c=a(this),d=c.attr("data-target"),e;d||(d=c.attr("href"),d=d&&d.replace(/.*(?=#[^\s]*$)/,"")),e=a(d),e.trigger("close"),b&&b.preventDefault(),e.length||(e=c.hasClass("alert")?c:c.parent()),e.removeClass("in"),a.support.transition&&e.hasClass("fade")?e.on(a.support.transition.end,f):f()}},a.fn.alert=function(b){return this.each(function(){var d=a(this),e=d.data("alert");e||d.data("alert",e=new c(this)),typeof b=="string"&&e[b].call(d)})},a.fn.alert.Constructor=c,a(function(){a("body").on("click.alert.data-api",b,c.prototype.close)})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.button.defaults,c)};b.prototype={constructor:b,setState:function(a){var b="disabled",c=this.$element,d=c.data(),e=c.is("input")?"val":"html";a+="Text",d.resetText||c.data("resetText",c[e]()),c[e](d[a]||this.options[a]),setTimeout(function(){a=="loadingText"?c.addClass(b).attr(b,b):c.removeClass(b).removeAttr(b)},0)},toggle:function(){var a=this.$element.parent('[data-toggle="buttons-radio"]');a&&a.find(".active").removeClass("active"),this.$element.toggleClass("active")}},a.fn.button=function(c){return this.each(function(){var d=a(this),e=d.data("button"),f=typeof c=="object"&&c;e||d.data("button",e=new b(this,f)),c=="toggle"?e.toggle():c&&e.setState(c)})},a.fn.button.defaults={loadingText:"loading..."},a.fn.button.Constructor=b,a(function(){a("body").on("click.button.data-api","[data-toggle^=button]",function(b){a(b.target).button("toggle")})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.carousel.defaults,c),this.options.slide&&this.slide(this.options.slide)};b.prototype={cycle:function(){return this.interval=setInterval(a.proxy(this.next,this),this.options.interval),this},to:function(b){var c=this.$element.find(".active"),d=c.parent().children(),e=d.index(c),f=this;if(b>d.length-1||b<0)return;return this.sliding?this.$element.one("slid",function(){f.to(b)}):e==b?this.pause().cycle():this.slide(b>e?"next":"prev",a(d[b]))},pause:function(){return clearInterval(this.interval),this},next:function(){if(this.sliding)return;return this.slide("next")},prev:function(){if(this.sliding)return;return this.slide("prev")},slide:function(b,c){var d=this.$element.find(".active"),e=c||d[b](),f=this.interval,g=b=="next"?"left":"right",h=b=="next"?"first":"last",i=this;return this.sliding=!0,f&&this.pause(),e=e.length?e:this.$element.find(".item")[h](),!a.support.transition&&this.$element.hasClass("slide")?(this.$element.trigger("slide"),d.removeClass("active"),e.addClass("active"),this.sliding=!1,this.$element.trigger("slid")):(e.addClass(b),e[0].offsetWidth,d.addClass(g),e.addClass(g),this.$element.trigger("slide"),this.$element.one(a.support.transition.end,function(){e.removeClass([b,g].join(" ")).addClass("active"),d.removeClass(["active",g].join(" ")),i.sliding=!1,setTimeout(function(){i.$element.trigger("slid")},0)})),f&&this.cycle(),this}},a.fn.carousel=function(c){return this.each(function(){var d=a(this),e=d.data("carousel"),f=typeof c=="object"&&c;e||d.data("carousel",e=new b(this,f)),typeof c=="number"?e.to(c):typeof c=="string"||(c=f.slide)?e[c]():e.cycle()})},a.fn.carousel.defaults={interval:5e3},a.fn.carousel.Constructor=b,a(function(){a("body").on("click.carousel.data-api","[data-slide]",function(b){var c=a(this),d,e=a(c.attr("data-target")||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,"")),f=!e.data("modal")&&a.extend({},e.data(),c.data());e.carousel(f),b.preventDefault()})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.collapse.defaults,c),this.options.parent&&(this.$parent=a(this.options.parent)),this.options.toggle&&this.toggle()};b.prototype={constructor:b,dimension:function(){var a=this.$element.hasClass("width");return a?"width":"height"},show:function(){var b=this.dimension(),c=a.camelCase(["scroll",b].join("-")),d=this.$parent&&this.$parent.find(".in"),e;d&&d.length&&(e=d.data("collapse"),d.collapse("hide"),e||d.data("collapse",null)),this.$element[b](0),this.transition("addClass","show","shown"),this.$element[b](this.$element[0][c])},hide:function(){var a=this.dimension();this.reset(this.$element[a]()),this.transition("removeClass","hide","hidden"),this.$element[a](0)},reset:function(a){var b=this.dimension();this.$element.removeClass("collapse")[b](a||"auto")[0].offsetWidth,this.$element.addClass("collapse")},transition:function(b,c,d){var e=this,f=function(){c=="show"&&e.reset(),e.$element.trigger(d)};this.$element.trigger(c)[b]("in"),a.support.transition&&this.$element.hasClass("collapse")?this.$element.one(a.support.transition.end,f):f()},toggle:function(){this[this.$element.hasClass("in")?"hide":"show"]()}},a.fn.collapse=function(c){return this.each(function(){var d=a(this),e=d.data("collapse"),f=typeof c=="object"&&c;e||d.data("collapse",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.collapse.defaults={toggle:!0},a.fn.collapse.Constructor=b,a(function(){a("body").on("click.collapse.data-api","[data-toggle=collapse]",function(b){var c=a(this),d,e=c.attr("data-target")||b.preventDefault()||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,""),f=a(e).data("collapse")?"toggle":c.data();a(e).collapse(f)})})}(window.jQuery),!function(a){function d(){a(b).parent().removeClass("open")}"use strict";var b='[data-toggle="dropdown"]',c=function(b){var c=a(b).on("click.dropdown.data-api",this.toggle);a("html").on("click.dropdown.data-api",function(){c.parent().removeClass("open")})};c.prototype={constructor:c,toggle:function(b){var c=a(this),e=c.attr("data-target"),f,g;return e||(e=c.attr("href"),e=e&&e.replace(/.*(?=#[^\s]*$)/,"")),f=a(e),f.length||(f=c.parent()),g=f.hasClass("open"),d(),!g&&f.toggleClass("open"),!1}},a.fn.dropdown=function(b){return this.each(function(){var d=a(this),e=d.data("dropdown");e||d.data("dropdown",e=new c(this)),typeof b=="string"&&e[b].call(d)})},a.fn.dropdown.Constructor=c,a(function(){a("html").on("click.dropdown.data-api",d),a("body").on("click.dropdown.data-api",b,c.prototype.toggle)})}(window.jQuery),!function(a){function c(){var b=this,c=setTimeout(function(){b.$element.off(a.support.transition.end),d.call(b)},500);this.$element.one(a.support.transition.end,function(){clearTimeout(c),d.call(b)})}function d(a){this.$element.hide().trigger("hidden"),e.call(this)}function e(b){var c=this,d=this.$element.hasClass("fade")?"fade":"";if(this.isShown&&this.options.backdrop){var e=a.support.transition&&d;this.$backdrop=a('<div class="modal-backdrop '+d+'" />').appendTo(document.body),this.options.backdrop!="static"&&this.$backdrop.click(a.proxy(this.hide,this)),e&&this.$backdrop[0].offsetWidth,this.$backdrop.addClass("in"),e?this.$backdrop.one(a.support.transition.end,b):b()}else!this.isShown&&this.$backdrop?(this.$backdrop.removeClass("in"),a.support.transition&&this.$element.hasClass("fade")?this.$backdrop.one(a.support.transition.end,a.proxy(f,this)):f.call(this)):b&&b()}function f(){this.$backdrop.remove(),this.$backdrop=null}function g(){var b=this;this.isShown&&this.options.keyboard?a(document).on("keyup.dismiss.modal",function(a){a.which==27&&b.hide()}):this.isShown||a(document).off("keyup.dismiss.modal")}"use strict";var b=function(b,c){this.options=a.extend({},a.fn.modal.defaults,c),this.$element=a(b).delegate('[data-dismiss="modal"]',"click.dismiss.modal",a.proxy(this.hide,this))};b.prototype={constructor:b,toggle:function(){return this[this.isShown?"hide":"show"]()},show:function(){var b=this;if(this.isShown)return;a("body").addClass("modal-open"),this.isShown=!0,this.$element.trigger("show"),g.call(this),e.call(this,function(){var c=a.support.transition&&b.$element.hasClass("fade");!b.$element.parent().length&&b.$element.appendTo(document.body),b.$element.show(),c&&b.$element[0].offsetWidth,b.$element.addClass("in"),c?b.$element.one(a.support.transition.end,function(){b.$element.trigger("shown")}):b.$element.trigger("shown")})},hide:function(b){b&&b.preventDefault();if(!this.isShown)return;var e=this;this.isShown=!1,a("body").removeClass("modal-open"),g.call(this),this.$element.trigger("hide").removeClass("in"),a.support.transition&&this.$element.hasClass("fade")?c.call(this):d.call(this)}},a.fn.modal=function(c){return this.each(function(){var d=a(this),e=d.data("modal"),f=typeof c=="object"&&c;e||d.data("modal",e=new b(this,f)),typeof c=="string"?e[c]():e.show()})},a.fn.modal.defaults={backdrop:!0,keyboard:!0},a.fn.modal.Constructor=b,a(function(){a("body").on("click.modal.data-api",'[data-toggle="modal"]',function(b){var c=a(this),d,e=a(c.attr("data-target")||(d=c.attr("href"))&&d.replace(/.*(?=#[^\s]+$)/,"")),f=e.data("modal")?"toggle":a.extend({},e.data(),c.data());b.preventDefault(),e.modal(f)})})}(window.jQuery),!function(a){"use strict";var b=function(a,b){this.init("tooltip",a,b)};b.prototype={constructor:b,init:function(b,c,d){var e,f;this.type=b,this.$element=a(c),this.options=this.getOptions(d),this.enabled=!0,this.options.trigger!="manual"&&(e=this.options.trigger=="hover"?"mouseenter":"focus",f=this.options.trigger=="hover"?"mouseleave":"blur",this.$element.on(e,this.options.selector,a.proxy(this.enter,this)),this.$element.on(f,this.options.selector,a.proxy(this.leave,this))),this.options.selector?this._options=a.extend({},this.options,{trigger:"manual",selector:""}):this.fixTitle()},getOptions:function(b){return b=a.extend({},a.fn[this.type].defaults,b,this.$element.data()),b.delay&&typeof b.delay=="number"&&(b.delay={show:b.delay,hide:b.delay}),b},enter:function(b){var c=a(b.currentTarget)[this.type](this._options).data(this.type);!c.options.delay||!c.options.delay.show?c.show():(c.hoverState="in",setTimeout(function(){c.hoverState=="in"&&c.show()},c.options.delay.show))},leave:function(b){var c=a(b.currentTarget)[this.type](this._options).data(this.type);!c.options.delay||!c.options.delay.hide?c.hide():(c.hoverState="out",setTimeout(function(){c.hoverState=="out"&&c.hide()},c.options.delay.hide))},show:function(){var a,b,c,d,e,f,g;if(this.hasContent()&&this.enabled){a=this.tip(),this.setContent(),this.options.animation&&a.addClass("fade"),f=typeof this.options.placement=="function"?this.options.placement.call(this,a[0],this.$element[0]):this.options.placement,b=/in/.test(f),a.remove().css({top:0,left:0,display:"block"}).appendTo(b?this.$element:document.body),c=this.getPosition(b),d=a[0].offsetWidth,e=a[0].offsetHeight;switch(b?f.split(" ")[1]:f){case"bottom":g={top:c.top+c.height,left:c.left+c.width/2-d/2};break;case"top":g={top:c.top-e,left:c.left+c.width/2-d/2};break;case"left":g={top:c.top+c.height/2-e/2,left:c.left-d};break;case"right":g={top:c.top+c.height/2-e/2,left:c.left+c.width}}a.css(g).addClass(f).addClass("in")}},setContent:function(){var a=this.tip();a.find(".tooltip-inner").html(this.getTitle()),a.removeClass("fade in top bottom left right")},hide:function(){function d(){var b=setTimeout(function(){c.off(a.support.transition.end).remove()},500);c.one(a.support.transition.end,function(){clearTimeout(b),c.remove()})}var b=this,c=this.tip();c.removeClass("in"),a.support.transition&&this.$tip.hasClass("fade")?d():c.remove()},fixTitle:function(){var a=this.$element;(a.attr("title")||typeof a.attr("data-original-title")!="string")&&a.attr("data-original-title",a.attr("title")||"").removeAttr("title")},hasContent:function(){return this.getTitle()},getPosition:function(b){return a.extend({},b?{top:0,left:0}:this.$element.offset(),{width:this.$element[0].offsetWidth,height:this.$element[0].offsetHeight})},getTitle:function(){var a,b=this.$element,c=this.options;return a=b.attr("data-original-title")||(typeof c.title=="function"?c.title.call(b[0]):c.title),a=a.toString().replace(/(^\s*|\s*$)/,""),a},tip:function(){return this.$tip=this.$tip||a(this.options.template)},validate:function(){this.$element[0].parentNode||(this.hide(),this.$element=null,this.options=null)},enable:function(){this.enabled=!0},disable:function(){this.enabled=!1},toggleEnabled:function(){this.enabled=!this.enabled},toggle:function(){this[this.tip().hasClass("in")?"hide":"show"]()}},a.fn.tooltip=function(c){return this.each(function(){var d=a(this),e=d.data("tooltip"),f=typeof c=="object"&&c;e||d.data("tooltip",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.tooltip.Constructor=b,a.fn.tooltip.defaults={animation:!0,delay:0,selector:!1,placement:"top",trigger:"hover",title:"",template:'<div class="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'}}(window.jQuery),!function(a){"use strict";var b=function(a,b){this.init("popover",a,b)};b.prototype=a.extend({},a.fn.tooltip.Constructor.prototype,{constructor:b,setContent:function(){var b=this.tip(),c=this.getTitle(),d=this.getContent();b.find(".popover-title")[a.type(c)=="object"?"append":"html"](c),b.find(".popover-content > *")[a.type(d)=="object"?"append":"html"](d),b.removeClass("fade top bottom left right in")},hasContent:function(){return this.getTitle()||this.getContent()},getContent:function(){var a,b=this.$element,c=this.options;return a=b.attr("data-content")||(typeof c.content=="function"?c.content.call(b[0]):c.content),a=a.toString().replace(/(^\s*|\s*$)/,""),a},tip:function(){return this.$tip||(this.$tip=a(this.options.template)),this.$tip}}),a.fn.popover=function(c){return this.each(function(){var d=a(this),e=d.data("popover"),f=typeof c=="object"&&c;e||d.data("popover",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.popover.Constructor=b,a.fn.popover.defaults=a.extend({},a.fn.tooltip.defaults,{placement:"right",content:"",template:'<div class="popover"><div class="arrow"></div><div class="popover-inner"><h3 class="popover-title"></h3><div class="popover-content"><p></p></div></div></div>'})}(window.jQuery),!function(a){function b(b,c){var d=a.proxy(this.process,this),e=a(b).is("body")?a(window):a(b),f;this.options=a.extend({},a.fn.scrollspy.defaults,c),this.$scrollElement=e.on("scroll.scroll.data-api",d),this.selector=(this.options.target||(f=a(b).attr("href"))&&f.replace(/.*(?=#[^\s]+$)/,"")||"")+" .nav li > a",this.$body=a("body").on("click.scroll.data-api",this.selector,d),this.refresh(),this.process()}"use strict",b.prototype={constructor:b,refresh:function(){this.targets=this.$body.find(this.selector).map(function(){var b=a(this).attr("href");return/^#\w/.test(b)&&a(b).length?b:null}),this.offsets=a.map(this.targets,function(b){return a(b).position().top})},process:function(){var a=this.$scrollElement.scrollTop()+this.options.offset,b=this.offsets,c=this.targets,d=this.activeTarget,e;for(e=b.length;e--;)d!=c[e]&&a>=b[e]&&(!b[e+1]||a<=b[e+1])&&this.activate(c[e])},activate:function(a){var b;this.activeTarget=a,this.$body.find(this.selector).parent(".active").removeClass("active"),b=this.$body.find(this.selector+'[href="'+a+'"]').parent("li").addClass("active"),b.parent(".dropdown-menu")&&b.closest("li.dropdown").addClass("active")}},a.fn.scrollspy=function(c){return this.each(function(){var d=a(this),e=d.data("scrollspy"),f=typeof c=="object"&&c;e||d.data("scrollspy",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.scrollspy.Constructor=b,a.fn.scrollspy.defaults={offset:10},a(function(){a('[data-spy="scroll"]').each(function(){var b=a(this);b.scrollspy(b.data())})})}(window.jQuery),!function(a){"use strict";var b=function(b){this.element=a(b)};b.prototype={constructor:b,show:function(){var b=this.element,c=b.closest("ul:not(.dropdown-menu)"),d=b.attr("data-target"),e,f;d||(d=b.attr("href"),d=d&&d.replace(/.*(?=#[^\s]*$)/,""));if(b.parent("li").hasClass("active"))return;e=c.find(".active a").last()[0],b.trigger({type:"show",relatedTarget:e}),f=a(d),this.activate(b.parent("li"),c),this.activate(f,f.parent(),function(){b.trigger({type:"shown",relatedTarget:e})})},activate:function(b,c,d){function g(){e.removeClass("active").find("> .dropdown-menu > .active").removeClass("active"),b.addClass("active"),f?(b[0].offsetWidth,b.addClass("in")):b.removeClass("fade"),b.parent(".dropdown-menu")&&b.closest("li.dropdown").addClass("active"),d&&d()}var e=c.find("> .active"),f=d&&a.support.transition&&e.hasClass("fade");f?e.one(a.support.transition.end,g):g(),e.removeClass("in")}},a.fn.tab=function(c){return this.each(function(){var d=a(this),e=d.data("tab");e||d.data("tab",e=new b(this)),typeof c=="string"&&e[c]()})},a.fn.tab.Constructor=b,a(function(){a("body").on("click.tab.data-api",'[data-toggle="tab"], [data-toggle="pill"]',function(b){b.preventDefault(),a(this).tab("show")})})}(window.jQuery),!function(a){"use strict";var b=function(b,c){this.$element=a(b),this.options=a.extend({},a.fn.typeahead.defaults,c),this.matcher=this.options.matcher||this.matcher,this.sorter=this.options.sorter||this.sorter,this.highlighter=this.options.highlighter||this.highlighter,this.$menu=a(this.options.menu).appendTo("body"),this.source=this.options.source,this.shown=!1,this.listen()};b.prototype={constructor:b,select:function(){var a=this.$menu.find(".active").attr("data-value");return this.$element.val(a),this.hide()},show:function(){var b=a.extend({},this.$element.offset(),{height:this.$element[0].offsetHeight});return this.$menu.css({top:b.top+b.height,left:b.left}),this.$menu.show(),this.shown=!0,this},hide:function(){return this.$menu.hide(),this.shown=!1,this},lookup:function(b){var c=this,d,e;return this.query=this.$element.val(),this.query?(d=a.grep(this.source,function(a){if(c.matcher(a))return a}),d=this.sorter(d),d.length?this.render(d.slice(0,this.options.items)).show():this.shown?this.hide():this):this.shown?this.hide():this},matcher:function(a){return~a.toLowerCase().indexOf(this.query.toLowerCase())},sorter:function(a){var b=[],c=[],d=[],e;while(e=a.shift())e.toLowerCase().indexOf(this.query.toLowerCase())?~e.indexOf(this.query)?c.push(e):d.push(e):b.push(e);return b.concat(c,d)},highlighter:function(a){return a.replace(new RegExp("("+this.query+")","ig"),function(a,b){return"<strong>"+b+"</strong>"})},render:function(b){var c=this;return b=a(b).map(function(b,d){return b=a(c.options.item).attr("data-value",d),b.find("a").html(c.highlighter(d)),b[0]}),b.first().addClass("active"),this.$menu.html(b),this},next:function(b){var c=this.$menu.find(".active").removeClass("active"),d=c.next();d.length||(d=a(this.$menu.find("li")[0])),d.addClass("active")},prev:function(a){var b=this.$menu.find(".active").removeClass("active"),c=b.prev();c.length||(c=this.$menu.find("li").last()),c.addClass("active")},listen:function(){this.$element.on("blur",a.proxy(this.blur,this)).on("keypress",a.proxy(this.keypress,this)).on("keyup",a.proxy(this.keyup,this)),(a.browser.webkit||a.browser.msie)&&this.$element.on("keydown",a.proxy(this.keypress,this)),this.$menu.on("click",a.proxy(this.click,this)).on("mouseenter","li",a.proxy(this.mouseenter,this))},keyup:function(a){a.stopPropagation(),a.preventDefault();switch(a.keyCode){case 40:case 38:break;case 9:case 13:if(!this.shown)return;this.select();break;case 27:this.hide();break;default:this.lookup()}},keypress:function(a){a.stopPropagation();if(!this.shown)return;switch(a.keyCode){case 9:case 13:case 27:a.preventDefault();break;case 38:a.preventDefault(),this.prev();break;case 40:a.preventDefault(),this.next()}},blur:function(a){var b=this;a.stopPropagation(),a.preventDefault(),setTimeout(function(){b.hide()},150)},click:function(a){a.stopPropagation(),a.preventDefault(),this.select()},mouseenter:function(b){this.$menu.find(".active").removeClass("active"),a(b.currentTarget).addClass("active")}},a.fn.typeahead=function(c){return this.each(function(){var d=a(this),e=d.data("typeahead"),f=typeof c=="object"&&c;e||d.data("typeahead",e=new b(this,f)),typeof c=="string"&&e[c]()})},a.fn.typeahead.defaults={source:[],items:8,menu:'<ul class="typeahead dropdown-menu"></ul>',item:'<li><a href="#"></a></li>'},a.fn.typeahead.Constructor=b,a(function(){a("body").on("focus.typeahead.data-api",'[data-provide="typeahead"]',function(b){var c=a(this);if(c.data("typeahead"))return;b.preventDefault(),c.typeahead(c.data())})})}(window.jQuery);

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
 *	lib/js/wn/assets.js
 */
wn.require=function(items){if(typeof items==="string"){items=[items];}
var l=items.length;for(var i=0;i<l;i++){var src=items[i];wn.assets.execute(src);}}
wn.assets={executed_:{},check:function(){if(window._version_number!=localStorage.getItem("_version_number")){localStorage.clear();localStorage.setItem("_version_number",window._version_number)}},exists:function(src){if('localStorage'in window&&localStorage.getItem(src))
return true},add:function(src,txt){if('localStorage'in window){localStorage.setItem(src,txt);}},get:function(src){return localStorage.getItem(src);},extn:function(src){if(src.indexOf('?')!=-1){src=src.split('?').slice(-1)[0];}
return src.split('.').slice(-1)[0];},load:function(src){var t=src;$.ajax({url:t,data:{q:Math.floor(Math.random()*1000)},dataType:'text',success:function(txt){wn.assets.add(src,txt);},async:false})},execute:function(src){if(!wn.assets.exists(src)){wn.assets.load(src);}
var type=wn.assets.extn(src);if(wn.assets.handler[type]){wn.assets.handler[type](wn.assets.get(src),src);wn.assets.executed_[src]=1;}},handler:{js:function(txt,src){wn.dom.eval(txt);},css:function(txt,src){wn.dom.set_style(txt);}}}
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
this.selectedIndex=0;return $(this);}
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
if(this.new_doctype){this.add_button('New '+this.new_doctype,function(){(me.custom_new_doc||me.make_new_doc)(me.new_doctype);},'icon-plus');}
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
this.add_filter();},add_filter:function(tablename,fieldname,condition,value){this.push_new_filter(tablename,fieldname,condition,value);if(fieldname){this.$w.find('.show_filters').toggle(true);}},push_new_filter:function(tablename,fieldname,condition,value){this.filters.push(new wn.ui.Filter({flist:this,tablename:tablename,fieldname:fieldname,condition:condition,value:value}));},get_filters:function(){var values=[];$.each(this.filters,function(i,f){if(f.field)
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
  </div>');this.$w=this.flist.$w.find('.list_filter:last-child');},make_select:function(){this.fieldselect=new wn.ui.FieldSelect(this.$w.find('.fieldname_select_area'),this.doctype,this.filter_fields);},set_events:function(){var me=this;this.fieldselect.$select.bind('change',function(){var $selected=$(this).find("option:selected")
me.set_field($selected.attr("table"),$selected.attr("fieldname"));});this.$w.find('a.close').bind('click',function(){me.$w.css('display','none');var value=me.field.get_value();me.field=null;if(!me.flist.get_filters().length){me.flist.$w.find('.set_filters').toggle(true);me.flist.$w.find('.show_filters').toggle(false);}
if(value){me.flist.listobj.run();}
me.flist.update_filters();return false;});me.$w.find('.condition').change(function(){if($(this).val()=='in'){me.set_field(me.field.df.parent,me.field.df.fieldname,'Data');if(!me.field.desc_area)
me.field.desc_area=$a(me.field.wrapper,'span','help',null,'values separated by comma');}else{me.set_field(me.field.df.parent,me.field.df.fieldname);}});if(me.fieldname){this.set_values(me.tablename,me.fieldname,me.condition,me.value);}else{me.set_field(me.doctype,'name');}},set_values:function(tablename,fieldname,condition,value){this.set_field(tablename,fieldname);if(condition)this.$w.find('.condition').val(condition).change();if(value)this.field.set_input(value)},set_field:function(tablename,fieldname,fieldtype){var me=this;var cur=me.field?{fieldname:me.field.df.fieldname,fieldtype:me.field.df.fieldtype,parent:me.field.df.parent,}:{}
var df=me.fieldselect.fields_by_name[tablename][fieldname];this.set_fieldtype(df,fieldtype);if(me.field&&cur.fieldname==fieldname&&df.fieldtype==cur.fieldtype&&df.parent==cur.parent){return;}
me.fieldselect.$select.val(tablename+"."+fieldname);var field_area=me.$w.find('.filter_field').empty().get(0);f=make_field(df,null,field_area,null,0,1);f.df.single_select=1;f.not_in_form=1;f.with_label=0;f.refresh();me.field=f;this.set_default_condition(df,fieldtype);$(me.field.wrapper).find(':input').keydown(function(ev){if(ev.which==13){me.flist.listobj.run();}})},set_fieldtype:function(df,fieldtype){if(df.original_type)
df.fieldtype=df.original_type;else
df.original_type=df.fieldtype;df.description='';df.reqd=0;if(fieldtype){df.fieldtype=fieldtype;return;}
if(df.fieldtype=='Check'){df.fieldtype='Select';df.options='No\nYes';}else if(['Text','Text Editor','Code','Link'].indexOf(df.fieldtype)!=-1){df.fieldtype='Data';}},set_default_condition:function(df,fieldtype){if(!fieldtype){if(df.fieldtype=='Data'){this.$w.find('.condition').val('like');}else{this.$w.find('.condition').val('=');}}},get_value:function(){var me=this;var val=me.field.get_value();var cond=me.$w.find('.condition').val();if(me.field.df.original_type=='Check'){val=(val=='Yes'?1:0);}
if(cond=='like'){if((val.length===0)||(val.lastIndexOf("%")!==(val.length-1))){val=(val||"")+'%';}}
return[me.fieldselect.$select.find('option:selected').attr('table'),me.field.df.fieldname,me.$w.find('.condition').val(),cstr(val)];}});wn.ui.FieldSelect=Class.extend({init:function(parent,doctype,filter_fields,with_blank){this.doctype=doctype;this.fields_by_name={};this.with_blank=with_blank;this.$select=$('<select>').appendTo(parent);if(filter_fields){for(var i in filter_fields)
this.add_field_option(this.filter_fields[i])}else{this.build_options();}},build_options:function(){var me=this;me.table_fields=[];var std_filters=[{fieldname:'name',fieldtype:'Data',label:'ID',parent:me.doctype},{fieldname:'modified',fieldtype:'Date',label:'Last Modified',parent:me.doctype},{fieldname:'owner',fieldtype:'Data',label:'Created By',parent:me.doctype},{fieldname:'creation',fieldtype:'Date',label:'Created On',parent:me.doctype},{fieldname:'_user_tags',fieldtype:'Data',label:'Tags',parent:me.doctype},{fieldname:'docstatus',fieldtype:'Int',label:'Doc Status',parent:me.doctype},];var doctype_obj=locals['DocType'][me.doctype];if(doctype_obj&&cint(doctype_obj.istable)){std_filters=std_filters.concat([{fieldname:'parent',fieldtype:'Data',label:'Parent',parent:me.doctype}]);}
if(this.with_blank){this.$select.append($('<option>',{value:''}).text(''));}
$.each(std_filters.concat(wn.meta.docfield_list[me.doctype]),function(i,df){me.add_field_option(df);});$.each(me.table_fields,function(i,table_df){if(table_df.options){$.each(wn.meta.docfield_list[table_df.options],function(i,df){me.add_field_option(df);});}});},add_field_option:function(df){var me=this;if(me.doctype&&df.parent==me.doctype){var label=df.label;var table=me.doctype;if(df.fieldtype=='Table')me.table_fields.push(df);}else{var label=df.label+' ('+df.parent+')';var table=df.parent;}
if(wn.model.no_value_type.indexOf(df.fieldtype)==-1&&!(me.fields_by_name[df.parent]&&me.fields_by_name[df.parent][df.fieldname])){this.$select.append($('<option>',{value:table+"."+df.fieldname,fieldname:df.fieldname,table:df.parent}).text(label));if(!me.fields_by_name[df.parent])me.fields_by_name[df.parent]={};me.fields_by_name[df.parent][df.fieldname]=df;}}})
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
wn.request.call=function(opts){wn.request.prepare(opts);var ajax_args={url:opts.url||wn.request.url,data:opts.args,type:opts.type||'POST',dataType:opts.dataType||'json',success:function(r,xhr){wn.request.cleanup(opts,r);opts.success(r,xhr.responseText);},error:function(xhr,textStatus){wn.request.cleanup(opts,{});show_alert('Unable to complete request: '+textStatus)
if(opts.error)opts.error(xhr)}};if(opts.progress_bar){var interval=null;$.extend(ajax_args,{xhr:function(){var xhr=jQuery.ajaxSettings.xhr();interval=setInterval(function(){if(xhr.readyState>2){var total=parseInt(xhr.getResponseHeader('Content-length'));var completed=parseInt(xhr.responseText.length);var percent=(100.0/total*completed).toFixed(2)
opts.progress_bar.css('width',(percent<10?10:percent)+'%');}},50);return xhr;},complete:function(){clearInterval(interval);}})}
$.ajax(ajax_args);}
wn.call=function(opts){var args=$.extend({},opts.args)
if(opts.module&&opts.page){args.cmd=opts.module+'.page.'+opts.page+'.'+opts.page+'.'+opts.method}else if(opts.method){args.cmd=opts.method;}
for(key in args){if(args[key]&&typeof args[key]!='string'){args[key]=JSON.stringify(args[key]);}}
wn.request.call({args:args,success:opts.callback,error:opts.error,btn:opts.btn,freeze:opts.freeze,show_spinner:!opts.no_spinner,progress_bar:opts.progress_bar});}
/*
 *	lib/js/core.js
 */
if(!console){var console={log:function(txt){}}}
window._version_number="%(_version_number)s";$(document).ready(function(){wn.assets.check();wn.provide('wn.app');$.extend(wn.app,new wn.Application());});

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
else if(user_fmt=='mm-dd-yyyy'){var d=d.split('-');return d[2]+'-'+d[0]+'-'+d[1];}},user_to_obj:function(d){return dateutil.str_to_obj(dateutil.user_to_str(d));},global_date_format:function(d){if(d.substr)d=this.str_to_obj(d);return nth(d.getDate())+' '+month_list_full[d.getMonth()]+' '+d.getFullYear();},get_today:function(){var today=new Date();var m=(today.getMonth()+1)+'';if(m.length==1)m='0'+m;var d=today.getDate()+'';if(d.length==1)d='0'+d;return today.getFullYear()+'-'+m+'-'+d;},get_cur_time:function(){var d=new Date();var hh=d.getHours()+''
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
 *	lib/js/wn/ui/appframe.js
 */
wn.ui.AppFrame=Class.extend({init:function(parent,title){this.buttons={};this.$w=$('<div></div>').appendTo(parent);this.$titlebar=$('<div class="appframe-titlebar">\
   <span class="appframe-title"></span>\
   <span class="close">&times;</span>\
  </div>').appendTo(this.$w);this.$w.find('.close').click(function(){window.history.back();})
if(title)this.title(title);},title:function(txt){this.$titlebar.find('.appframe-title').html(txt);},add_button:function(label,click,icon){this.add_toolbar();args={label:label,icon:''};if(icon){args.icon='<i class="'+icon+'"></i>';}
this.buttons[label]=$(repl('<button class="btn btn-small">\
   %(icon)s %(label)s</button>',args)).click(click).appendTo(this.toolbar);return this.buttons[label];},clear_buttons:function(){this.toolbar&&this.toolbar.empty();},add_toolbar:function(){if(!this.toolbar)
this.$w.append('<div class="appframe-toolbar"></div>');this.toolbar=this.$w.find('.appframe-toolbar');},add_label:function(label){return $("<span style='margin: 2px 4px;'>"+label+" </span>").appendTo(this.toolbar);},add_select:function(label,options){this.add_toolbar();return $("<select style='width: 160px; margin: 2px 4px;'>").add_options(options).appendTo(this.toolbar);},add_date:function(label,date){this.add_toolbar();return $("<input style='width: 80px; margin: 2px 4px;'>").datepicker({dateFormat:sys_defaults.date_format.replace("yyyy","yy"),changeYear:true,}).val(dateutil.str_to_user(date)||"").appendTo(this.toolbar);},});wn.ui.make_app_page=function(opts){if(opts.single_column){$(opts.parent).html('<div class="layout-wrapper layout-wrapper-appframe">\
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
 *	lib/js/legacy/webpage/page_header.js
 */
var def_ph_style={wrapper:{marginBottom:'16px',backgroundColor:'#EEE'},main_heading:{},sub_heading:{marginBottom:'8px',color:'#555',display:'none'},separator:{borderTop:'1px solid #ddd'},toolbar_area:{padding:'3px 0px',display:'none',borderBottom:'1px solid #ddd'}}
function PageHeader(parent,main_text,sub_text){this.wrapper=$a(parent,'div','page_header');this.close_btn=$a(this.wrapper,'a','close',{},'&times;');this.close_btn.onclick=function(){window.history.back();};this.breadcrumbs=$a(this.wrapper,'div','breadcrumbs-area');this.main_head=$a(this.wrapper,'h1','',def_ph_style.main_heading);this.sub_head=$a(this.wrapper,'h4','',def_ph_style.sub_heading);this.separator=$a(this.wrapper,'div','',def_ph_style.separator);this.toolbar_area=$a(this.wrapper,'div','',def_ph_style.toolbar_area);this.padding_area=$a(this.wrapper,'div','',{padding:'3px'});if(main_text)this.main_head.innerHTML=main_text;if(sub_text)this.sub_head.innerHTML=sub_text;this.buttons={};this.buttons2={};}
PageHeader.prototype.add_button=function(label,fn,bold,icon,green){var tb=this.toolbar_area;if(this.buttons[label])return;iconhtml=icon?('<i class="'+icon+'"></i> '):'';var $button=$('<button class="btn btn-small">'+iconhtml+label+'</button>').click(fn).appendTo(tb);if(green){$button.addClass('btn-info');$button.find('i').addClass('icon-white');}
if(bold)$button.css('font-weight','bold');this.buttons[label]=$button.get(0);$ds(this.toolbar_area);return this.buttons[label];}
PageHeader.prototype.clear_toolbar=function(){this.toolbar_area.innerHTML='';this.buttons={};}
PageHeader.prototype.make_buttonset=function(){$(this.toolbar_area).buttonset();}
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
var load_doc=loaddoc;function new_doc(doctype,in_form){doctype=get_label_doctype(doctype);wn.model.with_doctype(doctype,function(){if(!in_form&&locals.DocType[doctype].in_dialog){var new_name=LocalDB.create(doctype);_f.edit_record(doctype,new_name);}else{wn.views.formview.create(doctype);}})}
var newdoc=new_doc;var pscript={};function loadpage(page_name,call_back,no_history){wn.set_route(page_name);}
function loaddocbrowser(dt){wn.set_route('List',dt);}
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
 *	conf.js
 */
wn.provide('erpnext');erpnext.set_about=function(){wn.provide('wn.app');$.extend(wn.app,{name:'ERPNext',license:'GNU/GPL - Usage Condition: All "erpnext" branding must be kept as it is',source:'https://github.com/webnotes/erpnext',publisher:'Web Notes Technologies Pvt Ltd, Mumbai',copyright:'&copy; Web Notes Technologies Pvt Ltd',version:'2'});}
wn.modules_path='erpnext';$(document).bind('toolbar_setup',function(){$('.brand').html((wn.boot.website_settings.brand_html||'erpnext')+' <i class="icon-home icon-white navbar-icon-home" ></i>').css('max-width','200px').css('overflow','hidden').hover(function(){$(this).find('.icon-home').addClass('navbar-icon-home-hover');},function(){$(this).find('.icon-home').removeClass('navbar-icon-home-hover');});});