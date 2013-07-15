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

cur_frm.cscript.tname = "Sales Invoice Item";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "other_charges";
cur_frm.cscript.sales_team_fname = "sales_team";

// print heading
cur_frm.pformat.print_heading = 'Invoice';

wn.require('app/selling/doctype/sales_common/sales_common.js');
wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');

// On Load
// -------
cur_frm.cscript.onload = function(doc,dt,dn) {
	cur_frm.cscript.manage_rounded_total();
	if(!doc.customer && doc.debit_to) wn.meta.get_docfield(dt, 'debit_to', dn).print_hide = 0;
	if (doc.__islocal) {
		if(!doc.due_date) set_multiple(dt,dn,{due_date:get_today()});
		if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
		if(!doc.currency && sys_defaults.currency) set_multiple(dt,dn,{currency:sys_defaults.currency});
		if(!doc.price_list_currency) set_multiple(dt, dn, {price_list_currency: doc.currency, plc_conversion_rate: 1});

	}
}

cur_frm.cscript.onload_post_render = function(doc, dt, dn) {
	var callback = function(doc, dt, dn) {
		// called from mapper, update the account names for items and customer
		var callback2 = function(doc, dt, dn) {
			if(doc.customer && doc.__islocal) {
				$c_obj(make_doclist(doc.doctype,doc.name),
					'load_default_accounts','',
					function(r,rt) {
						refresh_field('entries');
						cur_frm.cscript.customer(doc,dt,dn,onload=true);
					}
				);
			}
		}
		// defined in sales_common.js
		var callback1 = function(doc, dt, dn) {
			//for previously created sales invoice, set required field related to pos	
			cur_frm.cscript.update_item_details(doc, dt, dn, callback2);
		}
		
		if(doc.is_pos ==1) cur_frm.cscript.is_pos(doc, dt, dn,callback1);
		else cur_frm.cscript.update_item_details(doc, dt, dn, callback2);
	}

	cur_frm.cscript.hide_price_list_currency(doc, dt, dn, callback); 

}


// Hide Fields
// ------------
cur_frm.cscript.hide_fields = function(doc, cdt, cdn) {
	par_flds = ['project_name', 'due_date', 'sales_order_main',
	'delivery_note_main', 'get_items', 'is_opening', 'conversion_rate',
	'source', 'cancel_reason', 'total_advance', 'gross_profit',
	'gross_profit_percent', 'get_advances_received',
	'advance_adjustment_details', 'sales_partner', 'commission_rate',
	'total_commission', 'advances'];
	
	item_flds_normal = ['sales_order', 'delivery_note']
	item_flds_pos = ['warehouse', 'serial_no', 'batch_no', 'actual_qty', 
		'delivered_qty', 'expense_account']
	
	if(cint(doc.is_pos) == 1) {
		hide_field(par_flds);
		unhide_field('payments_section');
		for(f in item_flds_normal) cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_normal[f], false);
		for(f in item_flds_pos) cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_pos[f], (doc.update_stock==1?true:false));
	} else {
		hide_field('payments_section');
		unhide_field(par_flds);
		for(f in item_flds_normal) cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_normal[f], true);
		for(f in item_flds_pos) cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_pos[f], false);
	}

	cur_frm.toggle_display("contact_section", doc.customer);

	// India related fields
	var cp = wn.control_panel;
	if (cp.country == 'India') unhide_field(['c_form_applicable', 'c_form_no']);
	else hide_field(['c_form_applicable', 'c_form_no']);
}


// Refresh
// -------
cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.cscript.is_opening(doc, dt, dn);
	erpnext.hide_naming_series();

	// Show / Hide button
	cur_frm.clear_custom_buttons();
	if (!cur_frm.cscript.is_onload)	cur_frm.cscript.hide_price_list_currency(doc, dt, dn); 

	if(doc.docstatus==1) {
		cur_frm.add_custom_button('View Ledger', cur_frm.cscript.view_ledger_entry);
		cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);

		if(doc.is_pos==1 && doc.update_stock!=1)
			cur_frm.add_custom_button('Make Delivery', cur_frm.cscript['Make Delivery Note']);

		if(doc.outstanding_amount!=0)
			cur_frm.add_custom_button('Make Payment Entry', cur_frm.cscript.make_bank_voucher);
	}
	cur_frm.cscript.hide_fields(doc, dt, dn);
	
}

//fetch retail transaction related fields
//--------------------------------------------
cur_frm.cscript.is_pos = function(doc,dt,dn,callback){
	cur_frm.cscript.hide_fields(doc, dt, dn);
	if(doc.is_pos == 1){
		if (!doc.company) {
			msgprint("Please select company to proceed");
			doc.is_pos = 0;
			refresh_field('is_pos');
		}
		else {
			var callback1 = function(r,rt){
				if(callback) callback(doc, dt, dn);
				cur_frm.refresh();
			}
			$c_obj(make_doclist(dt,dn),'set_pos_fields','',callback1);
		}
	}
}

cur_frm.cscript.mode_of_payment = function(doc) {
	cur_frm.call({
		method: "get_bank_cash_account",
		args: { mode_of_payment: doc.mode_of_payment }
	});
}

cur_frm.cscript.update_stock = function(doc, dt, dn) {
	cur_frm.cscript.hide_fields(doc, dt, dn);
}

cur_frm.cscript.warehouse = function(doc, cdt , cdn) {
	var d = locals[cdt][cdn];
	if (!d.item_code) { msgprint("please enter item code first"); return };
	if (d.warehouse) {
		arg = "{'item_code':'" + d.item_code + "','warehouse':'" + d.warehouse +"'}";
		get_server_fields('get_actual_qty',arg,'entries',doc,cdt,cdn,1);
	}
}



//Customer
cur_frm.cscript.customer = function(doc,dt,dn,onload) {
	cur_frm.toggle_display("contact_section", doc.customer);
	
	var pl = doc.price_list_name;
	var callback = function(r,rt) {
			var callback2 = function(doc, dt, dn) {
				doc = locals[dt][dn];
				if(doc.debit_to && doc.posting_date){
					get_server_fields('get_cust_and_due_date','','',doc,dt,dn,1,
					function(doc, dt, dn) {
						cur_frm.refresh();
						if (!onload && (pl != doc.price_list_name)) cur_frm.cscript.price_list_name(doc, dt, dn);
					});
					
				}
			}
			var doc = locals[cur_frm.doctype][cur_frm.docname];
			get_server_fields('get_debit_to','','',doc, dt, dn, 0, callback2);
	}
	var args = onload ? 'onload':''
	if(doc.customer) $c_obj(make_doclist(doc.doctype, doc.name), 'get_default_customer_address', args, callback);
	
}



cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {
	if(doc.customer) get_server_fields('get_customer_address', JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

// Set Due Date = posting date + credit days
cur_frm.cscript.debit_to = function(doc,dt,dn) {

	var callback2 = function(r,rt) {
			var doc = locals[cur_frm.doctype][cur_frm.docname];
			cur_frm.refresh();
	}

	var callback = function(r,rt) {
			var doc = locals[cur_frm.doctype][cur_frm.docname];
			if(doc.customer) $c_obj(make_doclist(dt,dn), 'get_default_customer_address', '', callback2);
			cur_frm.toggle_display("contact_section", doc.customer);
			
			cur_frm.refresh();
	}

	if(doc.debit_to && doc.posting_date){
		get_server_fields('get_cust_and_due_date','','',doc,dt,dn,1,callback);
	}
}



//refresh advance amount
//-------------------------------------------------


cur_frm.cscript.write_off_outstanding_amount_automatically = function(doc) {
	if (doc.write_off_outstanding_amount_automatically == 1) 
		doc.write_off_amount = flt(doc.grand_total) - flt(doc.paid_amount);
	
	doc.outstanding_amount = flt(doc.grand_total) - flt(doc.paid_amount) - flt(doc.write_off_amount);
	refresh_field(['write_off_amount', 'outstanding_amount']);
}

cur_frm.cscript.paid_amount = function(doc) {
	cur_frm.cscript.write_off_outstanding_amount_automatically(doc);
}

cur_frm.cscript.write_off_amount = function(doc) {
	cur_frm.cscript.write_off_outstanding_amount_automatically(doc);
}


//Set debit and credit to zero on adding new row
//----------------------------------------------
cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){

	cl = getchildren('Sales Invoice Item', doc.name, cur_frm.cscript.fname, doc.doctype);
	acc = '';
	cc = '';

	for(var i = 0; i<cl.length; i++) {

		if (cl[i].idx == 1){
			acc = cl[i].income_account;
			cc = cl[i].cost_center;
		}
		else{
			if (! cl[i].income_account) { cl[i].income_account = acc; refresh_field('income_account', cl[i].name, 'entries');}
			if (! cl[i].cost_center)	{cl[i].cost_center = cc;refresh_field('cost_center', cl[i].name, 'entries');}
		}
	}
}

cur_frm.cscript.is_opening = function(doc, dt, dn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

// Get Items based on SO or DN Selected
cur_frm.cscript.get_items = function(doc, dt, dn) {
	var callback = function(r,rt) {
		unhide_field(['customer_address','contact_person', 'territory','customer_group']);
		cur_frm.refresh_fields();
	}
	get_server_fields('pull_details','','',doc, dt, dn,1,callback);
}



// Allocated Amount in advances table
// -----------------------------------
cur_frm.cscript.allocated_amount = function(doc,cdt,cdn){
	cur_frm.cscript.calc_adjustment_amount(doc,cdt,cdn);
}

//Make Delivery Note Button
//-----------------------------

cur_frm.cscript['Make Delivery Note'] = function() {

	var doc = cur_frm.doc
	n = wn.model.make_new_doc_and_get_name('Delivery Note');
	$c('dt_map', args={
		'docs':wn.model.compress([locals['Delivery Note'][n]]),
		'from_doctype':doc.doctype,
		'to_doctype':'Delivery Note',
		'from_docname':doc.name,
		'from_to_list':"[['Sales Invoice','Delivery Note'],['Sales Invoice Item','Delivery Note Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team']]"
		}, function(r,rt) {
			 loaddoc('Delivery Note', n);
		}
	);
}

cur_frm.cscript.make_bank_voucher = function() {
	wn.call({
		method: "accounts.doctype.journal_voucher.journal_voucher.get_default_bank_cash_account",
		args: {
			"company": cur_frm.doc.company,
			"voucher_type": "Bank Voucher"
		},
		callback: function(r) {
			cur_frm.cscript.make_jv(cur_frm.doc, null, null, r.message);
		}
	});
}

cur_frm.fields_dict.debit_to.get_query = function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Debit" AND tabAccount.is_pl_account = "Yes" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return 'SELECT `tabCost Center`.name FROM `tabCost Center` WHERE `tabCost Center`.group_or_ledger="Ledger" AND `tabCost Center`.docstatus!=2 AND `tabCost Center`.company_name="'+doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s"'
}

//project name
//--------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	var cond = '';
	if(doc.customer) cond = '(`tabProject`.customer = "'+doc.customer+'" OR IFNULL(`tabProject`.customer,"")="") AND';
	return repl('SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND %(cond)s `tabProject`.name LIKE "%s" \
		ORDER BY `tabProject`.name ASC LIMIT 50', {cond:cond});
}

//Territory
//-----------------------------
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` FROM `tabTerritory` WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

// Income Account in Details Table
// --------------------------------
cur_frm.set_query("income_account", "entries", function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE (tabAccount.debit_or_credit="Credit" OR tabAccount.account_type = "Income Account") AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus!=2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"';	
})

// expense account
if (sys_defaults.auto_inventory_accounting) {
	cur_frm.fields_dict['entries'].grid.get_field('expense_account').get_query = function(doc) {
		return {
			"query": "accounts.utils.get_account_list", 
			"filters": {
				"is_pl_account": "Yes",
				"debit_or_credit": "Debit",
				"company": doc.company
			}
		}
	}
}

// warehouse in detail table
//----------------------------
cur_frm.fields_dict['entries'].grid.get_field('warehouse').get_query= function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return "SELECT `tabBin`.`warehouse`, `tabBin`.`actual_qty` FROM `tabBin` WHERE `tabBin`.`item_code` = '"+ d.item_code +"' AND ifnull(`tabBin`.`actual_qty`,0) > 0 AND `tabBin`.`warehouse` like '%s' ORDER BY `tabBin`.`warehouse` DESC LIMIT 50";
}

// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		query: "accounts.utils.get_cost_center_list",
		filters: { company_name: doc.company}
	}
}

// Sales Order
// -----------
cur_frm.fields_dict.sales_order_main.get_query = function(doc) {
	if (doc.customer)
		return 'SELECT DISTINCT `tabSales Order`.`name` FROM `tabSales Order` WHERE `tabSales Order`.company = "' + doc.company + '" and `tabSales Order`.`docstatus` = 1 and `tabSales Order`.`status` != "Stopped" and ifnull(`tabSales Order`.per_billed,0) < 99.99 and `tabSales Order`.`customer` =	"' + doc.customer + '" and `tabSales Order`.%(key)s LIKE "%s" ORDER BY `tabSales Order`.`name` DESC LIMIT 50';
	else
		return 'SELECT DISTINCT `tabSales Order`.`name` FROM `tabSales Order` WHERE `tabSales Order`.company = "' + doc.company + '" and `tabSales Order`.`docstatus` = 1 and `tabSales Order`.`status` != "Stopped" and ifnull(`tabSales Order`.per_billed,0) < 99.99 and `tabSales Order`.%(key)s LIKE "%s" ORDER BY `tabSales Order`.`name` DESC LIMIT 50';
}

// Delivery Note
// --------------
cur_frm.fields_dict.delivery_note_main.get_query = function(doc) {
	if (doc.customer)
		return 'SELECT DISTINCT `tabDelivery Note`.`name` FROM `tabDelivery Note` \
			WHERE `tabDelivery Note`.company = "' + doc.company 
			+ '" and `tabDelivery Note`.`docstatus` = 1 and \
			ifnull(`tabDelivery Note`.per_billed,0) < 99.99 and \
			`tabDelivery Note`.`customer` =	"' 
			+ doc.customer + '" and `tabDelivery Note`.%(key)s LIKE "%s" \
			ORDER BY `tabDelivery Note`.`name` DESC LIMIT 50';
	else
		return 'SELECT DISTINCT `tabDelivery Note`.`name` FROM `tabDelivery Note` \
			WHERE `tabDelivery Note`.company = "' + doc.company 
			+ '" and `tabDelivery Note`.`docstatus` = 1 and \
			ifnull(`tabDelivery Note`.per_billed,0) < 99.99 and \
			`tabDelivery Note`.%(key)s LIKE "%s" \
			ORDER BY `tabDelivery Note`.`name` DESC LIMIT 50';
}



cur_frm.cscript.income_account = function(doc, cdt, cdn){
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "income_account");
}

cur_frm.cscript.expense_account = function(doc, cdt, cdn){
	cur_frm.cscript.copy_account_in_all_row(doc, cdt, cdn, "expense_account");
}

cur_frm.cscript.copy_account_in_all_row = function(doc, cdt, cdn, fieldname) {
	var d = locals[cdt][cdn];
	if(d[fieldname]){
		var cl = getchildren('Sales Invoice Item', doc.name, cur_frm.cscript.fname, doc.doctype);
		for(var i = 0; i < cl.length; i++){
			if(!cl[i][fieldname]) cl[i][fieldname] = d[fieldname];
		}
	}
	refresh_field(cur_frm.cscript.fname);
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.cost_center){
		var cl = getchildren('Sales Invoice Item', doc.name, cur_frm.cscript.fname, doc.doctype);
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
		}
	}
	refresh_field(cur_frm.cscript.fname);
}

cur_frm.cscript.calc_adjustment_amount = function(doc,cdt,cdn) {
	var doc = locals[doc.doctype][doc.name];
	var el = getchildren('Sales Invoice Advance',doc.name,'advance_adjustment_details');
	var total_adjustment_amt = 0
	for(var i in el) {
			total_adjustment_amt += flt(el[i].allocated_amount)
	}
	doc.total_advance = flt(total_adjustment_amt);
	doc.outstanding_amount = flt(doc.grand_total) - flt(total_adjustment_amt) - flt(doc.paid_amount) - flt(doc.write_off_amount);
	refresh_many(['total_advance','outstanding_amount']);
}


// Make Journal Voucher
// --------------------
cur_frm.cscript.make_jv = function(doc, dt, dn, bank_account) {
	var jv = wn.model.make_new_doc_and_get_name('Journal Voucher');
	jv = locals['Journal Voucher'][jv];
	jv.voucher_type = 'Bank Voucher';

	jv.company = doc.company;
	jv.remark = repl('Payment received against invoice %(vn)s for %(rem)s', {vn:doc.name, rem:doc.remarks});
	jv.fiscal_year = doc.fiscal_year;

	// debit to creditor
	var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = doc.debit_to;
	d1.credit = doc.outstanding_amount;
	d1.against_invoice = doc.name;


	// credit to bank
	var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = bank_account.account;
	d1.debit = doc.outstanding_amount;
	d1.balance = bank_account.balance;

	loaddoc('Journal Voucher', jv.name);
}


/****************** Get Accounting Entry *****************/
cur_frm.cscript.view_ledger_entry = function(){	
	wn.set_route('Report', 'GL Entry', 'General Ledger', 'Voucher No='+cur_frm.doc.name);
}

cur_frm.cscript.on_submit = function(doc, cdt, cdn) {
	if(cint(wn.boot.notification_settings.sales_invoice)) {
		cur_frm.email_doc(wn.boot.notification_settings.sales_invoice_message);
	}
}

cur_frm.cscript.convert_into_recurring_invoice = function(doc, dt, dn) {
	// set default values for recurring invoices
	if(doc.convert_into_recurring_invoice) {
		var owner_email = doc.owner=="Administrator"
			? wn.user_info("Administrator").email
			: doc.owner;
		
		doc.notification_email_address = $.map([cstr(owner_email),
			cstr(doc.contact_email)], function(v) { return v || null; }).join(", ");
		doc.repeat_on_day_of_month = wn.datetime.str_to_obj(doc.posting_date).getDate();
	}
		
	refresh_many(["notification_email_address", "repeat_on_day_of_month"]);
}

cur_frm.cscript.invoice_period_from_date = function(doc, dt, dn) {
	// set invoice_period_to_date
	if(doc.invoice_period_from_date) {
		var recurring_type_map = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6,
			'Yearly': 12};

		var months = recurring_type_map[doc.recurring_type];
		if(months) {
			var to_date = wn.datetime.add_months(doc.invoice_period_from_date,
				months);
			doc.invoice_period_to_date = wn.datetime.add_days(to_date, -1);
			refresh_field('invoice_period_to_date');
		}
	}
}
