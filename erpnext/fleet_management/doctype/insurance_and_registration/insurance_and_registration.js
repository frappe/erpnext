// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Insurance and Registration', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		// disable_drag_drop(frm)
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}	
	},
});
