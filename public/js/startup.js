// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

var current_module;
var is_system_manager = 0;

wn.provide('erpnext.startup');

erpnext.startup.set_globals = function() {
	if(inList(user_roles,'System Manager')) is_system_manager = 1;
}

erpnext.startup.start = function() {
	console.log('Starting up...');
	$('#startup_div').html('Starting up...').toggle(true);
	
	erpnext.startup.set_globals();

	if(user != 'Guest'){
		erpnext.setup_mousetrap();
				
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
		erpnext.set_about();
		if(wn.control_panel.custom_startup_code)
			eval(wn.control_panel.custom_startup_code);		
	}
}

erpnext.hide_naming_series = function() {
	if(cur_frm.fields_dict.naming_series) {
		cur_frm.toggle_display("naming_series", cur_frm.doc.__islocal?true:false);
	}
}

erpnext.setup_mousetrap = function() {
	$(document).keydown("meta+g ctrl+g", function(e) {
		wn.ui.toolbar.search.show();
		return false;
	});
	
	$(document).keydown("meta+s ctrl+s", function(e) {
		if(cur_frm) {
			cur_frm.save_or_update();
		}
		else if(wn.container.page.save_action)
			wn.container.page.save_action();
		return false;
	})
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
