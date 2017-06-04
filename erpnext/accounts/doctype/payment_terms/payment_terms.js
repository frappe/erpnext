// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Terms', {
	refresh: function(frm) {

	}
		
});

cur_frm.set_query("income_account", "payment_term_unit", function(doc) {
	return{
		query: "erpnext.controllers.queries.get_income_account",
		filters: {'company': doc.company}
	}
});

cur_frm.set_query("debit_to", function(doc) {
		return {
			filters: {
				'account_type': 'Receivable',
				'is_group': 0,
				'company': doc.company
			}
		}
});
