// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pest', {
	validate: (frm) => {
		frm.doc.treatment_period = frm.doc.treatment_task.valueOf().reduce((greatest, d) => {
			return greatest>d.end_day?greatest:d.end_day;
		}, 1);
		frm.refresh_field("treatment_period");
	}
});