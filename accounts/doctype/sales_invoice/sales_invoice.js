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

wn.require('app/accounts/doctype/sales_taxes_and_charges_master/sales_taxes_and_charges_master.js');
wn.require('app/utilities/doctype/sms_control/sms_control.js');
wn.require('app/selling/doctype/sales_common/sales_common.js');

wn.provide("erpnext.accounts");
erpnext.accounts.SalesInvoiceController = erpnext.selling.SellingController.extend({
	onload: function() {
		this._super();
		
		if(!this.frm.doc.__islocal) {
			// show debit_to in print format
			if(!this.frm.doc.customer && this.frm.doc.debit_to) {
				this.frm.set_df_property("debit_to", "print_hide", 0);
			}
		}
	},
	
	refresh: function(doc, dt, dn) {
		this._super();
		
		cur_frm.cscript.is_opening(doc, dt, dn);
		cur_frm.dashboard.reset();

		if(doc.docstatus==1) {
			cur_frm.add_custom_button('View Ledger', function() {
				wn.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
				};
				wn.set_route("general-ledger");
			});
			
			var percent_paid = cint(flt(doc.grand_total - doc.outstanding_amount) / flt(doc.grand_total) * 100);
			cur_frm.dashboard.add_progress(percent_paid + "% Paid", percent_paid);

			cur_frm.add_custom_button('Send SMS', cur_frm.cscript.send_sms);

			if(doc.is_pos==1 && doc.update_stock!=1)
				cur_frm.add_custom_button('Make Delivery', cur_frm.cscript['Make Delivery Note']);

			if(doc.outstanding_amount!=0)
				cur_frm.add_custom_button('Make Payment Entry', cur_frm.cscript.make_bank_voucher);
		}

		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Sales Order'), 
				function() {
					wn.model.map_current_doc({
						method: "selling.doctype.sales_order.sales_order.make_sales_invoice",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_billed: ["<", 99.99],
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});

			cur_frm.add_custom_button(wn._('From Delivery Note'), 
				function() {
					wn.model.map_current_doc({
						method: "stock.doctype.delivery_note.delivery_note.make_sales_invoice",
						source_doctype: "Delivery Note",
						get_query_filters: {
							docstatus: 1,
							customer: cur_frm.doc.customer || undefined,
							company: cur_frm.doc.company
						}
					})
				});

		}
		
		cur_frm.cscript.hide_fields(doc, dt, dn);
	},

	tc_name: function() {
		this.get_terms();
	},
	
	is_pos: function() {
		if(cint(this.frm.doc.is_pos)) {
			if(!this.frm.doc.company) {
				this.frm.set_value("is_pos", 0);
				msgprint(wn._("Please specify Company to proceed"));
			} else {
				var me = this;
				this.frm.call({
					doc: me.frm.doc,
					method: "set_missing_values",
				});
			}
		}
		
		// TODO toggle display of fields
	},
	
	debit_to: function() {
		this.customer();
	},
	
	allocated_amount: function() {
		this.calculate_total_advance("Sales Invoice", "advance_adjustment_details");
		this.frm.refresh_fields();
	},
	
	write_off_outstanding_amount_automatically: function() {
		if(cint(this.frm.doc.write_off_outstanding_amount_automatically)) {
			wn.model.round_floats_in(this.frm.doc, ["grand_total", "paid_amount"]);
			// this will make outstanding amount 0
			this.frm.set_value("write_off_amount", 
				flt(this.frm.doc.grand_total - this.frm.doc.paid_amount), precision("write_off_amount"));
		}
		
		this.frm.runclientscript("write_off_amount");
	},
	
	write_off_amount: function() {
		this.calculate_outstanding_amount();
		this.frm.refresh_fields();
	},
	
	paid_amount: function() {
		this.write_off_outstanding_amount_automatically();
	},
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({frm: cur_frm}));

// Hide Fields
// ------------
cur_frm.cscript.hide_fields = function(doc, cdt, cdn) {
	par_flds = ['project_name', 'due_date', 'is_opening', 'conversion_rate',
	'source', 'total_advance', 'gross_profit',
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
	} else {
		hide_field('payments_section');
		unhide_field(par_flds);
		for(f in item_flds_normal) cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_normal[f], true);
	}
	for(f in item_flds_pos) cur_frm.fields_dict['entries'].grid.set_column_disp(item_flds_pos[f], (cint(doc.update_stock)==1?true:false));

	// India related fields
	var cp = wn.control_panel;
	if (cp.country == 'India') unhide_field(['c_form_applicable', 'c_form_no']);
	else hide_field(['c_form_applicable', 'c_form_no']);
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

//Make Delivery Note Button
//-----------------------------

cur_frm.cscript['Make Delivery Note'] = function() {
	wn.model.open_mapped_doc({
		method: "accounts.doctype.sales_invoice.sales_invoice.make_delivery_note",
		source_name: cur_frm.doc.name
	})
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
	return{
		filters: {
			'debit_or_credit': 'Debit',
			'is_pl_account': 'No',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}
}

cur_frm.fields_dict.cash_bank_account.get_query = function(doc) {
	return{
		filters: {
			'debit_or_credit': 'Debit',
			'is_pl_account': 'No',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
}

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return{
		filters:{
			'debit_or_credit': 'Debit',
			'is_pl_account': 'Yes',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return{
		filters:{
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
}

//project name
//--------------------------
cur_frm.fields_dict['project_name'].get_query = function(doc, cdt, cdn) {
	return{
		query: "controllers.queries.get_project_name",
		filters: {'customer': doc.customer}
	}	
}

//Territory
//-----------------------------
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return{
		filters: {'is_group': 'NO'}
	}	
}

// Income Account in Details Table
// --------------------------------
cur_frm.set_query("income_account", "entries", function(doc) {
	return{
		query: "accounts.doctype.sales_invoice.sales_invoice.get_income_account",
		filters: {'company': doc.company}
	}
});

// expense account
if (sys_defaults.auto_inventory_accounting) {
	cur_frm.fields_dict['entries'].grid.get_field('expense_account').get_query = function(doc) {
		return {
			filters: {
				'is_pl_account': 'Yes',
				'debit_or_credit': 'Debit',
				'company': doc.company,
				'group_or_ledger': 'Ledger'
			}
		}
	}
}

// warehouse in detail table
//----------------------------
cur_frm.fields_dict['entries'].grid.get_field('warehouse').get_query= function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return{
		filters:[
			['Bin', 'item_code', '=', d.item_code],
			['Bin', 'actual_qty', '>', 0]
		]
	}	
}

// Cost Center in Details Table
// -----------------------------
cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: { 
			'company': doc.company,
			'group_or_ledger': 'Ledger'
		}	
	}
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
