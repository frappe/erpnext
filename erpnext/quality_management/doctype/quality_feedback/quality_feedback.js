// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Feedback', {
	onload: function(frm){
		frm.doc.email = frappe.session.user_email;
		frm.refresh();
	},
});
