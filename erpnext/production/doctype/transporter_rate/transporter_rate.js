// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transporter Rate', {
	refresh: function(frm) {
		frm.set_query('expense_account', function(doc) {
			return {
				filters: {
					"disabled": 0,
					"is_group": 0,
					"account_type":"Expense Account"
				}
			};
		});
	}
});
