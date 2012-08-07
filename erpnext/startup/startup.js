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

erpnext.modules = {
	'Selling': 'selling-home',
	'Accounts': 'accounts-home',
	'Stock': 'stock-home',
	'Buying': 'buying-home',
	'Support': 'support-home',
	'Projects': 'projects-home',
	'Production': 'production-home',
	'Website': 'website-home',
	'HR': 'hr-home',
	'Setup': 'Setup',
	'Activity': 'activity',
	'To Do': 'todo',
	'Calendar': 'calendar',
	'Messages': 'messages',
	'Knowledge Base': 'questions',
	'Dashboard': 'dashboard'
}

// wn.modules is used in breadcrumbs for getting module home page
wn.provide('wn.modules');
$.extend(wn.modules, erpnext.modules);
wn.modules['Core'] = 'Setup';

erpnext.startup.set_globals = function() {
	if(inList(user_roles,'System Manager')) is_system_manager = 1;
}

erpnext.startup.start = function() {
	console.log('Starting up...');
	$('#startup_div').html('Starting up...').toggle(true);
	
	
	erpnext.startup.set_globals();
		
	if(user != 'Guest'){
		if(wn.boot.user_background) {
			erpnext.set_user_background(wn.boot.user_background);
		}

		// always allow apps
		wn.boot.profile.allow_modules = wn.boot.profile.allow_modules.concat(
			['To Do', 'Knowledge Base', 'Calendar', 'Activity', 'Messages'])
		
		// setup toolbar
		erpnext.toolbar.setup();
		
		// set interval for updates
		erpnext.startup.set_periodic_updates();

		// border to the body
		// ------------------
		$('footer').html('<div class="web-footer erpnext-footer">\
			<a href="#!attributions">ERPNext | Attributions and License</a></div>');

		// complete registration
		if(in_list(user_roles,'System Manager') && (wn.boot.setup_complete=='No')) { 
			wn.require("js/complete_setup.js");
			erpnext.complete_setup.show(); 
		}
		if(wn.boot.expires_on && in_list(user_roles, 'System Manager')) {
			var today = dateutil.str_to_obj(dateutil.get_today());
			var expires_on = dateutil.str_to_obj(wn.boot.expires_on);
			var diff = dateutil.get_diff(expires_on, today);
			if (0 <= diff && diff <= 15) {
				var expiry_string = diff==0 ? "today" : repl("in %(diff)s day(s)", { diff: diff });
				$('header').append(repl('<div class="expiry-info"> \
					Your ERPNext subscription will <b>expire %(expiry_string)s</b>. \
					Please renew your subscription to continue using ERPNext \
					(and remove this annoying banner). \
				</div>', { expiry_string: expiry_string }));
			} else if (diff < 0) {
				$('header').append(repl('<div class="expiry-info"> \
					This ERPNext subscription <b>has expired</b>. \
				</div>', { expiry_string: expiry_string }));
			}
		}
		erpnext.set_about();
		if(wn.control_panel.custom_startup_code)
			eval(wn.control_panel.custom_startup_code);		
	}

		
	$('body').append('<a class="erpnext-logo" title="Powered by ERPNext" \
		href="http://erpnext.com" target="_blank"></a>')
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
				
				show_in_circle('unread_messages', r.message.unread_messages.length);
				show_in_circle('open_support_tickets', r.message.open_support_tickets);
				show_in_circle('things_todo', r.message.things_todo);
				show_in_circle('todays_events', r.message.todays_events);
				show_in_circle('open_tasks', r.message.open_tasks);
				show_in_circle('unanswered_questions', r.message.unanswered_questions);

			} else {
				clearInterval(wn.updates.id);
			}
		}

		wn.call({
			method: 'startup.startup.get_global_status_messages',
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

erpnext.set_user_background = function(src) {
	set_style(repl('#body_div { background: url("files/%(src)s") repeat;}', {src:src}))
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});

// subject, sender, description
erpnext.send_message = function(opts) {
	if(opts.btn) {
		$(opts.btn).start_working();
	}
	wn.call({
		method: 'website.send_message',
		args: opts,
		callback: function(r) { 
			if(opts.btn) {
				$(opts.btn).done_working();
			}
			if(opts.callback)opts.callback(r) 
		}
	});
}

erpnext.hide_naming_series = function() {
	if(cur_frm.fields_dict.naming_series) {
		hide_field('naming_series');
		if(cur_frm.doc.__islocal) {
			unhide_field('naming_series');
		}
	}
}
