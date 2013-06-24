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

// Module Material Management
cur_frm.cscript.tname = "Delivery Note Item";
cur_frm.cscript.fname = "delivery_note_details";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/selling/doctype/sales_common/sales_common.js');

wn.provide("erpnext.stock");
erpnext.stock.DeliveryNoteController = erpnext.selling.SellingController.extend({
	refresh: function(doc, dt, dn) {
		this._super();
		
		if(flt(doc.per_billed, 2) < 100 && doc.docstatus==1) cur_frm.add_custom_button('Make Invoice', cur_frm.cscript['Make Sales Invoice']);
	
		if(flt(doc.per_installed, 2) < 100 && doc.docstatus==1) cur_frm.add_custom_button('Make Installation Note', cur_frm.cscript['Make Installation Note']);

		if (doc.docstatus==1) cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);

		if(doc.docstatus==0 && !doc.__islocal) {
			cur_frm.add_custom_button('Make Packing Slip', cur_frm.cscript['Make Packing Slip']);
		}
	
		set_print_hide(doc, dt, dn);
	
		// unhide expense_account and cost_center is auto_inventory_accounting enabled
		var aii_enabled = cint(sys_defaults.auto_inventory_accounting)
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp("expense_account", aii_enabled);
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp("cost_center", aii_enabled);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.stock.DeliveryNoteController({frm: cur_frm}));

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}


cur_frm.cscript.get_items = function(doc,dt,dn) {
	var callback = function(r,rt){
		var doc = locals[cur_frm.doctype][cur_frm.docname];					
		if(r.message){							
			doc.sales_order_no = r.message;			
			if(doc.sales_order_no) {					
				unhide_field(['customer_address','contact_person','territory','customer_group']);														
			}			
			
			refresh_many(['delivery_note_details', 'customer', 'customer_address',
			 	'contact_person', 'customer_name', 'address_display', 'contact_display',
			 	'contact_mobile', 'contact_email', 'territory', 'customer_group']);
		}
	} 
 $c_obj(make_doclist(doc.doctype, doc.name),'pull_sales_order_details','',callback); 
}


//================ create new contact ============================================================================
cur_frm.cscript.new_contact = function(){
	tn = wn.model.make_new_doc_and_get_name('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	loaddoc('Contact', tn);
}


// ***************** Get project name *****************
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	var cond = '';
	if(doc.customer) cond = '(`tabProject`.customer = "'+doc.customer+'" OR IFNULL(`tabProject`.customer,"")="") AND';
	return repl('SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND %(cond)s `tabProject`.name LIKE "%s" \
		ORDER BY `tabProject`.name ASC LIMIT 50', {cond:cond});
}


// *************** Customized link query for SALES ORDER based on customer and currency***************************** 
cur_frm.fields_dict['sales_order_no'].get_query = function(doc) {
	doc = locals[this.doctype][this.docname];
	var cond = '';
	
	if(doc.customer) {
		cond = '`tabSales Order`.customer = "'+doc.customer+'" and';
	}

	if(doc.project_name){
		cond += '`tabSales Order`.project_name ="'+doc.project_name+'"';
	}
	return repl('SELECT DISTINCT `tabSales Order`.`name` FROM `tabSales Order` WHERE `tabSales Order`.company = "%(company)s" and `tabSales Order`.`docstatus` = 1 and `tabSales Order`.`status` != "Stopped" and ifnull(`tabSales Order`.per_delivered,0) < 99.99 and %(cond)s `tabSales Order`.%(key)s LIKE "%s" ORDER BY `tabSales Order`.`name` DESC LIMIT 50', {company:doc.company,cond:cond})
}

cur_frm.cscript.serial_no = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.serial_no) {
		 get_server_fields('get_serial_details',d.serial_no,'delivery_note_details',doc,cdt,cdn,1);
	}
}

cur_frm.fields_dict['transporter_name'].get_query = function(doc) {
	return 'SELECT DISTINCT `tabSupplier`.`name` FROM `tabSupplier` WHERE `tabSupplier`.supplier_type = "transporter" AND `tabSupplier`.docstatus != 2 AND `tabSupplier`.%(key)s LIKE "%s" ORDER BY `tabSupplier`.`name` LIMIT 50';
}

cur_frm.cscript['Make Sales Invoice'] = function() {
	var doc = cur_frm.doc
	n = wn.model.make_new_doc_and_get_name('Sales Invoice');
	$c('dt_map', args={
		'docs':wn.model.compress([locals['Sales Invoice'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Sales Invoice',
		'from_docname':doc.name,
		'from_to_list':"[['Delivery Note','Sales Invoice'],['Delivery Note Item','Sales Invoice Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team']]"
		}, function(r,rt) {
			 loaddoc('Sales Invoice', n);
		}
	);
}

cur_frm.cscript['Make Installation Note'] = function() {
	var doc = cur_frm.doc;
	if(doc.per_installed < 99.99){
		n = wn.model.make_new_doc_and_get_name('Installation Note');
		$c('dt_map', args={
			'docs':wn.model.compress([locals['Installation Note'][n]]),
			'from_doctype':doc.doctype,
			'to_doctype':'Installation Note',
			'from_docname':doc.name,
			'from_to_list':"[['Delivery Note','Installation Note'],['Delivery Note Item','Installation Note Item']]"
			}, function(r,rt) {
				 loaddoc('Installation Note', n);
			}
		);
	}
	else if(doc.per_installed >= 100)
		msgprint("Item installation is already completed")
}

cur_frm.cscript['Make Packing Slip'] = function() {
	n = wn.model.make_new_doc_and_get_name('Packing Slip');
	ps = locals["Packing Slip"][n];
	ps.delivery_note = cur_frm.doc.name;
	loaddoc('Packing Slip', n);
}


//get query select Territory
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

var set_print_hide= function(doc, cdt, cdn){
	var dn_fields = wn.meta.docfield_map['Delivery Note'];
	var dn_item_fields = wn.meta.docfield_map['Delivery Note Item'];
	
	if (doc.print_without_amount) {
		dn_fields['currency'].print_hide = 1;
		dn_item_fields['export_rate'].print_hide = 1;
		dn_item_fields['adj_rate'].print_hide = 1;
		dn_item_fields['ref_rate'].print_hide = 1;
		dn_item_fields['export_amount'].print_hide = 1;
	} else {
		dn_fields['currency'].print_hide = 0;
		dn_item_fields['export_rate'].print_hide = 0;
		dn_item_fields['export_amount'].print_hide = 0;
	}
}

cur_frm.cscript.print_without_amount = function(doc, cdt, cdn) {
	set_print_hide(doc, cdt, cdn);
}


//****************** For print sales order no and date*************************
cur_frm.pformat.sales_order_no= function(doc, cdt, cdn){
	//function to make row of table
	
	var make_row = function(title,val1, val2, bold){
		var bstart = '<b>'; var bend = '</b>';

		return '<tr><td style="width:39%;">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
		 +'<td style="width:61%;text-align:left;">'+val1+(val2?' ('+dateutil.str_to_user(val2)+')':'')+'</td>'
		 +'</tr>'
	}

	out ='';
	
	var cl = getchildren('Delivery Note Item',doc.name,'delivery_note_details');

	// outer table	
	var out='<div><table class="noborder" style="width:100%"><tr><td style="width: 50%"></td><td>';
	
	// main table
	out +='<table class="noborder" style="width:100%">';

	// add rows
	if(cl.length){
		prevdoc_list = new Array();
		for(var i=0;i<cl.length;i++){
			if(cl[i].prevdoc_doctype == 'Sales Order' && cl[i].prevdoc_docname && prevdoc_list.indexOf(cl[i].prevdoc_docname) == -1) {
				prevdoc_list.push(cl[i].prevdoc_docname);
				if(prevdoc_list.length ==1)
					out += make_row(cl[i].prevdoc_doctype, cl[i].prevdoc_docname, cl[i].prevdoc_date,0);
				else
					out += make_row('', cl[i].prevdoc_docname, cl[i].prevdoc_date,0);
			}
		}
	}

	out +='</table></td></tr></table></div>';

	return out;
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.delivery_note)) {
		cur_frm.email_doc(wn.boot.notification_settings.delivery_note_message);
	}
}

if (sys_defaults.auto_inventory_accounting) {

	cur_frm.cscript.expense_account = function(doc, cdt, cdn){
		var d = locals[cdt][cdn];
		if(d.expense_account) {
			var cl = getchildren('Delivery Note Item', doc.name, cur_frm.cscript.fname, doc.doctype);
			for(var i = 0; i < cl.length; i++){
				if(!cl[i].expense_account) cl[i].expense_account = d.expense_account;
			}
		}
		refresh_field(cur_frm.cscript.fname);
	}

	// expense account
	cur_frm.fields_dict['delivery_note_details'].grid.get_field('expense_account').get_query = function(doc) {
		return {
			"query": "accounts.utils.get_account_list", 
			"filters": {
				"is_pl_account": "Yes",
				"debit_or_credit": "Debit",
				"company": doc.company
			}
		}
	}

	// cost center
	cur_frm.cscript.cost_center = function(doc, cdt, cdn){
		var d = locals[cdt][cdn];
		if(d.cost_center) {
			var cl = getchildren('Delivery Note Item', doc.name, cur_frm.cscript.fname, doc.doctype);
			for(var i = 0; i < cl.length; i++){
				if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
			}
		}
		refresh_field(cur_frm.cscript.fname);
	}
	
	cur_frm.fields_dict.delivery_note_details.grid.get_field("cost_center").get_query = function(doc) {
		return {
			query: "accounts.utils.get_cost_center_list",
			filters: { company_name: doc.company}
		}
	}
}