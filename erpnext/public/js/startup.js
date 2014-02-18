// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

var current_module;

frappe.provide('erpnext.startup');

erpnext.startup.start = function() {
	console.log(frappe._('Starting up...'));
	$('#startup_div').html('Starting up...').toggle(true);
	
	erpnext.toolbar.setup();
	
	if(frappe.boot.expires_on && in_list(user_roles, 'System Manager')) {
		erpnext.startup.show_expiry_banner();
	}
}

erpnext.startup.show_expiry_banner = function() {
	var today = dateutil.str_to_obj(frappe.boot.server_date);
	var expires_on = dateutil.str_to_obj(frappe.boot.expires_on);
	var diff = dateutil.get_diff(expires_on, today);
	var payment_link = "<a href=\"https://erpnext.com/modes-of-payment.html\" target=\"_blank\">"+
		frappe._("Click here to buy subscription.")+"</a>";
	
	var msg = "";
	if (0 <= diff && diff <= 10) {
		var expiry_string = diff==0 ? "today" : repl("in %(diff)s day(s)", { diff: diff });
		msg = repl(frappe._('Your ERPNext subscription will')+' <b>expire %(expiry_string)s</b>. %(payment_link)s',
			{ expiry_string: expiry_string, payment_link: payment_link });
	} else if (diff < 0) {
		msg = repl(frappe._('This ERPNext subscription')+'<b>'+frappe._('has expired')+'</b>. %(payment_link)s', {payment_link: payment_link});
	}
	
	if(msg) frappe.ui.toolbar.show_banner(msg);
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
