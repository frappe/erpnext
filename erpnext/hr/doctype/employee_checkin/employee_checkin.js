// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Checkin', {
	setup: (frm) => {
		if(!frm.doc.time) {
			frm.set_value("time", frappe.datetime.now_datetime());
		}
	},
	refresh: (frm) => {
		// make log type mandatory
		frm.set_df_property('log_type', 'reqd', frm.doc.log_type ? 0 : 1);
	}
});
