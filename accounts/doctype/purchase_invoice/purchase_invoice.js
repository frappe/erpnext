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

erpnext.accounts.PurchaseInvoice = erpnext.buying.BuyingController.extend({
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
			cur_frm.add_custom_button('View Ledger', function() {
				wn.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
				};
				wn.set_route("general-ledger");
			});
		}

		if(doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Purchase Order'), 
				function() {
					wn.model.map_current_doc({
						method: "buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
						source_doctype: "Purchase Order",
						get_query_filters: {
							supplier: cur_frm.doc.supplier || undefined,
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_billed: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				});

			cur_frm.add_custom_button(wn._('From Purchase Receipt'), 
				function() {
					wn.model.map_current_doc({
						method: "stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
						source_doctype: "Purchase Receipt",
						get_query_filters: {
							supplier: cur_frm.doc.supplier || undefined,
							docstatus: 1,
							company: cur_frm.doc.company
						}
					})
				});	
			
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
	}, 

	tc_name: function() {
		this.get_terms();
	},
	
	entries_add: function(doc, cdt, cdn) {
		var row = wn.model.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("entries", row, ["expense_head", "cost_center"]);
	}
});

cur_frm.script_manager.make(erpnext.accounts.PurchaseInvoice);

cur_frm.cscript.is_opening = function(doc, dt, dn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
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
	return{
		filters:{'supplier':  doc.supplier}
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'supplier':  doc.supplier}
	}	
}

cur_frm.fields_dict['entries'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	return {
		query:"controllers.queries.item_query",
		filters:{
			'is_purchase_item': 'Yes'	
		}
	}	 
}

cur_frm.fields_dict['credit_to'].get_query = function(doc) {
	return{
		filters:{
			'debit_or_credit': 'Credit',
			'is_pl_account': 'No',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
}

// Get Print Heading
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
return{
		filters:[
			['Print Heading', 'docstatus', '!=', 2]
		]
	}	
}

cur_frm.fields_dict['entries'].grid.get_field("expense_head").get_query = function(doc) {
	return{
		filters:{
			'debit_or_credit':'Debit',
			'account_type': 'Expense Account',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
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
		filters: { 
			'company': doc.company,
			'group_or_ledger': 'Ledger'
		}

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
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}	
}


cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Purchase Invoice";
}