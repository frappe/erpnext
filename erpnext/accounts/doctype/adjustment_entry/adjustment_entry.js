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
		const me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_unreconciled_entries',
			callback: function() {
				me.frm.fields_dict.get_unreconciled_entries.$input.removeClass('btn-primary');
			}
		});
  	},

	refresh: function() {

	},
	company: function() {
		this.clear_all_tables();
		this.update_labels();
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
		this.update_labels();
		const me = this;
		return this.frm.call({
			doc: me.frm.doc,
			freeze: true,
			method: 'recalculate_tables'
		});
	},

	update_labels: function () {
		const company_currency = frappe.get_doc(":Company", this.frm.doc.company).default_currency;
		['debit_entries', 'credit_entries'].map(reference_type => {
			this.frm.set_currency_labels(['voucher_payment_amount', 'payment_exchange_rate', 'allocated_amount', 'balance'], this.frm.doc.payment_currency, reference_type);
			this.frm.set_currency_labels(['voucher_base_amount', 'allocated_base_amount', 'gain_loss_amount'], company_currency, reference_type);
			this.frm.get_field(reference_type).grid.header_row.refresh();
		});
		this.frm.set_currency_labels(['exchange_rate_to_base_currency'],company_currency, 'exchange_rates');
		this.frm.set_currency_labels(['exchange_rate_to_payment_currency'],this.frm.doc.payment_currency, 'exchange_rates');
		this.frm.get_field('exchange_rates').grid.header_row.refresh();
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
		const allocated_amount_in_entry_currency = data.allocated_amount / data.payment_exchange_rate;
		const gain_loss_amount = data.allocated_base_amount - allocated_amount_in_entry_currency * data.exchange_rate;
		frappe.model.set_value(cdt, cdn, 'gain_loss_amount', gain_loss_amount);
	}
});

function call_recalculate_references(frm) {
	return frm.call({
		doc: frm.doc,
		method: 'recalculate_references',
		args: {
			reference_types: ['debit_entries', 'credit_entries']
		}
	});
}

frappe.ui.form.on('Adjustment Entry Exchange Rates', {
	exchange_rate_to_payment_currency: call_recalculate_references ,
	exchange_rate_to_base_currency: call_recalculate_references,
});

$.extend(cur_frm.cscript, new erpnext.accounts.AdjustmentEntryController({frm: cur_frm}));