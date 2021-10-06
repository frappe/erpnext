// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank reconciliations', {
	// refresh: function(frm) {

	// }
	setup: function(frm) {
		frm.set_query("bank_trasaction", "detail", function(doc) {
			var filters = {"docstatus": 4, "bank_account": doc.bank_account};

			return {
				filters: filters
			};
		});
	},
});
