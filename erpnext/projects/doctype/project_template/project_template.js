// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Template', {
	// refresh: function(frm) {

	// }
	setup: function (frm) {
		frm.set_query("task", "tasks", function () {
			return {
				filters: {
					"is_template": 1
				}
			};
		});
	}
});
