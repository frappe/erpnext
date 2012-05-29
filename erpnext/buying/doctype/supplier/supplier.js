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
			render_row: function(wrapper, data) {
				$(wrapper).css('padding','5px 0px');
				var link = $ln(wrapper,cstr(data.name), function() { loaddoc("Address", this.dn); }, {fontWeight:'bold'});
				link.dn = data.name
				
				$a(wrapper,'span','',{marginLeft:'5px', color: '#666'},(data.is_primary_address ? '[Primary]' : '') + (data.is_shipping_address ? '[Shipping]' : ''));
				$a(wrapper,'div','',{marginTop:'5px', color:'#555'}, 
					(data.address_line1 ? data.address_line1 + '<br />' : '') + 
					(data.address_line2 ? data.address_line2 + '<br />' : '') + 
					(data.city ? data.city + '<br />' : '') + 
					(data.state ? data.state + ', ' : '') + 
					(data.country ? data.country  + '<br />' : '') + 
					(data.pincode ? 'Pincode: ' + data.pincode + '<br />' : '') + 
					(data.phone ? 'Phone: ' + data.phone + '<br />' : '') + 
					(data.fax ? 'Fax: ' + data.fax + '<br />' : '') + 
					(data.email_id ? 'Email: ' + data.email_id + '<br />' : ''));			
			}
		});
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
			render_row: function(wrapper, data) {
				$(wrapper).css('padding', '5px 0px');
				var link = $ln(wrapper, cstr(data.name), function() { loaddoc("Contact", this.dn); }, {fontWeight:'bold'});
				link.dn = data.name

				$a(wrapper,'span','',{marginLeft:'5px', color: '#666'},(data.is_primary_contact ? '[Primary]' : ''));
				$a(wrapper,'div', '',{marginTop:'5px', color:'#555'}, data.first_name + (data.last_name ? ' ' + data.last_name + '<br />' : '<br>') + (data.phone ? 'Tel: ' + data.phone + '<br />' : '') + (data.mobile_no ? 'Mobile: ' + data.mobile_no + '<br />' : '') + (data.email_id ? 'Email: ' + data.email_id + '<br />' : '') + (data.department ? 'Department: ' + data.department + '<br />' : '') + (data.designation ? 'Designation: ' + data.designation + '<br />' : ''));
			}
		});
	}
	cur_frm.contact_list.run();
}


// Transaction History

cur_frm.cscript.make_po_list = function(parent, doc) {
	cur_frm.cscript.render_transaction_history(parent, doc, 'Purchase Order', 
		[
			{fieldname: 'name', width: '28%', label: 'Id', type: 'Link'},
			{fieldname: 'status', width: '25%', label: 'Status', type: 'Data'},
			{fieldname: 'modified', width: '12%', label: 'Last Modified On', 
				type: 'Date', style: 'text-align: right; color: #777'},
			{fieldname: 'currency', width: '0%', label: 'Currency', 
				style: 'display: hidden'},
			{fieldname: 'grand_total', width: '35%', label: 'Grand Total', 
				type: 'Currency', style: 'text-align: right'},
		]);
}

cur_frm.cscript.make_pr_list = function(parent, doc) {
	cur_frm.cscript.render_transaction_history(parent, doc, 'Purchase Receipt', 
		[
			{fieldname: 'name', width: '28%', label: 'Id', type: 'Link'},
			{fieldname: 'status', width: '15%', label: 'Status', type: 'Data'},
			{fieldname: 'per_billed', width: '10%', label: '% Billed', 
				type: 'Percentage', style: 'text-align: right'},
			{fieldname: 'modified', width: '12%', label: 'Last Modified On', 
				type: 'Date', style: 'text-align: right; color: #777'},
			{fieldname: 'currency', width: '0%', label: 'Currency', 
				style: 'display: hidden'},
			{fieldname: 'grand_total', width: '35%', label: 'Grand Total', 
				type: 'Currency', style: 'text-align: right'},
		]);
}

cur_frm.cscript.make_pi_list = function(parent, doc) {
	cur_frm.cscript.render_transaction_history(parent, doc, 'Purchase Invoice', 
		[
			{fieldname: 'name', width: '30%', label: 'Id', type: 'Link'},
			{fieldname: 'modified', width: '35%', label: 'Last Modified On', 
				type: 'Date', style: 'text-align: right; color: #777'},
			{fieldname: 'currency', width: '0%', label: 'Currency', 
				style: 'display: hidden'},
			{fieldname: 'grand_total', width: '35%', label: 'Grand Total', 
				type: 'Currency', style: 'text-align: right'},
		]);
}