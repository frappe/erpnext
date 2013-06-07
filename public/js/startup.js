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
		
		// set interval for updates
		erpnext.startup.set_periodic_updates();

		// complete registration
		if(in_list(user_roles,'System Manager') && (wn.boot.setup_complete=='No')) { 
			wn.require("app/js/complete_setup.js");
			erpnext.complete_setup.show(); 
		}
		if(wn.boot.expires_on && in_list(user_roles, 'System Manager')) {
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


// ========== Update Messages ============
erpnext.update_messages = function(reset) {
	// Updates Team Messages
	
	if(inList(['Guest'], user) || !wn.session_alive) { return; }

	if(!reset) {
		var set_messages = function(r) {
			if(!r.exc) {
				// This function is defined in toolbar.js
				erpnext.toolbar.set_new_comments(r.message.unread_messages);
				
				var show_in_circle = function(parent_id, msg) {
					var parent = $('#'+parent_id);
					if(parent) {
						if(msg) {
							parent.find('span:first').text(msg);
							parent.toggle(true);
						} else {
							parent.toggle(false);
						}
					}
				}
				
				show_in_circle('unread_messages', r.message.unread_messages);
				show_in_circle('open_support_tickets', r.message.open_support_tickets);
				show_in_circle('things_todo', r.message.things_todo);
				show_in_circle('todays_events', r.message.todays_events);
				show_in_circle('open_tasks', r.message.open_tasks);
				show_in_circle('unanswered_questions', r.message.unanswered_questions);
				show_in_circle('open_leads', r.message.open_leads);

			} else {
				clearInterval(wn.updates.id);
			}
		}

		wn.call({
			method: 'startup.startup.get_global_status_messages',
			type:"GET",
			callback: set_messages
		});
	
	} else {
		erpnext.toolbar.set_new_comments(0);
		$('#unread_messages').toggle(false);
	}
}

erpnext.startup.set_periodic_updates = function() {
	// Set interval for periodic updates of team messages
	wn.updates = {};

	if(wn.updates.id) {
		clearInterval(wn.updates.id);
	}

	wn.updates.id = setInterval(erpnext.update_messages, 60000);
}

erpnext.hide_naming_series = function() {
	if(cur_frm.fields_dict.naming_series) {
		cur_frm.toggle_display("naming_series", cur_frm.doc.__islocal?true:false);
	}
}

erpnext.setup_mousetrap = function() {
	Mousetrap.bind(["command+g", "ctrl+g"], function() {
		wn.ui.toolbar.search.show();
		return false;
	});

	Mousetrap.bind(["command+s", "ctrl+s"], function() {
		if(cur_frm && !cur_frm.save_disabled && cint(cur_frm.doc.docstatus)===0)
			cur_frm.save();
		else if(cur_frm && !cur_frm.save_disabled && cint(cur_frm.doc.docstatus)===1
				&& cur_frm.doc.__unsaved)
			cur_frm.frm_head.appframe.buttons['Update'].click();
		else if(wn.container.page.save_action)
			wn.container.page.save_action();
		return false;
	});	
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
