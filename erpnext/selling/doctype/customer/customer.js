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

wn.require('erpnext/setup/doctype/contact_control/contact_control.js');
wn.require('erpnext/support/doctype/communication/communication.js');

/* ********************************* onload ********************************************* */

cur_frm.cscript.onload = function(doc,dt,dn){
	// history doctypes and scripts
	cur_frm.history_dict = {
		'Quotation' : 'cur_frm.cscript.make_qtn_list(this.body, this.doc)',
		'Sales Order' : 'cur_frm.cscript.make_so_list(this.body, this.doc)',
		'Delivery Note' : 'cur_frm.cscript.make_dn_list(this.body, this.doc)',
		'Sales Invoice' : 'cur_frm.cscript.make_si_list(this.body, this.doc)'
	}
	// make address, contact, shipping, history list body
	cur_frm.cscript.make_hl_body();
  	//cur_frm.cscript.make_sl_body();

	cur_frm.cscript.load_defaults(doc, dt, dn);
	
	cur_frm.cscript.make_communication_body();
}

cur_frm.cscript.load_defaults = function(doc, dt, dn) {
	doc = locals[doc.doctype][doc.name];
	if(!(doc.__islocal && doc.lead_name)) { return; }

	var fields_to_refresh = LocalDB.set_default_values(doc);
	if(fields_to_refresh) { refresh_many(fields_to_refresh); }
}

cur_frm.add_fetch('lead_name', 'company_name', 'customer_name');
cur_frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');

/* ********************************* refresh ********************************************* */

cur_frm.cscript.refresh = function(doc,dt,dn) {
	if(sys_defaults.cust_master_name == 'Customer Name')
		hide_field('naming_series');
	else
		unhide_field('naming_series');

	if(doc.__islocal){		
		hide_field(['address_html','contact_html']);
		//cur_frm.cscript.set_hl_msg(doc);
 		//cur_frm.cscript.set_sl_msg(doc);
	}else{
		unhide_field(['address_html','contact_html']);
		// make lists
		cur_frm.cscript.make_address(doc,dt,dn);
		cur_frm.cscript.make_contact(doc,dt,dn);
		cur_frm.cscript.make_history(doc,dt,dn);
		cur_frm.cscript.render_communication_list(doc, cdt, cdn);
		//cur_frm.cscript.make_shipping_address(doc,dt,dn);
	}
}

cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new wn.ui.Listing({
			parent: cur_frm.fields_dict['address_html'].wrapper,
			page_length: 2,
			new_doctype: "Address",
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where customer='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_address desc"
			},
			as_dict: 1,
			no_results_message: 'No addresses created',
			render_row: cur_frm.cscript.render_address_row,
		});
		// note: render_address_row is defined in contact_control.js
	}
	cur_frm.address_list.run();
}

cur_frm.cscript.make_contact = function() {
	if(!cur_frm.contact_list) {
		cur_frm.contact_list = new wn.ui.Listing({
			parent: cur_frm.fields_dict['contact_html'].wrapper,
			page_length: 2,
			new_doctype: "Contact",
			get_query: function() {
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where customer='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_contact desc"
			},
			as_dict: 1,
			no_results_message: 'No contacts created',
			render_row: cur_frm.cscript.render_contact_row,
		});
		// note: render_contact_row is defined in contact_control.js
	}
	cur_frm.contact_list.run();

}

/* ********************************* client triggers ************************************** */

// ---------------
// customer group
// ---------------
cur_frm.fields_dict['customer_group'].get_query = function(doc,dt,dn) {
	return 'SELECT `tabCustomer Group`.`name`, `tabCustomer Group`.`parent_customer_group` FROM `tabCustomer Group` WHERE `tabCustomer Group`.`is_group` = "No" AND `tabCustomer Group`.`docstatus`!= 2 AND `tabCustomer Group`.%(key)s LIKE "%s" ORDER BY	`tabCustomer Group`.`name` ASC LIMIT 50';
}


// -----
// lead
// -----
cur_frm.fields_dict['lead_name'].get_query = function(doc,dt,dn){
	return 'SELECT `tabLead`.`name` FROM `tabLead` WHERE `tabLead`.`status`!="Converted" AND `tabLead`.%(key)s LIKE "%s" ORDER BY `tabLead`.`name` ASC LIMIT 50';	
}


// Transaction History
// functions called by these functions are defined in communication.js
cur_frm.cscript.make_qtn_list = function(parent, doc) {
	cur_frm.cscript.get_common_list_view(parent, doc, 'Quotation');
}

cur_frm.cscript.make_so_list = function(parent, doc) {
	cur_frm.cscript.get_common_list_view(parent, doc, 'Sales Order');
}

cur_frm.cscript.make_dn_list = function(parent, doc) {
	cur_frm.cscript.get_common_list_view(parent, doc, 'Delivery Note');
}

cur_frm.cscript.get_common_list_view = function(parent, doc, doctype) {
	var ListView = wn.views.ListView.extend({
		init: function(doclistview) {
			this._super(doclistview);
			this.fields = this.fields.concat([
				"`tab" + doctype + "`.status",
				"`tab" + doctype + "`.currency",
				"ifnull(`tab" + doctype + "`.grand_total_export, 0) as grand_total_export",
				
			]);
		},

		prepare_data: function(data) {
			this._super(data);
			data.grand_total_export = data.currency + " " + fmt_money(data.grand_total_export)
		},

		columns: [
			{width: '3%', content: 'docstatus'},
			{width: '25%', content: 'name'},
			{width: '25%', content: 'status'},
			{width: '35%', content: 'grand_total_export', css: {'text-align': 'right'}},			
			{width: '12%', content:'modified', css: {'text-align': 'right'}}		
		],
	});
	
	cur_frm.cscript.render_list(doc, doctype, parent, ListView);
}


cur_frm.cscript.make_si_list = function(parent, doc) {
	var ListView = wn.views.ListView.extend({
		init: function(doclistview) {
			this._super(doclistview);
			this.fields = this.fields.concat([
				"ifnull(`tabSales Invoice`.outstanding_amount, 0) as outstanding_amount",
				"`tabSales Invoice`.currency",
				"ifnull(`tabSales Invoice`.conversion_rate, 0) as conversion_rate",
				"ifnull(`tabSales Invoice`.grand_total_export, 0) as grand_total_export",
				
			]);
		},

		prepare_data: function(data) {
			this._super(data);
			if (data.outstanding_amount) {
				data.outstanding_amount = data.currency + " " + 
					fmt_money(flt(data.outstanding_amount)/flt(data.conversion_rate)) + 
					" [outstanding]";
				
			} else {
				data.outstanding_amount = '';
			}
			data.grand_total_export = data.currency + " " + fmt_money(data.grand_total_export);
		},

		columns: [
			{width: '3%', content: 'docstatus'},
			{width: '25%', content: 'name'},
			{width: '25%', content: 'outstanding_amount',
				css: {'text-align': 'right', 'color': '#777'}},
			{width: '35%', content: 'grand_total_export', css: {'text-align': 'right'}},
			{width: '12%', content:'modified', css: {'text-align': 'right'}}
		],
	});
	
	cur_frm.cscript.render_list(doc, 'Sales Invoice', parent, ListView);
}