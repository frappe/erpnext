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
				return "select name, first_name, last_name, email_id, phone, mobile_no, department, designation, is_primary_contact from tabContact where customer='"+cur_frm.docname+"' and docstatus != 2 order by is_primary_contact desc"
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

/* ********************************* client triggers ************************************** */

// ---------------
// customer group
// ---------------
cur_frm.fields_dict['customer_group'].get_query = function(doc,dt,dn) {
	return 'SELECT `tabCustomer Group`.`name`, `tabCustomer Group`.`parent_customer_group` FROM `tabCustomer Group` WHERE `tabCustomer Group`.`is_group` = "No" AND `tabCustomer Group`.`docstatus`!= 2 AND `tabCustomer Group`.%(key)s LIKE "%s" ORDER BY	`tabCustomer Group`.`name` ASC LIMIT 50';
}

cur_frm.cscript.CGHelp = function(doc,dt,dn){
	var call_back = function(){
		var sb_obj = new SalesBrowser();				
		sb_obj.set_val('Customer Group');
	}
	loadpage('Sales Browser',call_back);
}

// -----
// lead
// -----
cur_frm.fields_dict['lead_name'].get_query = function(doc,dt,dn){
	return 'SELECT `tabLead`.`name` FROM `tabLead` WHERE `tabLead`.`status`!="Converted" AND `tabLead`.%(key)s LIKE "%s" ORDER BY `tabLead`.`name` ASC LIMIT 50';	
}

/* ********************************* transaction history ************************************** */

// --------------------
// make quotation list
// --------------------
cur_frm.cscript.make_qtn_list = function(parent,doc){
	wn.require('lib/js/legacy/widgets/listing.js');

	var lst = new Listing();
	lst.colwidths = ['5%','20%','20%','20%','20%','15%'];
	lst.colnames = ['Sr.','Id','Status','Quotation Date','Contact Person','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Data','Currency'];
	lst.coloptions = ['','Quotation','','','',''];

	var q = repl("select name,status,transaction_date, contact_person, grand_total from tabQuotation where customer='%(cust)s' order by transaction_date desc", {'cust':doc.name});
	var q_max = repl("select count(name) from tabQuotation where customer='%(cust)s'", {'cust':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Quotation','Quotation');
}

// -------------
// make so list
// -------------
cur_frm.cscript.make_so_list = function(parent,doc){
	wn.require('lib/js/legacy/widgets/listing.js');

	var lst = new Listing();
	lst.colwidths = ['5%','20%','20%','30%','25%'];
	lst.colnames = ['Sr.','Id','Status','Sales Order Date','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Currency'];
	lst.coloptions = ['','Sales Order','','',''];

	var q = repl("select name,status,transaction_date, grand_total from `tabSales Order` where customer='%(cust)s' order by transaction_date desc", {'cust':doc.name});
	var q_max = repl("select count(name) from `tabSales Order` where customer='%(cust)s'", {'cust':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Sales Order','Sales Order');
}

// -------------
// make dn list
// -------------
cur_frm.cscript.make_dn_list = function(parent,doc){
	wn.require('lib/js/legacy/widgets/listing.js');

	var lst = new Listing();
	lst.colwidths = ['5%','20%','20%','20%','20%','15%'];
	lst.colnames = ['Sr.','Id','Status','Delivery Note Date','Territory','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Link','Currency'];
	lst.coloptions = ['','Delivery Note','','','Territory',''];

	var q = repl("select name,status,transaction_date,territory,grand_total from `tabDelivery Note` where customer='%(cust)s' order by transaction_date desc", {'cust':doc.name});
	var q_max = repl("select count(name) from `tabDelivery Note` where customer='%(cust)s'", {'cust':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Delivery Note','Delivery Note');
}

// -------------
// make si list
// -------------
cur_frm.cscript.make_si_list = function(parent,doc){
	wn.require('lib/js/legacy/widgets/listing.js');
	
	var lst = new Listing();
	lst.colwidths = ['5%','20%','20%','20%','20%','15%'];
	lst.colnames = ['Sr.','Id','Posting Date','Due Date','Debit To','Grand Total'];
	lst.coltypes = ['Data','Link','Data','Data','Link','Currency'];
	lst.coloptions = ['','Sales Invoice','','','Account',''];


	var q = repl("select name,posting_date,due_date,debit_to,grand_total from `tabSales Invoice` where customer='%(cust)s' order by posting_date desc", {'cust':doc.name});
	var q_max = repl("select count(name) from `tabSales Invoice` where customer='%(cust)s'", {'cust':doc.name});
	
	cur_frm.cscript.run_list(lst,parent,q,q_max,doc,'Sales Invoice','Sales Invoice');
}
