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
		
		if(flt(doc.per_billed, 2) < 100 && doc.docstatus==1) cur_frm.add_custom_button('Make Invoice', this.make_sales_invoice);
	
		if(flt(doc.per_installed, 2) < 100 && doc.docstatus==1) 
			cur_frm.add_custom_button('Make Installation Note', this.make_installation_note);

		if (doc.docstatus==1) {
			cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);
		}

		if(doc.docstatus==0 && !doc.__islocal) {
			cur_frm.add_custom_button('Make Packing Slip', cur_frm.cscript['Make Packing Slip']);
		}
	
		set_print_hide(doc, dt, dn);
	
		// unhide expense_account and cost_center is auto_inventory_accounting enabled
		var aii_enabled = cint(sys_defaults.auto_inventory_accounting)
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp("expense_account", aii_enabled);
		cur_frm.fields_dict[cur_frm.cscript.fname].grid.set_column_disp("cost_center", aii_enabled);

		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Sales Order'), 
				function() {
					wn.model.map_current_doc({
						method: "selling.doctype.sales_order.sales_order.make_delivery_note",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_delivered: ["<", 99.99],
							project_name: cur_frm.doc.project_name || undefined,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});
		}

	}, 
	
	make_sales_invoice: function() {
		wn.model.open_mapped_doc({
			method: "stock.doctype.delivery_note.delivery_note.make_sales_invoice",
			source_name: cur_frm.doc.name
		})
	}, 
	
	make_installation_note: function() {
		wn.model.open_mapped_doc({
			method: "stock.doctype.delivery_note.delivery_note.make_installation_note",
			source_name: cur_frm.doc.name
		});
	},

	tc_name: function() {
		this.get_terms();
	},
	
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.stock.DeliveryNoteController({frm: cur_frm}));

cur_frm.cscript.new_contact = function(){
	tn = wn.model.make_new_doc_and_get_name('Contact');
	locals['Contact'][tn].is_customer = 1;
	if(doc.customer) locals['Contact'][tn].customer = doc.customer;
	loaddoc('Contact', tn);
}


// ***************** Get project name *****************
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	return {
		query: "controllers.queries.get_project_name",
		filters: {
			'customer': doc.customer
		}
	}
}

cur_frm.cscript.serial_no = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.serial_no) {
		 get_server_fields('get_serial_details',d.serial_no,'delivery_note_details',doc,cdt,cdn,1);
	}
}

cur_frm.fields_dict['transporter_name'].get_query = function(doc) {
	return{
		filters: { 'supplier_type': "transporter" }
	}	
}

cur_frm.cscript['Make Packing Slip'] = function() {
	n = wn.model.make_new_doc_and_get_name('Packing Slip');
	ps = locals["Packing Slip"][n];
	ps.delivery_note = cur_frm.doc.name;
	loaddoc('Packing Slip', n);
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
			filters: {
				"is_pl_account": "Yes",
				"debit_or_credit": "Debit",
				"company": doc.company,
				"group_or_ledger": "Ledger"
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

			filters: { 
				'company': doc.company,
				'group_or_ledger': "Ledger"
			}
		}
	}
}