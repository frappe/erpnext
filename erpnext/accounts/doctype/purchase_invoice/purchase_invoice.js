// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tname = "Purchase Invoice Item";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "other_charges";

frappe.provide("erpnext.accounts");
{% include 'buying/doctype/purchase_common/purchase_common.js' %};
{% include 'accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js' %}
{% include 'accounts/doctype/sales_invoice/pos.js' %}

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
			this.frm.add_custom_button(__('Make Payment Entry'), this.make_bank_voucher,
				frappe.boot.doctype_icons["Journal Voucher"]);

		if(doc.docstatus==1) {
			cur_frm.appframe.add_button(__('View Ledger'), function() {
				frappe.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
					"company": doc.company,
					group_by_voucher: 0
				};
				frappe.set_route("query-report", "General Ledger");
			}, "icon-table");
		}

		if(doc.docstatus===0) {
			cur_frm.add_custom_button(__('From Purchase Order'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
						source_doctype: "Purchase Order",
						get_query_filters: {
							supplier: cur_frm.doc.supplier || undefined,
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_billed: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");

			cur_frm.add_custom_button(__('From Purchase Receipt'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
						source_doctype: "Purchase Receipt",
						get_query_filters: {
							supplier: cur_frm.doc.supplier || undefined,
							docstatus: 1,
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");

		}

		this.is_opening(doc);
	},

	supplier: function() {
		var me = this;
		if(this.frm.updating_party_details)
			return;
		erpnext.utils.get_party_details(this.frm, "erpnext.accounts.party.get_party_details",
			{
				posting_date: this.frm.doc.posting_date,
				party: this.frm.doc.supplier,
				party_type: "Supplier",
				account: this.frm.doc.debit_to,
				price_list: this.frm.doc.buying_price_list,
			}, function() {
			me.apply_pricing_rule();
		})
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
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("entries", row,
			["expense_account", "cost_center", "project_name"]);
	},

	on_submit: function() {
		$.each(this.frm.doc["entries"], function(i, row) {
			if(row.purchase_receipt) frappe.model.clear_doc("Purchase Receipt", row.purchase_receipt)
		})
	}
});

cur_frm.script_manager.make(erpnext.accounts.PurchaseInvoice);

cur_frm.cscript.is_opening = function(doc, dt, dn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

cur_frm.cscript.make_bank_voucher = function() {
	return frappe.call({
		method: "erpnext.accounts.doctype.journal_voucher.journal_voucher.get_payment_entry_from_purchase_invoice",
		args: {
			"purchase_invoice": cur_frm.doc.name,
		},
		callback: function(r) {
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
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
		query: "erpnext.controllers.queries.item_query",
		filters:{
			'is_purchase_item': 'Yes'
		}
	}
}

cur_frm.fields_dict['credit_to'].get_query = function(doc) {
	return{
		filters:{
			'report_type': 'Balance Sheet',
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

cur_frm.set_query("expense_account", "entries", function(doc) {
	return{
		query: "erpnext.accounts.doctype.purchase_invoice.purchase_invoice.get_expense_account",
		filters: {'company': doc.company}
	}
});

cur_frm.cscript.expense_account = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.expense_account){
		var cl = doc.entries || [];
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].expense_account) cl[i].expense_account = d.expense_account;
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
		var cl = doc.entries || [];
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
		}
	}
	refresh_field('entries');
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
		cur_frm.pformat.print_heading = __("Purchase Invoice");
}
