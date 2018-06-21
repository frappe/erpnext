// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Salary', {
	setup: function(frm) {
		frm.set_query("salary_component", function() {
			return {
				filters: {
					is_additional_component: true
				}
			};
		});
		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
	}
});
