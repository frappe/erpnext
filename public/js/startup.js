// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

var current_module;

wn.provide('erpnext.startup');

erpnext.startup.start = function() {
	console.log(wn._('Starting up...'));
	$('#startup_div').html('Starting up...').toggle(true);
	
	erpnext.toolbar.setup();
	
	if(wn.boot.expires_on && in_list(user_roles, 'System Manager')) {
		erpnext.startup.show_expiry_banner();
	}
}

erpnext.startup.show_expiry_banner = function() {
	var today = dateutil.str_to_obj(wn.boot.server_date);
	var expires_on = dateutil.str_to_obj(wn.boot.expires_on);
	var diff = dateutil.get_diff(expires_on, today);
	var payment_link = "<a href=\"https://erpnext.com/modes-of-payment.html\" target=\"_blank\">"+
		wn._("Click here to buy subscription.")+"</a>";
	
	var msg = "";
	if (0 <= diff && diff <= 10) {
		var expiry_string = diff==0 ? "today" : repl("in %(diff)s day(s)", { diff: diff });
		msg = repl(wn._('Your ERPNext subscription will')+'<b>expire %(expiry_string)s</b>. %(payment_link)s',
			{ expiry_string: expiry_string, payment_link: payment_link });
	} else if (diff < 0) {
		msg = repl(wn._('This ERPNext subscription')+'<b>'+wn._('has expired')+'</b>. %(payment_link)s', {payment_link: payment_link});
	}
	
	if(msg) wn.ui.toolbar.show_banner(msg);
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
