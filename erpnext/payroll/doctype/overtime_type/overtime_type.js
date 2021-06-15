// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Overtime Type', {
	setup: function(frm) {
		frm.set_query("applicable_for", () => {
			let doctype_list = ["Employee", "Department", "Employee Grade"];
			return {
				filters: {
					name: ["in", doctype_list]
				}
			};
		});
	}
});
