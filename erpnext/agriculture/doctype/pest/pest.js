// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pest', {
	validate: (frm) => {
		frm.doc.period = frm.doc.agriculture_task.valueOf().reduce((greatest, d) => {
			return greatest>d.end_day?greatest:d.end_day;
		}, 1);
		frm.refresh_field("period");
	}
});