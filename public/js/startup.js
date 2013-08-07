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
			var today = dateutil.str_to_obj(wn.boot.server_date);
			var expires_on = dateutil.str_to_obj(wn.boot.expires_on);
			var diff = dateutil.get_diff(expires_on, today);
			var payment_link = "<a href=\"https://erpnext.com/modes-of-payment.html\" target=\"_blank\">See Payment Options.</a>";		
			if (0 <= diff && diff <= 15) {
				var expiry_string = diff==0 ? "today" : repl("in %(diff)s day(s)", { diff: diff });
				$('header').append(repl('<div class="expiry-info"> \
					Your ERPNext subscription will <b>expire %(expiry_string)s</b>. \
					Please renew your subscription to continue using ERPNext \
					(and remove this annoying banner). %(payment_link)s\
				</div>', { expiry_string: expiry_string, payment_link: payment_link }));
			} else if (diff < 0) {
				$('header').append(repl('<div class="expiry-info"> \
					This ERPNext subscription <b>has expired</b>. %(payment_link)s\
				</div>', { expiry_string: expiry_string, payment_link: payment_link }));
			}
		}
	}
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
