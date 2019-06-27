// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

const ALL_TABLES = ['exchange_rates', 'credit_entries', 'debit_entries'];

erpnext.accounts.AdjustmentEntryController = frappe.ui.form.Controller.extend({

	onload: function() {
		const me = this;
		ALL_TABLES.forEach(function (field) {
			me.frm.set_df_property(field, "cannot_add_rows", 1);
		});
		this.set_customer_supplier_required();
	},

	get_unreconciled_entries: function() {
		var me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_unreconciled_entries',
			callback: function(r, rt) {
				me.frm.fields_dict.get_unreconciled_entries.$input.removeClass('btn-primary');
			}
		});
  	},

	refresh: function() {

	},
	company: function() {
		this.clear_all_tables();
		// TODO: Change labels on table columns
	},
	customer: function() {
		this.clear_all_tables();
	},
	supplier: function() {
		this.clear_all_tables();
	},
	adjustment_type: function() {
		this.set_customer_supplier_required();
		this.clear_all_tables();
	},
	payment_currency: function() {
		// TODO: Change labels on table columns
		const me = this;
		return this.frm.call({
			doc: me.frm.doc,
			freeze: true,
			method: 'recalculate_all'
		});
	},

	allocate_payment_amount: function() {
		const me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'allocate_amount_to_references'
		});
	},

	clear_all_tables: function() {
		const me = this;
		ALL_TABLES.forEach(function (field) {
			me.frm.set_value(field, []);
		});
		this.frm.fields_dict.get_unreconciled_entries.$input.addClass('btn-primary');
	},

	set_customer_supplier_required: function() {
		const frm = this.frm;
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
});

frappe.ui.form.on('Adjustment Entry Reference', {
	allocated_amount: function(frm, cdt, cdn) {
		const data = locals[cdt][cdn];
		const exchange_rates = frm.doc.exchange_rates;
		const base_exchange_rate = exchange_rates.find(exchg_rate => exchg_rate.currency === frm.doc.payment_currency).exchange_rate_to_base_currency;
		const balance = data.voucher_payment_amount - data.allocated_amount;
		const allocated_base_amount = data.allocated_amount * base_exchange_rate;
		frappe.model.set_value(cdt, cdn, 'balance', balance);
		frappe.model.set_value(cdt, cdn, 'allocated_base_amount', allocated_base_amount);
	}
});

frappe.ui.form.on('Adjustment Entry Exchange Rates', {
	exchange_rate_to_payment_currency: function(frm) {
		frm.call({
			doc: frm.doc,
			method: 'recalculate_references',
			args: {
				reference_types: ['debit_entries', 'credit_entries']
			}
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.accounts.AdjustmentEntryController({frm: cur_frm}));