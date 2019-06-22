// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const ALL_TABLES = ['exchange_rates', 'sales_invoices', 'purchase_invoices', 'received_payments', 'paid_payments'];

frappe.ui.form.on('Adjustment Entry', {
	onload: function(frm) {
		ALL_TABLES.forEach(function (field) {
			frm.set_df_property(field, "cannot_add_rows", 1);
		});
		frm.trigger("set_customer_supplier_required");
	},
	refresh: function(frm) {

	},
	company: function(frm) {
		frm.trigger("clear_all_tables");
		// TODO: Change labels on table columns
	},
	customer: function(frm) {
		frm.trigger("clear_all_tables");
	},
	supplier: function(frm) {
		frm.trigger("clear_all_tables");
	},
	adjustment_type: function(frm) {
		frm.trigger("set_customer_supplier_required");
		frm.trigger("clear_all_tables");
	},
	payment_currency: function(frm) {
		// TODO: Change labels on table columns
	},
	get_unreconciled_entries: function(frm) {
		if(!frm.doc.company || !frm.doc.adjustment_type || (frm.doc.adjustment_type !== 'Purchase' && !frm.doc.customer) || (frm.doc.adjustment_type !== 'Sales' && !frm.doc.supplier)) {
			frappe.throw("Please enter the required fields first");
		}
    	frm.fields_dict.get_unreconciled_entries.$input.removeClass('btn-primary');
  	},
	set_customer_supplier_required: function(frm) {
		if(frm.doc.adjustment_type === 'Sales') {
			frm.set_df_property("customer", "reqd", 1);
			frm.set_df_property("supplier", "reqd", 0);
			frm.set_value("supplier", null);
		} else if(frm.doc.adjustment_type === 'Purchase') {
			frm.set_df_property("customer", "reqd", 0);
			frm.set_df_property("supplier", "reqd", 1);
			frm.set_value("customer", null);
		} else {
			frm.set_df_property("customer", "reqd", 1);
			frm.set_df_property("supplier", "reqd", 1);
		}
	},
	clear_all_tables: function(frm) {
		ALL_TABLES.forEach(function (field) {
			frm.set_value(field, []);
		});
		frm.set_df_property('deduction_section_break', 'hidden', 1);
		frm.set_df_property('deductions', 'hidden', 1);
		frm.fields_dict.get_unreconciled_entries.$input.addClass('btn-primary');
	}
});
