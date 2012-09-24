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

cur_frm.cscript.onload = function(doc,dt,dn){

	// history doctypes and scripts
	cur_frm.history_dict = {
		'Purchase Order' : 'cur_frm.cscript.make_po_list(this.body, this.doc)',
		'Purchase Receipt' : 'cur_frm.cscript.make_pr_list(this.body, this.doc)',
		'Purchase Invoice' : 'cur_frm.cscript.make_pi_list(this.body, this.doc)'
	}
	
	// make contact, history list body
	//cur_frm.cscript.make_cl_body();
	cur_frm.cscript.make_hl_body();
	cur_frm.cscript.make_communication_body();
}

cur_frm.cscript.refresh = function(doc,dt,dn) {
  if(sys_defaults.supp_master_name == 'Supplier Name')
    hide_field('naming_series');
  else
    unhide_field('naming_series'); 
    
  if(doc.__islocal){
    	hide_field(['address_html','contact_html']); 
   }
  else{
	  	unhide_field(['address_html','contact_html']);
		// make lists
		cur_frm.cscript.make_address(doc,dt,dn);
		cur_frm.cscript.make_contact(doc,dt,dn);
		cur_frm.cscript.render_communication_list(doc, cdt, cdn);
		cur_frm.cscript.make_history(doc,dt,dn);
  }
}

cur_frm.cscript.make_address = function() {
	if(!cur_frm.address_list) {
		cur_frm.address_list = new wn.ui.Listing({
			parent: cur_frm.fields_dict['address_html'].wrapper,
			page_length: 2,
			new_doctype: "Address",
			get_query: function() {
				return "select name, address_type, address_line1, address_line2, city, state, country, pincode, fax, email_id, phone, is_primary_address, is_shipping_address from tabAddress where supplier='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_address desc"
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
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where supplier='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_contact desc"
			},
			as_dict: 1,
			no_results_message: 'No contacts created',
			render_row: cur_frm.cscript.render_contact_row,
		});
		// note: render_contact_row is defined in contact_control.js
	}
	cur_frm.contact_list.run();
}


// Transaction History

cur_frm.cscript.make_po_list = function(parent, doc) {
	var ListView = wn.views.ListView.extend({
		init: function(doclistview) {
			this._super(doclistview);
			this.fields = this.fields.concat([
				"`tabPurchase Order`.status",
				"`tabPurchase Order`.currency",
				"ifnull(`tabPurchase Order`.grand_total_import, 0) as grand_total_import",
				
			]);
		},

		prepare_data: function(data) {
			this._super(data);
			data.grand_total_import = data.currency + " " + fmt_money(data.grand_total_import);
		},

		columns: [
			{width: '3%', content: 'docstatus'},
			{width: '20%', content: 'name'},
			{width: '30%', content: 'status',
				css: {'text-align': 'right', 'color': '#777'}},
			{width: '35%', content: 'grand_total_import', css: {'text-align': 'right'}},
			{width: '12%', content:'modified', css: {'text-align': 'right'}}
		],
	});
	
	cur_frm.cscript.render_list(doc, 'Purchase Order', parent, ListView);
}

cur_frm.cscript.make_pr_list = function(parent, doc) {
	var ListView = wn.views.ListView.extend({
		init: function(doclistview) {
			this._super(doclistview);
			this.fields = this.fields.concat([
				"`tabPurchase Receipt`.status",
				"`tabPurchase Receipt`.currency",
				"ifnull(`tabPurchase Receipt`.grand_total_import, 0) as grand_total_import",
				"ifnull(`tabPurchase Receipt`.per_billed, 0) as per_billed",
			]);
		},

		prepare_data: function(data) {
			this._super(data);
			data.grand_total_import = data.currency + " " + fmt_money(data.grand_total_import);
		},

		columns: [
			{width: '3%', content: 'docstatus'},
			{width: '20%', content: 'name'},
			{width: '20%', content: 'status',
				css: {'text-align': 'right', 'color': '#777'}},
			{width: '35%', content: 'grand_total_import', css: {'text-align': 'right'}},
			{width: '10%', content: 'per_billed', type: 'bar-graph', label: 'Billed'},
			{width: '12%', content:'modified', css: {'text-align': 'right'}}
		],
	});
	
	cur_frm.cscript.render_list(doc, 'Purchase Receipt', parent, ListView);
}

cur_frm.cscript.make_pi_list = function(parent, doc) {
	var ListView = wn.views.ListView.extend({
		init: function(doclistview) {
			this._super(doclistview);
			this.fields = this.fields.concat([
				"`tabPurchase Invoice`.currency",
				"ifnull(`tabPurchase Invoice`.grand_total_import, 0) as grand_total_import",
			]);
		},

		prepare_data: function(data) {
			this._super(data);
			data.grand_total_import = data.currency + " " + fmt_money(data.grand_total_import);
		},

		columns: [
			{width: '3%', content: 'docstatus'},
			{width: '30%', content: 'name'},
			{width: '55%', content: 'grand_total_import', css: {'text-align': 'right'}},
			{width: '12%', content:'modified', css: {'text-align': 'right'}}
		],
	});
	
	cur_frm.cscript.render_list(doc, 'Purchase Invoice', parent, ListView);
}