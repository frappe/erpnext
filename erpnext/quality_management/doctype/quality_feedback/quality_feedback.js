// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Feedback', {
	onload: function(frm){
		frm.set_value("email", frappe.session.user_email);
		frm.set_value("date", frappe.datetime.get_today());
		frm.refresh();
	},
});
