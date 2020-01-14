// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Incentive', {
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				filters: {
					"status": "Active"
				}
			};
		});

		frm.set_query("salary_component", function() {
			return {
				filters: {
					"type": "Earning"
				}
			};
		});
	}
});
