// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Transaction', {
	onload: function(frm) {
		frm.set_query('payment_document', 'payment_entries', function(doc, cdt, cdn) {
			return {
				"filters": {
					"name": ["in", ["Payment Entry", "Journal Entry", "Sales Invoice", "Purchase Invoice"]]
				}
			};
		});
	}
});
