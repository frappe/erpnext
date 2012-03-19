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

erpnext.startup.set_globals = function() {
	pscript.is_erpnext_saas = cint(wn.control_panel.sync_with_gateway)
	if(inList(user_roles,'System Manager')) is_system_manager = 1;
}

erpnext.startup.start = function() {
	$('#startup_div').html('Starting up...').toggle(true);
	
	
	erpnext.startup.set_globals();

	if(wn.boot.custom_css) {
		set_style(wn.boot.custom_css);
	}
	if(wn.boot.user_background) {
		erpnext.set_user_background(wn.boot.user_background);
	}
		
	if(user == 'Guest'){
		if(wn.boot.website_settings.title_prefix) {
			wn.title_prefix = wn.boot.website_settings.title_prefix;
		}
	} else {
		// always allow apps
		wn.boot.profile.allow_modules = wn.boot.profile.allow_modules.concat(
			['To Do', 'Knowledge Base', 'Calendar', 'Activity', 'Messages'])
		
		// setup toolbar
		erpnext.toolbar.setup();
				
		// set interval for updates
		erpnext.startup.set_periodic_updates();

		// border to the body
		// ------------------
		//$('footer').html('<div class="web-footer erpnext-footer">\
		//	<a href="#!attributions">ERPNext | Attributions and License</a></div>');

		// complete registration
		if(in_list(user_roles,'System Manager') && (wn.boot.setup_complete=='No')) { 
			wn.require("erpnext/startup/js/complete_setup.js");
			erpnext.complete_setup(); 
		}

	}

	$('#startup_div').toggle(false);
}

// chart of accounts
// ====================================================================
show_chart_browser = function(nm, chart_type){

  var call_back = function(){
    if(nm == 'Sales Browser'){
      var sb_obj = new SalesBrowser();
      sb_obj.set_val(chart_type);
    }
    else if(nm == 'Accounts Browser')
      pscript.make_chart(chart_type);
  }
  loadpage(nm,call_back);
}


// ========== Update Messages ============
var update_messages = function(reset) {
	// Updates Team Messages
	
	if(inList(['Guest'], user) || !wn.session_alive) { return; }

	if(!reset) {
		$c_page('home', 'event_updates', 'get_global_status_messages', null,
			function(r,rt) {
				if(!r.exc) {
					// This function is defined in toolbar.js
					wn.container.wntoolbar.set_new_comments(r.message.unread_messages);
					
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

				} else {
					clearInterval(wn.updates.id);
				}
			}
		);
	} else {
		wn.container.wntoolbar.set_new_comments(0);
		$('#unread_messages').toggle(false);
	}
}

erpnext.startup.set_periodic_updates = function() {
	// Set interval for periodic updates of team messages
	wn.updates = {};

	if(wn.updates.id) {
		clearInterval(wn.updates.id);
	}

	wn.updates.id = setInterval(update_messages, 60000);
}

erpnext.set_user_background = function(src) {
	set_style(repl('body { background: url("files/%(src)s") repeat;}', {src:src}))
}

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
