// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Structure Assignment', {
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query",
				filters: {
					company: frm.doc.company
				}
			}
		});
	},

	refresh: function(frm) {

	}
});
