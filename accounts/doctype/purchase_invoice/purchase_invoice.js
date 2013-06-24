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

wn.provide("erpnext.accounts");
wn.require('app/accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js');
wn.require('app/buying/doctype/purchase_common/purchase_common.js');

erpnext.accounts.PurchaseInvoiceController = erpnext.buying.BuyingController.extend({
	onload: function() {
		this._super();
		
		if(!this.frm.doc.__islocal) {
			// show credit_to in print format
			if(!this.frm.doc.supplier && this.frm.doc.credit_to) {
				this.frm.set_df_property("credit_to", "print_hide", 0);
			}
		}
	},
	
	refresh: function(doc) {
		this._super();
		
		// Show / Hide button
		if(doc.docstatus==1 && doc.outstanding_amount > 0)
			this.frm.add_custom_button('Make Payment Entry', this.make_bank_voucher);

		if(doc.docstatus==1) { 
			this.frm.add_custom_button('View Ledger', this.view_ledger_entry);
		}
		
		this.is_opening(doc);
	},
	
	credit_to: function() {
		this.supplier();
	},
	
	write_off_amount: function() {
		this.calculate_outstanding_amount();
		this.frm.refresh_fields();
	},
	
	allocated_amount: function() {
		this.calculate_total_advance("Purchase Invoice", "advance_allocation_details");
		this.frm.refresh_fields();
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.PurchaseInvoiceController({frm: cur_frm}));


cur_frm.cscript.supplier_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {
	if(doc.supplier) get_server_fields('get_supplier_address', JSON.stringify({supplier: doc.supplier, address: doc.supplier_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

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

cur_frm.cscript.get_items = function(doc, dt, dn) {
	var callback = function(r,rt) { 
		unhide_field(['supplier_address', 'contact_person']);				
		cur_frm.refresh_fields();
	}
	$c_obj(make_doclist(dt,dn),'pull_details','',callback);
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


cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,address_line1,city FROM tabAddress WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation FROM tabContact WHERE supplier = "'+ doc.supplier +'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['entries'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	return erpnext.queries.item({
		'ifnull(tabItem.is_purchase_item, "No")': 'Yes'
	})
}

cur_frm.fields_dict['credit_to'].get_query = function(doc) {
	return 'SELECT tabAccount.name FROM tabAccount WHERE tabAccount.debit_or_credit="Credit" AND tabAccount.is_pl_account="No" AND tabAccount.group_or_ledger="Ledger" AND tabAccount.docstatus != 2 AND tabAccount.company="'+doc.company+'" AND tabAccount.%(key)s LIKE "%s"'
}

cur_frm.fields_dict['purchase_order_main'].get_query = function(doc) {
	if (doc.supplier){
		return 'SELECT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 AND `tabPurchase Order`.supplier = "'+ doc.supplier +'" AND `tabPurchase Order`.`status` != "Stopped" AND ifnull(`tabPurchase Order`.`per_billed`,0) < 99.99 AND `tabPurchase Order`.`company` = "' + doc.company + '" AND `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50'
	} else {
		return 'SELECT `tabPurchase Order`.`name` FROM `tabPurchase Order` WHERE `tabPurchase Order`.`docstatus` = 1 AND `tabPurchase Order`.`status` != "Stopped" AND ifnull(`tabPurchase Order`.`per_billed`, 0) < 99.99 AND `tabPurchase Order`.`company` = "' + doc.company + '" AND `tabPurchase Order`.%(key)s LIKE "%s" ORDER BY `tabPurchase Order`.`name` DESC LIMIT 50'
	}
}

cur_frm.fields_dict['purchase_receipt_main'].get_query = function(doc) {
	if (doc.supplier){
		return 'SELECT `tabPurchase Receipt`.`name` FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.`docstatus` = 1 AND `tabPurchase Receipt`.supplier = "'+ doc.supplier +'" AND `tabPurchase Receipt`.`status` != "Stopped" AND ifnull(`tabPurchase Receipt`.`per_billed`, 0) < 99.99 AND `tabPurchase Receipt`.`company` = "' + doc.company + '" AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.`name` DESC LIMIT 50'
	} else {
		return 'SELECT `tabPurchase Receipt`.`name` FROM `tabPurchase Receipt` WHERE `tabPurchase Receipt`.`docstatus` = 1 AND `tabPurchase Receipt`.`status` != "Stopped" AND ifnull(`tabPurchase Receipt`.`per_billed`, 0) < 99.99 AND `tabPurchase Receipt`.`company` = "' + doc.company + '" AND `tabPurchase Receipt`.%(key)s LIKE "%s" ORDER BY `tabPurchase Receipt`.`name` DESC LIMIT 50'
	}
}

// Get Print Heading
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabPrint Heading`.name FROM `tabPrint Heading` WHERE `tabPrint Heading`.docstatus !=2 AND `tabPrint Heading`.name LIKE "%s" ORDER BY `tabPrint Heading`.name ASC LIMIT 50';
}

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

cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		query: "accounts.utils.get_cost_center_list",
		filters: { company_name: doc.company}
	}
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

cur_frm.cscript.make_jv = function(doc, dt, dn, bank_account) {
	var jv = wn.model.make_new_doc_and_get_name('Journal Voucher');
	jv = locals['Journal Voucher'][jv];
	jv.voucher_type = 'Bank Voucher';
	jv.remark = repl('Payment against voucher %(vn)s for %(rem)s', {vn:doc.name, rem:doc.remarks});
	jv.total_debit = doc.outstanding_amount;
	jv.total_credit = doc.outstanding_amount;
	jv.fiscal_year = doc.fiscal_year;
	jv.company = doc.company;
	
	// debit to creditor
	var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = doc.credit_to;
	d1.debit = doc.outstanding_amount;
	d1.against_voucher = doc.name;
	
	// credit to bank
	var d1 = wn.model.add_child(jv, 'Journal Voucher Detail', 'entries');
	d1.account = bank_account.account;
	d1.credit = doc.outstanding_amount;
	d1.balance = bank_account.balance;
	
	loaddoc('Journal Voucher', jv.name);
}

cur_frm.fields_dict['entries'].grid.get_field('project_name').get_query = function(doc, cdt, cdn) {
	return 'SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}


cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Purchase Invoice";
}

cur_frm.cscript.view_ledger_entry = function(){
	wn.set_route('Report', 'GL Entry', 'General Ledger', 'Voucher No='+cur_frm.doc.name);
}
