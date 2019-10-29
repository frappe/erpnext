// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Unpledge', {
	refresh: function(frm) {

		frm.set_query("against_pledge", "securities", () => {
			return {
				filters : [["status", "in", ["Pledged", "Partially Pledged"]]]
			};
		});
	}
});
