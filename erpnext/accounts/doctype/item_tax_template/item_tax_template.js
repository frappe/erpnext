// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Tax Template', {
	setup: function(frm) {
		frm.set_query("tax_type", function(doc) {
			return {
				query: "erpnext.controllers.queries.tax_account_query",
				filters: {
					"account_type": ['Tax', 'Chargeable', 'Income Account', 'Expense Account'],
					"company": doc.company
				}
			}
		});
	}
});
