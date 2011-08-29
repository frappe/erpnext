if(user == 'Guest'){
  $dh(page_body.left_sidebar);
}

var current_module;
var is_system_manager = 0;
var module_content_dict = {};
var user_full_nm = {};

// check if session user is system manager
if(inList(user_roles,'System Manager')) is_system_manager = 1;

function startup_setup() {
	pscript.is_erpnext_saas = cint(locals['Control Panel']['Control Panel'].sync_with_gateway)


	if(get_url_arg('embed')) {
		// hide header, footer
		$dh(page_body.banner_area);
		$dh(page_body.wntoolbar);
		$dh(page_body.footer);
		return;
	}

	if(user=='Guest' && !get_url_arg('akey')) {
		if(pscript.is_erpnext_saas) {
			window.location.href = 'https://www.erpnext.com';
			return;
		}
	}

	// page structure
	// --------------
	$td(page_body.wntoolbar.body_tab,0,0).innerHTML = '<i><b>erp</b>next</i>';
	$y($td(page_body.wntoolbar.body_tab,0,0), {width:'140px', color:'#FFF', paddingLeft:'8px', paddingRight:'8px', fontSize:'14px'})
	$dh(page_body.banner_area);

	// sidebar
	// -------
	pscript.startup_make_sidebar();

	// border to the body
	// ------------------
	$dh(page_body.footer);

	// for logout and payment
	var callback = function(r,rt) {
		if(r.message){
			login_file = 'http://' + r.message;
		}
		else if(pscript.is_erpnext_saas) {
			login_file = 'http://www.erpnext.com';
		}
		// setup toolbar
		pscript.startup_setup_toolbar();
	}
	$c_obj('Home Control', 'get_login_url', '', callback);
}

// ====================================================================

pscript.startup_make_sidebar = function() {
	$y(page_body.left_sidebar, {width:(100/6)+'%', paddingTop:'8px'});

	var callback = function(r,rt) {
		// menu
		var ml = r.message;

		// clear
		page_body.left_sidebar.innerHTML = '';

		for(var m=0; m<ml.length; m++){
			if(ml[m]) {
				new SidebarItem(ml[m]);
			}
		}
		if(in_list(user_roles, 'System Manager')) {
			var div = $a(page_body.left_sidebar, 'div', 'link_type', {padding:'8px', fontSize:'11px'});
			$(div).html('[edit]').click(pscript.startup_set_module_order)
		}
		nav_obj.observers.push({notify:function(t,dt,dn) { pscript.select_sidebar_menu(t, dt, dn); }});

		// select current
		var no = nav_obj.ol[nav_obj.ol.length-1];
		if(no && menu_item_map[decodeURIComponent(no[0])][decodeURIComponent(no[1])])
			pscript.select_sidebar_menu(decodeURIComponent(no[0]), decodeURIComponent(no[1]));
	}
	$c_obj('Home Control', 'get_modules', '', callback);
}

// ====================================================================
// Menu observer
// ====================================================================

cur_menu_pointer = null;
var menu_item_map = {'Form':{}, 'Page':{}, 'Report':{}, 'List':{}}

pscript.select_sidebar_menu = function(t, dt, dn) {
	// get menu item
	if(menu_item_map[t][dt]) {
		// select
		menu_item_map[t][dt].select();
	} else {
		// none found :-( Unselect
		if(cur_menu_pointer)
			cur_menu_pointer.deselect();
	}
}

// ====================================================================
// Menu pointer
// ====================================================================

var body_background = '#e2e2e2';

MenuPointer = function(parent, label) {

	this.wrapper = $a(parent, 'div', '', {padding:'0px', cursor:'pointer', margin:'2px 0px'});
	$br(this.wrapper, '3px');

	this.tab = make_table($a(this.wrapper, 'div'), 1, 2, '100%', ['', '11px'], {height:'22px',
		verticalAlign:'middle', padding:'0px'}, {borderCollapse:'collapse', tableLayout:'fixed'});

	$y($td(this.tab, 0, 0), {padding:'0px 4px', color:'#444', whiteSpace:'nowrap'});

	// triangle border (?)
	this.tab.triangle_div = $a($td(this.tab, 0, 1), 'div','', {
		borderColor: body_background + ' ' + body_background + ' ' + body_background + ' ' + 'transparent',
		borderWidth:'11px', borderStyle:'solid', height:'0px', width:'0px', marginRight:'-11px'});

	this.label_area = $a($td(this.tab, 0, 0), 'span', '', '', label);

	$(this.wrapper)
		.hover(
			function() { if(!this.selected)$bg(this, '#eee'); } ,
			function() { if(!this.selected)$bg(this, body_background); }
		)

	$y($td(this.tab, 0, 0), {borderBottom:'1px solid #ddd'});

}

// ====================================================================

MenuPointer.prototype.select = function(grey) {
	$y($td(this.tab, 0, 0), {color:'#fff', borderBottom:'0px solid #000'});
	//$gr(this.wrapper, '#F84', '#F63');
	$gr(this.wrapper, '#888', '#666');
	this.selected = 1;

	if(cur_menu_pointer && cur_menu_pointer != this)
		cur_menu_pointer.deselect();

	cur_menu_pointer = this;
}

// ====================================================================

MenuPointer.prototype.deselect = function() {
	$y($td(this.tab, 0, 0), {color:'#444', borderBottom:'1px solid #ddd'});
	$gr(this.wrapper, body_background, body_background);
	this.selected = 0;
}


// ====================================================================
// Sidebar Item
// ====================================================================

var cur_sidebar_item = null;

SidebarItem = function(det) {
	var me = this;
	this.det = det;
	this.wrapper = $a(page_body.left_sidebar, 'div', '', {marginRight:'12px'});

	this.body = $a(this.wrapper, 'div');
	this.tab = make_table(this.body, 1, 2, '100%', ['24px', null], {verticalAlign:'middle'}, {tableLayout:'fixed'});

	// icon
	var ic = $a($td(this.tab, 0, 0), 'div', 'module-icons module-icons-' + det.module_label.toLowerCase(), {marginLeft:'3px', marginBottom:'-2px'});

	// pointer table
	this.pointer = new MenuPointer($td(this.tab, 0, 1), det.module_label);
	$y($td(this.pointer.tab, 0, 0), {fontWeight:'bold'});

	// for page type
	if(det.module_page) {
		menu_item_map.Page[det.module_page] = this.pointer;
	}

	// items area
	this.items_area = $a(this.wrapper, 'div');

	this.body.onclick = function() { me.onclick(); }
}

// ====================================================================

SidebarItem.prototype.onclick = function() {
	var me = this;

	if(this.det.module_page) {
		// page type
		this.pointer.select();

		$item_set_working(me.pointer.label_area);
		loadpage(this.det.module_page, function() { $item_done_working(me.pointer.label_area); });

	} else {
		// show sub items
		this.toggle();
	}
}

// ====================================================================

SidebarItem.prototype.collapse = function() {
	$(this.items_area).slideUp();
	this.is_open = 0;
	$fg(this.pointer.label_area, '#444')
}

// ====================================================================

SidebarItem.prototype.toggle = function() {
	if(this.loading) return;

	if(this.is_open) {
		this.collapse();
	} else {
		if(this.loaded) $(this.items_area).slideDown();
		else this.show_items();
		this.is_open = 1;
		$fg(this.pointer.label_area, '#000')
		//this.pointer.select(1);

		// close existing open
		if(cur_sidebar_item && cur_sidebar_item != this) {
			cur_sidebar_item.collapse();
		}
		cur_sidebar_item = this;
	}
}

// ====================================================================

SidebarItem.prototype.show_items = function() {
	this.loading = 1;
	var me = this;

	$item_set_working(this.pointer.label_area);
	var callback = function(r,rt){
		me.loaded = 1;
		me.loading = 0;
		var smi = null;
		var has_reports = 0;
		var has_tools = 0;

		// widget code
		$item_done_working(me.pointer.label_area);

		if(r.message.il) {
			me.il = r.message.il;

			// forms
			for(var i=0; i<me.il.length;i++){
				if(me.il[i].doc_type == 'Forms') {
					if(in_list(profile.can_read, me.il[i].doc_name)) {
						var smi = new SidebarModuleItem(me, me.il[i]);

						menu_item_map['Form'][me.il[i].doc_name] = smi.pointer;
						menu_item_map['List'][me.il[i].doc_name] = smi.pointer;
					}
				}
				if(me.il[i].doc_type=='Reports') has_reports = 1;
				if(in_list(['Single DocType', 'Pages', 'Setup Forms'], me.il[i].doc_type)) has_tools = 1;
			}
			// reports
			if(has_reports) {
				var smi = new SidebarModuleItem(me, {doc_name:'Reports', doc_type:'Reports'});

				// add to menu-item mapper
				menu_item_map['Page'][me.det.module_label + ' Reports'] = smi.pointer;
			}

			// tools
			if(has_tools) {
				var smi = new SidebarModuleItem(me, {doc_name:'Tools', doc_type:'Tools'});

				// add to menu-item mapper
				menu_item_map['Page'][me.det.module_label + ' Tools'] = smi.pointer;
			}

			// custom reports
			if(r.message.custom_reports.length) {
				me.il = add_lists(r.message.il, r.message.custom_reports);
				var smi = new SidebarModuleItem(me, {doc_name:'Custom Reports', doc_type:'Custom Reports'});

				// add to menu-item mapper
				menu_item_map['Page'][me.det.module_label + ' Custom Reports'] = smi.pointer;

			}

		}
		$(me.items_area).slideDown();

		// high light
		var no = nav_obj.ol[nav_obj.ol.length-1];
		if(no && menu_item_map[decodeURIComponent(no[0])][decodeURIComponent(no[1])])
			pscript.select_sidebar_menu(decodeURIComponent(no[0]), decodeURIComponent(no[1]));

	}

	$c_obj('Home Control', 'get_module_details', me.det.name, callback);
}

// ====================================================================
// Show Reports
// ====================================================================

SidebarItem.prototype.show_section = function(sec_type) {
	var me = this;
	var label = this.det.module_label + ' ' + sec_type;
	var type_map = {'Reports':'Reports', 'Custom Reports':'Custom Reports', 'Pages':'Tools', 'Single DocType':'Tools', 'Setup Forms':'Tools'}

	if(page_body.pages[label]) {
		loadpage(label, null, 1);
	} else {
		// make the reports page
		var page = page_body.add_page(label);
		this.wrapper = $a(page,'div','layout_wrapper');


		// head
		this.head = new PageHeader(this.wrapper, label);

		// body
		this.body1 = $a(this.wrapper, 'div', '', {marginTop:'16px'});

		// add a report link
		var add_link = function(det) {
			var div = $a(me.body1, 'div', '', {marginBottom:'6px'});
			var span = $a(div, 'span', 'link_type');

			// tag the span
			span.innerHTML = det.display_name; span.det = det;
			if(sec_type=='Reports' || sec_type=='Custom Reports') {
				// Reports
				// -------
				span.onclick = function() { loadreport(this.det.doc_name, this.det.display_name); }

			} else {
				// Tools
				// -----

				if(det.doc_type=='Pages') {
					// Page
					if(det.click_function) {
						span.onclick = function() { eval(this.det.click_function) }
						span.click_function = det.click_function;
					} else {
						span.onclick = function() { loadpage(this.det.doc_name); }
					}
				} else if(det.doc_type=='Setup Forms') {
					// Doc Browser
					span.onclick = function() { loaddocbrowser(this.det.doc_name); }
				} else {
					// Single
					span.onclick = function() { loaddoc(this.det.doc_name, this.det.doc_name); }
				}
			}
		}

		// item list
		for(var i=0; i<me.il.length;i++){
			if(type_map[me.il[i].doc_type] == sec_type) {
				add_link(me.il[i]);
			}
		}
		loadpage(label, null, 1);
	}
}


// ====================================================================
// Sidebar module item
// ====================================================================

SidebarModuleItem = function(si, det) {
	this.det = det;
	var me= this;

	this.pointer = new MenuPointer(si.items_area, get_doctype_label(det.doc_name));
	$y(si.items_area, {marginLeft:'32px'})
	$y($td(this.pointer.tab, 0, 0), {fontSize:'11px'});

	this.pointer.wrapper.onclick = function() {
		if(me.det.doc_type=='Forms')
			loaddocbrowser(det.doc_name);
		else
			si.show_section(me.det.doc_type);
	}
}


// ====================================================================
// Drag & Drop order selection
// ====================================================================

pscript.startup_set_module_order = function() {
	var update_order= function(ml) {
		mdict = {};
		for(var i=0; i<ml.length; i++) {
			mdict[ml[i][3][3]] = {'module_seq':ml[i][1], 'is_hidden':(ml[i][2] ? 'No' : 'Yes')}
		}
		$c_obj('Home Control', 'set_module_order', JSON.stringify(mdict), function(r,rt) { pscript.startup_make_sidebar(); } )
	}

	var callback = function(r, rt) {
		var ml = [];
		for(var i=0; i<r.message.length; i++) {
			var det = r.message[i];
			ml.push([det[1], det[2], (det[3]!='No' ? 0 : 1), det[0]]);
		}
		new ListSelector('Set Module Sequence', 'Select items and set the order you want them to appear'+
			'<br><b>Note:</b> <i>These changes will apply to all users!</i>', ml, update_order, 1);
	}
	$c_obj('Home Control', 'get_module_order', '', callback)

}

// ====================================================================

pscript.startup_setup_toolbar = function() {
  var menu_tab = page_body.wntoolbar.menu_table_right;
	// Profile
  // ---------
  $td(menu_tab,0,0).innerHTML = '<a style="font-weight: bold; color: #FFF" href="javascript:'+"loadpage('profile-settings')"+'">'+user_fullname+'</a>';

	if(pscript.is_erpnext_saas){
		// Help
  	// --------------
		//var help_url = login_file + '#!helpdesk'
		$td(menu_tab,0,1).innerHTML = '<a style="font-weight: bold; color: #FFF" href="http://groups.google.com/group/erpnext-user-forum" target="_blank">Forum</a>';

		// Manage account
		// --------------
		if(is_system_manager) {
			$td(menu_tab,0,3).innerHTML = '<a style="font-weight: bold; color: #FFF;" href="#!billing">Billing</a>';
		}
	}
	else{
		$dh($td(menu_tab,0,1));
		$dh($td(menu_tab,0,3));
	}

	// Live Chat Help
	// --------------
	$td(menu_tab,0,2).innerHTML = '<a style="font-weight: bold; color: #FFF" href="http://www.providesupport.com?messenger=iwebnotes" target="_blank">Chat</a>';

	// help
	// ----
	var cell = menu_tab.rows[0].insertCell(3);
	cell.innerHTML = '<a style="font-weight: bold; color: #FFF" href="http://erpnext.blogspot.com/2011/03/erpnext-help.html" target="_blank">Help</a>';
	$y(cell, page_body.wntoolbar.right_table_style);

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


// get plural
// ====================================================================

get_plural = function(str){
	if(str.charAt(str.length-1).toLowerCase() == 'y')	return str.substr(0, str.length-1) + 'ies'
	else return str + 's';
}

// set user fullname
// ====================================================================
pscript.set_user_fullname = function(ele,username,get_latest){

	var set_it = function(){
		if(ele)
			ele.innerHTML = user_full_nm[username];
	}

	if(get_latest){
		$c_obj('Home Control','get_user_fullname',username, function(r,rt){ user_full_nm[username] = r.message; set_it(); });
	}
	else{
		if(user_full_nm[username]){
			set_it();
		}

		else
			$c_obj('Home Control','get_user_fullname',username, function(r,rt){ user_full_nm[username] = r.message; set_it(); });
	}
}

// ====================================================================
startup_setup();

/* features setup "Dictionary", "Script"
Dictionary Format
	'projects': {
		'Sales Order': {
			'fields':['project_name'],
			'sales_order_details':['projected_qty']
		},
		'Purchase Order': {
			'fields':['project_name']
		}
	}
// ====================================================================*/
pscript.feature_dict = {
	'projects': {
		'Bill Of Materials': {'fields':['project_name']},
		'Delivery Note': {'fields':['project_name']},
		'Payable Voucher': {'fields':['project_name']},
		'Production Order': {'fields':['project_name']},
		'Purchase Order': {'fields':['project_name']},
		'Purchase Receipt': {'fields':['project_name']},
		'Receivable Voucher': {'fields':['project_name']},
		'Sales Order': {'fields':['project_name']},
		'Stock Entry': {'fields':['project_name']},
		'Timesheet': {'timesheet_details':['project_name']}
	},
	'packing_details': {
		'Delivery Note': {'fields':['packing_details','print_packing_slip'],'delivery_note_details':['no_of_packs','pack_gross_wt','pack_nett_wt','pack_no','pack_unit']},
		'Sales Order': {'fields':['packing_details']}
	},
	'discounts': {
		'Delivery Note': {'delivery_note_details':['adj_rate']},
		'Quotation': {'quotation_details':['adj_rate']},
		'Receivable Voucher': {'rv_details':['adj_rate']},
		'Sales Order': {'sale_order_details':['adj_rate']}
	},
	'brands': {
		'Delivery Note': {'delivery_note_details':['brand']},
		'Enquiry': {'enquiry_details':['brand']},
		'Indent': {'indent_details':['brand']},
		'Item': {'fields':['brand']},
		'Purchase Order': {'po_details':['brand']},
		'Purchase Receipt': {'purchase_receipt_details':['brand']},
		'Payable Voucher': {'pv_details':['brand']},
		'Quotation': {'quotation_details':['brand']},
		'Receivable Voucher': {'rv_details':['brand']},
		'Sales BOM': {'fields':['new_item_brand']},
		'Sales Order': {'sales_order_details':['brand']},
		'Serial No': {'fields':['brand']}
	},
	'after_sale_installations': {
		'Delivery Note': {'fields':['installation_status','per_installed'],'delivery_note_details':['installed_qty']}
	},
	'item_batch_nos': {
		'Delivery Note': {'delivery_note_details':['batch_no']},
		'Item': {'fields':['has_batch_no']},
		'Purchase Receipt': {'purchase_receipt_details':['batch_no']},
		'QA Inspection Report': {'fields':['batch_no']},
		'Sales and Pruchase Return Wizard': {'return_details':['batch_no']},
		'Receivable Voucher': {'rv_details':['batch_no']},
		'Stock Entry': {'stock_entry_details':['batch_no']},
		'Stock Ledger Entry': {'fields':['batch_no']}
	},
	'item_serial_nos': {
		'Customer Issue': {'fields':['serial_no']},
		'Delivery Note': {'delivery_note_details':['serial_no'],'delivery_note_packing_details':['serial_no']},
		'Installation Note': {'installed_item_details':['serial_no']},
		'Item': {'fields':['has_serial_no']},
		'Maintenance Schedule': {'item_maintenance_details':['serial_no'],'maintenance_schedule_details':['serial_no']},
		'Maintenance Visit': {'maintenance_visit_details':['serial_no']},
		'Purchase Receipt': {'purchase_receipt_details':['serial_no']},
		'QA Inspection Report': {'fields':['item_serial_no']},
		'Sales and Pruchase Return Wizard': {'return_details':['serial_no']},
		'Receivable Voucher': {'rv_details':['serial_no']},
		'Stock Entry': {'stock_entry_details':['serial_no']},
		'Stock Ledger Entry': {'fields':['serial_no']}
	},
	'item_groups_in_details': {
		'Delivery Note': {'delivery_note_details':['item_group']},
		'Enquiry': {'enquiry_details':['item_group']},
		'Indent': {'indent_details':['item_group']},
		'Item': {'fields':['item_group']},
		'Manage Account': {'fields':['default_item_group']},
		'Purchase Order': {'po_details':['item_group']},
		'Purchase Receipt': {'purchase_receipt_details':['item_group']},
		'Purchase Voucher': {'pv_details':['item_group']},
		'Quotation': {'quotation_details':['item_group']},
		'Receivable Voucher': {'rv_details':['item_group']},
		'Sales BOM': {'fields':['serial_no']},
		'Sales Order': {'sales_order_details':['item_group']},
		'Serial No': {'fields':['item_group']},
		'Sales Partner': {'partner_target_details':['item_group']},
		'Sales Person': {'target_details':['item_group']},
		'Territory': {'target_details':['item_group']}
	},
	'page_break': {
		'Delivery Note': {'delivery_note_details':['page_break'],'delivery_note_packing_details':['page_break']},
		'Indent': {'indent_details':['page_break']},
		'Purchase Order': {'po_details':['page_break']},
		'Purchase Receipt': {'purchase_receipt_details':['page_break']},
		'Purchase Voucher': {'pv_details':['page_break']},
		'Quotation': {'quotation_details':['page_break']},
		'Receivable Voucher': {'rv_details':['page_break']},
		'Sales Order': {'sales_order_details':['page_break']}
	},
	'multi_currency': {
		'Delivery Note': {'fields':['currency','conversion_rate']},
		'Payable Voucher': {'fields':['currency','conversion_rate']},
		'POS Setting': {'fields':['currency','conversion_rate']},
		'Purchase Order': {'fields':['currency','conversion_rate']},
		'Purchase Receipt': {'fields':['currency','conversion_rate']},
		'Quotation': {'fields':['currency','conversion_rate']},
		'Receivable Voucher': {'fields':['currency','conversion_rate']},
		'Quotation': {'fields':['currency','conversion_rate']},
		'Item': {'ref_rate_details':['currency']},
		'Sales BOM': {'fields':['currency']},
		'Sales Order': {'fields':['currency','conversion_rate']},
		'Supplier Quotation': {'fields':['currency','conversion_rate']}
	},
	'exports': {
		'Delivery Note': {'fields':['currency','conversion_rate','Note','grand_total_export','in_words_export','rounded_total_export'],'delivery_note_details':['base_ref_rate','export_amount','export_rate',]},
		'POS Setting': {'fields':['currency','conversion_rate']},
		'Quotation': {'fields':['currency','conversion_rate']},
		'Receivable Voucher': {'fields':['currency','conversion_rate']},
		'Quotation': {'fields':['currency','conversion_rate']},
		'Item': {'ref_rate_details':['currency']},
		'Sales BOM': {'fields':['currency']},
		'Sales Order': {'fields':['currency','conversion_rate']},
		'Supplier Quotation': {'fields':['currency','conversion_rate']}
	},
	'imports': {
		'Payable Voucher': {'fields':['currency','conversion_rate']},
		'Purchase Order': {'fields':['currency','conversion_rate']},
		'Purchase Receipt': {'fields':['currency','conversion_rate']},
		'Receivable Voucher': {'fields':['currency','conversion_rate']},
		'Supplier Quotation': {'fields':['currency','conversion_rate']}
	}

}

$(document).bind('form_refresh', function() {
	for(sys_feat in sys_defaults)
	{
		if(sys_defaults[sys_feat]=='0' && (sys_feat in pscript.feature_dict)) //"Features to hide" exists
		{
			if(cur_frm.doc.doctype in  pscript.feature_dict[sys_feat])
			{
				for(fort in pscript.feature_dict[sys_feat][cur_frm.doc.doctype])
				{
					if(fort=='fields')
						hide_field(pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort]);
					else
					{
						for(grid_field in pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort])
							if(cur_frm.fields_dict[fort])
								cur_frm.fields_dict[fort].grid.set_column_disp(pscript.feature_dict[sys_feat][cur_frm.doc.doctype][fort][grid_field], false);
							else
								alert('Grid "'+fort+'" does not exists');
					}
				}
			}
		}
	}
})
