// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Flow Mapping', {
	refresh: function(frm) {
		frm.events.disable_unchecked_fields(frm);
	},
	reset_check_fields: function(frm) {
		frm.fields.filter(field => field.df.fieldtype === 'Check')
			.map(field => frm.set_df_property(field.df.fieldname, 'read_only', 0));
	},
	has_checked_field(frm) {
		const val = frm.fields.filter(field => field.value === 1);
		return val.length ? 1 : 0;
	},
	_disable_unchecked_fields: function(frm) {
		// get value of clicked field
		frm.fields.filter(field => field.value === 0)
			.map(field => frm.set_df_property(field.df.fieldname, 'read_only', 1));
	},
	disable_unchecked_fields: function(frm) {
		frm.events.reset_check_fields(frm);
		const checked = frm.events.has_checked_field(frm);
		if (checked) {
			frm.events._disable_unchecked_fields(frm);
		}
	},
	is_working_capital: function(frm) {
		frm.events.disable_unchecked_fields(frm);
	},
	is_finance_cost: function(frm) {
		frm.events.disable_unchecked_fields(frm);
	},
	is_income_tax_liability: function(frm) {
		frm.events.disable_unchecked_fields(frm);
	},
	is_income_tax_expense: function(frm) {
		frm.events.disable_unchecked_fields(frm);
	},
	is_finance_cost_adjustment: function(frm) {
		frm.events.disable_unchecked_fields(frm);
	}
});
