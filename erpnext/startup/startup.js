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
	pscript.is_erpnext_saas = cint(wn.control_panel.sync_with_gateway)
	if(inList(user_roles,'System Manager')) is_system_manager = 1;
}

erpnext.startup.start = function() {
	$('#startup_div').html('Starting up...').toggle(true);
	
	erpnext.startup.set_globals();

	if(wn.boot.custom_css) {
		set_style(wn.boot.custom_css);
	}
		
	if(user == 'Guest'){
		if(wn.boot.website_settings.title_prefix) {
			wn.title_prefix = wn.boot.website_settings.title_prefix;
		}
	} else {
		// setup toolbar
		erpnext.toolbar.setup();
		
		// set interval for updates
		erpnext.startup.set_periodic_updates();

		// border to the body
		// ------------------
		$('footer').html('<div class="web-footer erpnext-footer">\
			Powered by <a href="https://erpnext.com">ERPNext</a></div>');
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


// Module Page
// ====================================================================

ModulePage = function(parent, module_name, module_label, help_page, callback) {
	this.parent = parent;

	// add to current page
	page_body.cur_page.module_page = this;

	this.wrapper = $a(parent,'div');
	this.module_name = module_name;
	this.transactions = [];
	this.page_head = new PageHeader(this.wrapper, module_label);

	if(help_page) {
		var btn = this.page_head.add_button('Help', function() { loadpage(this.help_page) }, 1, 'ui-icon-help')
		btn.help_page = help_page;
	}

	if(callback) this.callback = function(){ callback(); }
}

// ========== Update Messages ============
var update_messages = function() {
	// Updates Team Messages
	
	if(inList(['Guest'], user)) { return; }
	
	$c_page('home', 'event_updates', 'get_unread_messages', null,
		function(r,rt) {
			if(!r.exc) {
				// This function is defined in toolbar.js
				page_body.wntoolbar.set_new_comments(r.message);
				var circle = $('#msg_count')
				if(circle) {
					if(r.message.length) {
						circle.find('span:first').text(r.message.length);
						circle.toggle(true);
					} else {
						circle.toggle(false);
					}
				}
			} else {
				clearInterval(wn.updates.id);
			}
		}
	);
}

erpnext.startup.set_periodic_updates = function() {
	// Set interval for periodic updates of team messages
	wn.updates = {};

	if(wn.updates.id) {
		clearInterval(wn.updates.id);
	}

	wn.updates.id = setInterval(update_messages, 60000);
}

// =======================================

// start
$(document).bind('startup', function() {
	erpnext.startup.start();
});
