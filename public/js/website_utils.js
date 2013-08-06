// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt


var erpnext = {};
var wn = {};

// Add / update a new Lead / Communication
// subject, sender, description
erpnext.send_message = function(opts) {
	return wn.call({
		type: "POST",
		method: "website.helpers.contact.send_message",
		args: opts,
		callback: opts.callback
	});
}

wn.call = function(opts) {
	if(opts.btn) {
		$(opts.btn).attr("disabled", "disabled");
	}
	
	if(opts.msg) {
		$(opts.msg).toggle(false);
	}
	
	if(!opts.args) opts.args = {};
	
	// get or post?
	if(!opts.args._type) {
		opts.args._type = opts.type || "GET";
	}

	// method
	if(opts.method) {
		opts.args.cmd = opts.method;
	}

	// stringify
	$.each(opts.args, function(key, val) {
		if(typeof val != "string") {
			opts.args[key] = JSON.stringify(val);
		}
	});
	
	$.ajax({
		type: "POST",
		url: "server.py",
		data: opts.args,
		dataType: "json",
		success: function(data) {
			if(opts.btn) {
				$(opts.btn).attr("disabled", false);
			}
			if(data.exc) {
				if(opts.btn) {
					$(opts.btn).addClass("btn-danger");
					setTimeout(function() { $(opts.btn).removeClass("btn-danger"); }, 1000);
				}
				try {
					var err = JSON.parse(data.exc);
					if($.isArray(err)) {
						err = err.join("\n");
					}
					console.error ? console.error(err) : console.log(err);
				} catch(e) {
					console.log(data.exc);
				}
			} else{
				if(opts.btn) {
					$(opts.btn).addClass("btn-success");
					setTimeout(function() { $(opts.btn).removeClass("btn-success"); }, 1000);
				}
			}
			if(opts.msg && data.message) {
				$(opts.msg).html(data.message).toggle(true);
			}
			if(opts.callback)
				opts.callback(data);
		},
		error: function(response) {
			console.error ? console.error(response) : console.log(response);
		}
	});
	
	return false;
}

// Setup the user tools
//
$(document).ready(function() {
	// update login
	var full_name = getCookie("full_name");
	if(full_name) {
		$("#user-tools").addClass("hide");
		$("#user-tools-post-login").removeClass("hide");
		$("#user-full-name").text(full_name);
	}
	
	wn.cart.set_cart_count();
	
	$("#user-tools a").tooltip({"placement":"bottom"});
	$("#user-tools-post-login a").tooltip({"placement":"bottom"});
});

// Utility functions

function valid_email(id) { 
	if(id.toLowerCase().search("[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")==-1) 
		return 0; else return 1; }

var validate_email = valid_email;

function get_url_arg(name) {
	name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
	var regexS = "[\\?&]"+name+"=([^&#]*)";
	var regex = new RegExp( regexS );
	var results = regex.exec( window.location.href );
	if(results == null)
		return "";
	else
		return decodeURIComponent(results[1]);		
}

function make_query_string(obj) {
	var query_params = [];
	$.each(obj, function(k, v) { query_params.push(encodeURIComponent(k) + "=" + encodeURIComponent(v)); });
	return "?" + query_params.join("&");
}

function repl(s, dict) {
	if(s==null)return '';
	for(key in dict) {
		s = s.split("%("+key+")s").join(dict[key]);
	}
	return s;
}

function replace_all(s, t1, t2) {
	return s.split(t1).join(t2);
}

function getCookie(name) {
	return getCookies()[name];
}

function getCookies() {
	var c = document.cookie, v = 0, cookies = {};
	if (document.cookie.match(/^\s*\$Version=(?:"1"|1);\s*(.*)/)) {
		c = RegExp.$1;
		v = 1;
	}
	if (v === 0) {
		c.split(/[,;]/).map(function(cookie) {
			var parts = cookie.split(/=/, 2),
				name = decodeURIComponent(parts[0].trimLeft()),
				value = parts.length > 1 ? decodeURIComponent(parts[1].trimRight()) : null;
			if(value && value.charAt(0)==='"') {
				value = value.substr(1, value.length-2);
			}
			cookies[name] = value;
		});
	} else {
		c.match(/(?:^|\s+)([!#$%&'*+\-.0-9A-Z^`a-z|~]+)=([!#$%&'*+\-.0-9A-Z^`a-z|~]*|"(?:[\x20-\x7E\x80\xFF]|\\[\x00-\x7F])*")(?=\s*[,;]|$)/g).map(function($0, $1) {
			var name = $0,
				value = $1.charAt(0) === '"'
						  ? $1.substr(1, -1).replace(/\\(.)/g, "$1")
						  : $1;
			cookies[name] = value;
		});
	}
	return cookies;
}

if (typeof String.prototype.trimLeft !== "function") {
	String.prototype.trimLeft = function() {
		return this.replace(/^\s+/, "");
	};
}
if (typeof String.prototype.trimRight !== "function") {
	String.prototype.trimRight = function() {
		return this.replace(/\s+$/, "");
	};
}
if (typeof Array.prototype.map !== "function") {
	Array.prototype.map = function(callback, thisArg) {
		for (var i=0, n=this.length, a=[]; i<n; i++) {
			if (i in this) a[i] = callback.call(thisArg, this[i]);
		}
		return a;
	};
}

// shopping cart
if(!wn.cart) wn.cart = {};
var full_name = getCookie("full_name");

$.extend(wn.cart, {
	update_cart: function(opts) {
		if(!full_name) {
			if(localStorage) {
				localStorage.setItem("last_visited", window.location.pathname.slice(1));
				localStorage.setItem("pending_add_to_cart", opts.item_code);
			}
			window.location.href = "login";
		} else {
			return wn.call({
				type: "POST",
				method: "website.helpers.cart.update_cart",
				args: {
					item_code: opts.item_code,
					qty: opts.qty,
					with_doclist: opts.with_doclist
				},
				btn: opts.btn,
				callback: function(r) {
					if(opts.callback)
						opts.callback(r);
					
					wn.cart.set_cart_count();
				}
			});
		}
	},
	
	set_cart_count: function() {
		var cart_count = getCookie("cart_count");
		if(cart_count)
			$(".cart-count").html("( "+ cart_count +" )")
	}
});