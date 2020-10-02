// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transaction Type', {
	setup: function(frm) {
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': ['in', ['Receivable', 'Payable']],
				'company': d.company,
				"is_group": 0
			};
			return {
				filters: filters
			}
		});
		frm.set_query('cost_center', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'company': d.company,
				"is_group": 0
			};
			return {
				filters: filters
			}
		});
	}
});
