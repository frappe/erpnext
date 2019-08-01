// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

const ALL_TABLES = ['exchange_rates', 'credit_entries', 'debit_entries'];

erpnext.accounts.AdjustmentEntryController = frappe.ui.form.Controller.extend({

	setup: function() {
		const frm = this.frm;
		frm.set_query("cost_center", function() {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.company
				}
			};
		});
		const voucher_type_query = function() {
			return {
				filters: { "name": ["in", ["Sales Invoice", "Purchase Invoice"]] }
			};
		};
		frm.set_query("voucher_type", "debit_entries", voucher_type_query);
		frm.set_query("voucher_type", "credit_entries", voucher_type_query);

		const voucher_number_query = function(doc, cdt, cdn) {
			const child = locals[cdt][cdn];
			const filters = [[child.voucher_type, "docstatus", "=", 1], [child.voucher_type, "company", "=", doc.company]];
			if(child.parentfield === 'debit_entries') {
				if(child.voucher_type === 'Purchase Invoice') {
					filters.push([child.voucher_type, "supplier", "=", doc.supplier]);
					filters.push([child.voucher_type, "outstanding_amount", "<",0]);
				} else {
					filters.push([child.voucher_type, "customer", "=", doc.customer]);
					filters.push([child.voucher_type, "outstanding_amount", ">",0]);
				}
			} else {
				if(child.voucher_type === 'Sales Invoice') {
					filters.push([child.voucher_type, "customer", "=", doc.customer]);
					filters.push([child.voucher_type, "outstanding_amount", "<",0]);
				} else {
					filters.push([child.voucher_type, "supplier", "=", doc.supplier]);
					filters.push([child.voucher_type, "outstanding_amount", ">",0]);
				}
			}
			return {
				filters: filters
			};
		};
		frm.set_query("voucher_number", "debit_entries", voucher_number_query);
		frm.set_query("voucher_number", "credit_entries", voucher_number_query);
	},

	onload: function() {
		this.frm.set_df_property("exchange_rates", "cannot_add_rows", 1);
		this.update_labels();
	},

	cost_center: function(){
		this.get_unreconciled_entries();
	},

	get_unreconciled_entries: function() {
		const me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'get_unreconciled_entries',
			freeze: true,
			callback: function() {
				me.frm.fields_dict.get_unreconciled_entries.$input.removeClass('btn-primary');
			}
		});
	},

	refresh: function() {
		this.show_general_ledger();
	},

	show_general_ledger: function() {
		const frm = this.frm;
		if(frm.doc.docstatus===1) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": frm.doc.posting_date,
					"company": frm.doc.company,
					group_by: ""
				};
				frappe.set_route("query-report", "General Ledger");
			}, "fa fa-table");
		}
	},

	company: function() {
		this.clear_all_tables();
		this.update_labels();
		const me = this;
		this.frm.call({
			doc: me.frm.doc,
			method: 'validate_company_exchange_gain_loss_account'
		});
	},

	customer: function() {
		this.clear_all_tables();
		this.set_account_details(this.frm.doc.customer, 'Customer');
	},
	supplier: function() {
		this.clear_all_tables();
		this.set_account_details(this.frm.doc.supplier, 'Supplier');
	},

	set_account_details: function(party, party_type) {
		const me = this;
		return this.frm.call({
			doc: me.frm.doc,
			method: 'set_party_account_details',
			args: {
				party,
				party_type
			}
		});
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

});

function get_exchange_rate(frm, from_currency, exchange_rate_field) {
	const exchange_rates = frm.doc.exchange_rates;
	const exchange_rate = exchange_rates.find(exchg_rate => exchg_rate.currency === from_currency);
	return exchange_rate ? exchange_rate[exchange_rate_field] : 1;
}

function call_calculate_summary(frm) {
	return frm.call({
		doc: frm.doc,
		method: 'calculate_summary_totals'
	});
}

frappe.ui.form.on('Adjustment Entry Reference', {
	credit_entries_remove: call_calculate_summary,

	debit_entries_remove: call_calculate_summary,

	voucher_number: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.voucher_number && row.voucher_type) {
			return frm.call({
				doc: frm.doc,
				method: "add_reference_doc_details",
				args: {
					reference_type: row.parentfield,
					voucher_type:  row.voucher_type,
					voucher_number: row.voucher_number
				}
			});
		}
	},

	allocated_amount: function(frm, cdt, cdn) {
		const data = locals[cdt][cdn];
		const base_exchange_rate = get_exchange_rate(frm, frm.doc.payment_currency, 'exchange_rate_to_base_currency');
		const balance = data.voucher_payment_amount - data.allocated_amount;
		const allocated_base_amount = data.allocated_amount * base_exchange_rate;
		frappe.model.set_value(cdt, cdn, 'balance', flt(balance));
		frappe.model.set_value(cdt, cdn, 'allocated_base_amount', flt(allocated_base_amount));
		const allocated_amount_in_entry_currency = data.allocated_amount / data.payment_exchange_rate;
		const gain_loss_amount = data.allocated_base_amount - allocated_amount_in_entry_currency * data.exchange_rate;
		const final_gain_loss_amount = data.parentfield === 'debit_entries' ? flt(gain_loss_amount) : flt(gain_loss_amount * -1);
		frappe.model.set_value(cdt, cdn, 'gain_loss_amount', final_gain_loss_amount);
		frm.call({
			doc: frm.doc,
			method: 'calculate_summary_totals'
		});
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
	exchange_rate_to_base_currency: function (frm) {
		call_recalculate_references(frm);
	},
});

frappe.ui.form.on('Adjustment Entry Deduction', {
	amount: function (frm, cdt, cdn) {
		const data = locals[cdt][cdn];
		const base_exchange_rate = get_exchange_rate(frm, frm.doc.payment_currency, 'exchange_rate_to_base_currency');
		const base_amount = data.amount * base_exchange_rate;
		frappe.model.set_value(cdt, cdn, 'base_amount', base_amount);
		frm.call({
			doc: frm.doc,
			method: 'calculate_summary_totals'
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.accounts.AdjustmentEntryController({frm: cur_frm}));