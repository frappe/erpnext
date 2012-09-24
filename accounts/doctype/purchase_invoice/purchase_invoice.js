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

cur_frm.cscript.tname = "Purchase Invoice Item";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "purchase_tax_details";
wn.require('erpnext/accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js');
wn.require('erpnext/buying/doctype/purchase_common/purchase_common.js');

// On Load
// --------
cur_frm.cscript.onload = function(doc,dt,dn) {
	if(!doc.voucher_date) set_multiple(dt,dn,{voucher_date:get_today()});
	if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});  
	
	tds_flds = ['tds','tds_applicable','tds_category','get_tds','tax_code','rate','ded_amount','total_tds_on_voucher','tds_amount_on_advance'];
	if(wn.control_panel.country == 'India') unhide_field(tds_flds);
	else hide_field(tds_flds);
}


//Onload post render
//------------------------
cur_frm.cscript.onload_post_render = function(doc, dt, dn) {
	var callback = function(doc, dt, dn) {
		var callback1 = function(doc, dt, dn) {
			if(doc.__islocal && doc.supplier) cur_frm.cscript.supplier(doc,dt,dn);
		}
	
		// defined in purchase_common.js
		cur_frm.cscript.update_item_details(doc, dt, dn, callback1);
	}
	cur_frm.cscript.dynamic_label(doc, dt, dn, callback);
}

// Refresh
// --------
cur_frm.cscript.refresh = function(doc, dt, dn) {
	
	cur_frm.clear_custom_buttons();
	erpnext.hide_naming_series();

	if (!cur_frm.cscript.is_onload) cur_frm.cscript.dynamic_label(doc, dt, dn);


	// Show / Hide button
	if(doc.docstatus==1 && doc.outstanding_amount > 0)
		cur_frm.add_custom_button('Make Payment Entry', cur_frm.cscript.make_bank_voucher);
	
	if(doc.docstatus==1) { 
		cur_frm.add_custom_button('View Ledger', cur_frm.cscript.view_ledger_entry);
	}	
	cur_frm.cscript.is_opening(doc, dt, dn);
}


//Supplier
cur_frm.cscript.supplier = function(doc,dt,dn) {
	var callback = function(r,rt) {
			var doc = locals[cur_frm.doctype][cur_frm.docname];		
			get_server_fields('get_credit_to','','',doc, dt, dn, 0, callback2);
	}
	
	var callback2 = function(r,rt){
		var doc = locals[cur_frm.doctype][cur_frm.docname];
		var el = getchildren('Purchase Invoice Item',doc.name,'entries');
		for(var i in el){
			if(el[i].item_code && (!el[i].expense_head || !el[i].cost_center)){
				args = {
					item_code: el[i].item_code,
					expense_head: el[i].expense_head,
					cost_center: el[i].cost_center
				};
				get_server_fields('get_default_values', JSON.stringify(args), 'entries', doc, el[i].doctype, el[i].name, 1);
			}
		}
		cur_frm.cscript.calc_amount(doc, 1);
	}

	if (doc.supplier) {
		get_server_fields('get_default_supplier_address',
			JSON.stringify({ supplier: doc.supplier }),'', doc, dt, dn, 1, function(doc, dt, dn) {
				cur_frm.refresh();
				callback(doc, dt, dn);
			});
		unhide_field(['supplier_address','contact_person']);
	}

}

cur_frm.cscript.supplier_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {
	if(doc.supplier) get_server_fields('get_supplier_address', JSON.stringify({supplier: doc.supplier, address: doc.supplier_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}



cur_frm.fields_dict.supplier_address.on_new = function(dn) {
	locals['Address'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
	locals['Address'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}

cur_frm.fields_dict.contact_person.on_new = function(dn) {
	locals['Contact'][dn].supplier = locals[cur_frm.doctype][cur_frm.docname].supplier;
	locals['Contact'][dn].supplier_name = locals[cur_frm.doctype][cur_frm.docname].supplier_name;
}


cur_frm.cscript.credit_to = function(doc,dt,dn) {

	var callback = function(doc, dt, dn) {
			var doc = locals[doc.doctype][doc.name];
			if(doc.supplier) {
				get_server_fields('get_default_supplier_address',
					JSON.stringify({ supplier: doc.supplier }), '', doc, dt, dn, 1, function() {
						cur_frm.refresh();
					});
				unhide_field(['supplier_address','contact_person']);
			}
			cur_frm.refresh();
	}

	get_server_fields('get_cust', '', '', doc, dt, dn, 1, callback);
}



//Set expense_head and cost center on adding new row
//----------------------------------------------
cur_frm.fields_dict['entries'].grid.onrowadd = function(doc, cdt, cdn){
	
	cl = getchildren('Purchase Invoice Item', doc.name, cur_frm.cscript.fname, doc.doctype);
	acc = '';
	cc = '';

	for(var i = 0; i<cl.length; i++) {
		if (cl[i].idx == 1){
			acc = cl[i].expense_head;
			cc = cl[i].cost_center;
		}
		else{
			if (! cl[i].expense_head) { cl[i].expense_head = acc; refresh_field('expense_head', cl[i].name, 'entries');}
			if (! cl[i].cost_center)	{cl[i].cost_center = cc; refresh_field('cost_center', cl[i].name, 'entries');}
		}
	}
}

cur_frm.cscript.is_opening = function(doc, dt, dn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

cur_frm.cscript.write_off_amount = function(doc) {
	doc.total_amount_to_pay = flt(doc.grand_total) - flt(doc.ded_amount) - flt(doc.write_off_amount);
	doc.outstanding_amount = flt(doc.total_amount_to_pay) - flt(doc.total_advance);
	refresh_many(['outstanding_amount', 'total_amount_to_pay']);
}



// Recalculate Button
// -------------------
cur_frm.cscript.recalculate = function(doc, cdt, cdn) {
	cur_frm.cscript.calculate_tax(doc,cdt,cdn);
	calc_total_advance(doc,cdt,cdn);
}

// Get Items Button
// -----------------
cur_frm.cscript.get_items = function(doc, dt, dn) {
	var callback = function(r,rt) { 
		unhide_field(['supplier_address', 'contact_person']);				
		refresh_many(['credit_to','supplier','supplier_address','contact_person','supplier_name', 'address_display', 'contact_display','contact_mobile', 'contact_email','entries', 'purchase_receipt_main', 'purchase_order_main', 'purchase_tax_details']);
	}
	$c_obj(make_doclist(dt,dn),'pull_details','',callback);
}

// ========== Purchase Invoice Items Table ============

// Item Code
// ----------
cur_frm.cscript.item_code = function(doc,cdt,cdn){
	var d = locals[cdt][cdn];
	if(d.item_code){
		get_server_fields('get_item_details',d.item_code,'entries',doc,cdt,cdn,1);
	}
}

// Rate in Deduct Taxes (TDS)
// --------------------------
cur_frm.cscript.rate = function(doc,dt,dn) {
	//This is done as Purchase tax detail and PV detail both contain the same fieldname 'rate'
	if(dt != 'Purchase Taxes and Charges')	 cur_frm.cscript.calc_amount(doc, 2);
}

// Amount
// -------
cur_frm.cscript.ded_amount = function(doc,dt,dn) {calculate_outstanding(doc);}

// Get TDS Button
// ---------------
cur_frm.cscript.get_tds = function(doc, dt, dn) {
	var callback = function(r,rt) {
		cur_frm.refresh();
		refresh_field('ded_amount');
		//cur_frm.cscript.calc_total(locals[dt][dn]);
	}
	$c_obj(make_doclist(dt,dn), 'get_tds', '', callback);
}

// ===================== Advance Allocation ==================
cur_frm.cscript.allocated_amount = function(doc,cdt,cdn){
	var d = locals[cdt][cdn];
	if (d.allocated_amount && d.tds_amount){
		d.tds_allocated=flt(d.tds_amount*(d.allocated_amount/d.advance_amount))
		refresh_field('tds_allocated', d.name, 'advance_allocation_details');
	}
	tot_tds=0
	el = getchildren('Purchase Invoice Advance',doc.name,'advance_allocation_details')
	for(var i in el){
		tot_tds += el[i].tds_allocated
	}
	doc.tds_amount_on_advance = tot_tds
	refresh_field('tds_amount_on_advance');
	
	calc_total_advance(doc, cdt, cdn);
}


// Make Journal Voucher
// --------------------
cur_frm.cscript.make_bank_voucher = function() {
	$c('accounts.get_default_bank_account', { company: cur_frm.doc.company }, function(r, rt) {
		if(!r.exc) {
			cur_frm.cscript.make_jv(cur_frm.doc, null, null, r.message);
	}
	});
}


/* ***************************** GET QUERY Functions *************************** */


cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,address_line1,city FROM tabAddress WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

// Item Code
// ----------
cur_frm.fields_dict['entries'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	return 'SELECT tabItem.name, tabItem.description FROM tabItem WHERE tabItem.is_purchase_item="Yes" AND (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` ="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND tabItem.docstatus != 2 AND tabItem.%(key)s LIKE "%s" LIMIT 50'
}

// Credit To
// ----------
cur_frm.fields_dict['credit_to'].get_query = function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Credit" AND tabAccount.is_pl_account="No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}


// Purchase Order
// ---------------
cur_frm.fields_dict['purchase_order_main'].get_query = function(doc) {
	if (doc.supplier){
		return 'SELECT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 AND `tabPurchase Order`.supplier = "'+ doc.supplier +'" AND `tabPurchase Order`.`status` != "Stopped" AND ifnull(`tabPurchase Order`.`per_billed`,0) < 100 AND `tabPurchase Order`.`company` = "' + doc.company + '" AND `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50'
	} else {
		return 'SELECT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 AND `tabPurchase Order`.`status` != "Stopped" AND ifnull(`tabPurchase Order`.`per_billed`, 0) < 100 AND `tabPurchase Order`.`company` = "' + doc.company + '" AND `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50'
	}
}

// Purchase Receipt
// -----------------
cur_frm.fields_dict['purchase_receipt_main'].get_query = function(doc) {
	if (doc.supplier){
		return 'SELECT `tabPurchase Receipt`.`name` FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.`docstatus` = 1 AND `tabPurchase Receipt`.supplier = "'+ doc.supplier +'" AND `tabPurchase Receipt`.`status` != "Stopped" AND ifnull(`tabPurchase Receipt`.`per_billed`, 0) < 100 AND `tabPurchase Receipt`.`company` = "' + doc.company + '" AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.`name` DESC LIMIT 50'
	} else {
		return 'SELECT `tabPurchase Receipt`.`name` FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.`docstatus` = 1 AND `tabPurchase Receipt`.`status` != "Stopped" AND ifnull(`tabPurchase Receipt`.`per_billed`, 0) < 100 AND `tabPurchase Receipt`.`company` = "' + doc.company + '" AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.`name` DESC LIMIT 50'
	}
}

// Get Print Heading
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}


// ================== Purchase Invoice Items Table ===================
// Expense Head
// -------------
cur_frm.fields_dict['entries'].grid.get_field("expense_head").get_query = function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE (tabAccount.debit_or_credit="Debit" OR tabAccount.account_type = "Expense Account") AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"';
}
cur_frm.cscript.expense_head = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.expense_head){
		var cl = getchildren('Purchase Invoice Item', doc.name, 'entries', doc.doctype);
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].expense_head) cl[i].expense_head = d.expense_head;
		}
	}
	refresh_field('entries');
}


// Cost Center
//-------------
cur_frm.fields_dict['entries'].grid.get_field("cost_center").get_query = function(doc) {
	return 'SELECT `tabCost Center`.`name` FROM `tabCost Center` WHERE `tabCost Center`.`company_name` = "' +doc.company+'" AND `tabCost Center`.%(key)s LIKE "%s" AND `tabCost Center`.`group_or_ledger` = "Ledger" AND `tabCost Center`.docstatus != 2 ORDER BY	`tabCost Center`.`name` ASC LIMIT 50';
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.cost_center){
		var cl = getchildren('Purchase Invoice Item', doc.name, 'entries', doc.doctype);
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
		}
	}
	refresh_field('entries');
}


// TDS Account Head
cur_frm.fields_dict['tax_code'].get_query = function(doc) {
	return "SELECT `tabTDS Category Account`.account_head FROM `tabTDS Category Account` WHERE `tabTDS Category Account`.parent = '"+doc.tds_category+"' AND `tabTDS Category Account`.company='"+doc.company+"' AND `tabTDS Category Account`.account_head LIKE '%s' ORDER BY `tabTDS Category Account`.account_head DESC LIMIT 50";
}

cur_frm.cscript.tax_code = function(doc, dt, dn) {
	get_server_fields('get_tds_rate','','',doc, dt, dn, 0);
}

/* ***************************** UTILITY FUNCTIONS ************************ */
// Calculate Advance
// ------------------
calc_total_advance = function(doc,cdt,cdn) {
	var doc = locals[doc.doctype][doc.name];
	var el = getchildren('Purchase Invoice Advance',doc.name,'advance_allocation_details')
	var tot_tds=0;
	var total_advance = 0;
	for(var i in el) {
		if (! el[i].allocated_amount == 0) {
			total_advance += flt(el[i].allocated_amount);
			tot_tds += flt(el[i].tds_allocated)
		}
	}
	doc.total_amount_to_pay = flt(doc.grand_total) - flt(doc.ded_amount) - flt(doc.write_off_amount);
	doc.tds_amount_on_advance = flt(tot_tds);
	doc.total_advance = flt(total_advance);
	doc.outstanding_amount = flt(doc.total_amount_to_pay) - flt(total_advance);
	refresh_many(['total_advance','outstanding_amount','tds_amount_on_advance', 'total_amount_to_pay']);
}

// Make JV
// --------
cur_frm.cscript.make_jv = function(doc, dt, dn, bank_account) {
	var jv = LocalDB.create('Journal Voucher');
	jv = locals['Journal Voucher'][jv];
	jv.voucher_type = 'Bank Voucher';
	jv.remark = repl('Payment against voucher %(vn)s for %(rem)s', {vn:doc.name, rem:doc.remarks});
	jv.total_debit = doc.outstanding_amount;
	jv.total_credit = doc.outstanding_amount;
	jv.fiscal_year = doc.fiscal_year;
	jv.company = doc.company;
	
	// debit to creditor
	var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = doc.credit_to;
	d1.debit = doc.outstanding_amount;
	d1.against_voucher = doc.name;
	
	// credit to bank
	var d1 = LocalDB.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = bank_account;
	d1.credit = doc.outstanding_amount;
	
	loaddoc('Journal Voucher', jv.name);
}

// ***************** Get project name *****************
cur_frm.fields_dict['entries'].grid.get_field('project_name').get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.status = "Open" AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}


cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Purchase Invoice";
}

/****************** Get Accounting Entry *****************/
cur_frm.cscript.view_ledger_entry = function(){
	wn.set_route('Report', 'GL Entry', 'General Ledger', 'Voucher No='+cur_frm.doc.name);
}
