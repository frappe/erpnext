var current_module;
var is_system_manager = 0;
var module_content_dict = {};
var user_full_nm = {};

wn.provide('erpnext.startup');

erpnext.startup.set_globals = function() {
	pscript.is_erpnext_saas = cint(wn.control_panel.sync_with_gateway)
	if(inList(user_roles,'System Manager')) is_system_manager = 1;
}

erpnext.startup.start = function() {
	$('#startup_div').html('Starting up...').toggle(true);
	
	erpnext.startup.set_globals();
	
	if(user == 'Guest'){
		$dh(page_body.left_sidebar);
		wn.require('erpnext/website/css/website.css');
		wn.require('erpnext/website/js/topbar.js');
		if(wn.boot.custom_css) {
			set_style(wn.boot.custom_css);
		}
		if(wn.boot.website_settings.title_prefix) {
			wn.title_prefix = wn.boot.website_settings.title_prefix;
		}
	} else {
		// modules
		wn.require('erpnext/startup/modules.js');
		pscript.startup_make_sidebar();

		// setup toolbar
		wn.require('erpnext/startup/toolbar.js');
		erpnext.toolbar.setup();
		wn.require('erpnext/startup/feature_setup.js');

		// border to the body
		// ------------------
		$('footer').html('<div class="erpnext-footer">\
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

// start
erpnext.startup.start();