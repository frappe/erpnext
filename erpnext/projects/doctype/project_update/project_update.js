// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Update', {
	refresh: function() {

	},

	onload: function (frm) {
		frm.set_value("naming_series", "UPDATE-.project.-.YY.MM.DD.-.####");
	},

	validate: function (frm) {
		frm.set_value("time", frappe.datetime.now_time());
		frm.set_value("date", frappe.datetime.nowdate());
	}
});
