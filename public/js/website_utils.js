
var erpnext = {};
var wn = {};

// Add / update a new Lead / Communication
// subject, sender, description
erpnext.send_message = function(opts) {
	wn.call({
		type: "POST",
		method: "website.helpers.contact.send_message",
		args: opts,
		callback: opts.callback
	})
}

wn.call = function(opts) {
	if(opts.btn) {
		var $spinner = $('<img src="lib/images/ui/button-load.gif">').appendTo($(opts.btn).parent())
		$(opts.btn).attr("disabled", "disabled");
	}
	
	if(opts.msg) {
		$(opts.msg).toggle(false);
	}
	
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
				$spinner.remove();
			}
			if(data.exc) {
				console.log(data.exc);
			}
			if(opts.msg && data.message) {
				$(opts.msg).html(data.message).toggle(true);
			}
			if(opts.callback)
				opts.callback(data);
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
		$("#user-tools").html(repl('<a href="profile" title="My Profile" id="user-full-name">%(full_name)s</a> | \
			<a href="account" title="My Account">My Account</a> | \
			<!--<a href="cart" title="Shopping Cart"><i class="icon-shopping-cart"></i> (%(count)s)</a> | -->\
			<a href="server.py?cmd=web_logout" title="Sign Out"><i class="icon-signout"></i></a>', {
			full_name: full_name,
			count: getCookie("cart_count") || "0"
		}));
		$("#user-tools a").tooltip({"placement":"bottom"});
	}
})

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
			if(value.charAt(0)==='"') {
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
