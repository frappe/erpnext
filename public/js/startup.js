// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

var current_module;

wn.provide('erpnext.startup');

erpnext.startup.start = function() {
	console.log('Starting up...');
	$('#startup_div').html('Starting up...').toggle(true);
	
	if(user != 'Guest'){
		// setup toolbar
		erpnext.toolbar.setup();
		
		// complete registration
		if(in_list(user_roles,'System Manager') && (wn.boot.setup_complete==='No')) { 
			wn.require("app/js/complete_setup.js");
			erpnext.complete_setup.show(); 
		} else if(!wn.boot.customer_count) {
			if(wn.get_route()[0]!=="Setup") {
				msgprint("<a class='btn btn-success' href='#Setup'>" 
					+ wn._("Proceed to Setup") + "</a>\
					<br><br><p class='text-muted'>"+
					wn._("This message goes away after you create your first customer.")+
					"</p>", wn._("Welcome"));
			}
		} else if(wn.boot.expires_on && in_list(user_roles, 'System Manager')) {
			erpnext.startup.show_expiry_banner();
		}
	}
}

erpnext.startup.show_expiry_banner = function() {
	var today = dateutil.str_to_obj(wn.boot.server_date);
	var expires_on = dateutil.str_to_obj(wn.boot.expires_on);
	var diff = dateutil.get_diff(expires_on, today);
	var payment_link = "<a href=\"https://erpnext.com/modes-of-payment.html\" target=\"_blank\">\
		Click here to buy subscription.</a>";
	
	var msg = "";
	if (0 <= diff && diff <= 10) {
		var expiry_string = diff==0 ? "today" : repl("in %(diff)s day(s)", { diff: diff });
		msg = repl('Your ERPNext subscription will <b>expire %(expiry_string)s</b>. %(payment_link)s',
			{ expiry_string: expiry_string, payment_link: payment_link });
	} else if (diff < 0) {
		msg = repl('This ERPNext subscription <b>has expired</b>. %(payment_link)s', {payment_link: payment_link});
	}
	
	if(msg) wn.ui.toolbar.show_banner(msg);
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
