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

frappe.ui.form.on('Project Template Task', {
	task: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.db.get_value("Task", row.task, "subject", (value) => {
			row.subject = value.subject;
			refresh_field("tasks");
		});
	}
});
