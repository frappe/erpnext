// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Goal', {
	refresh: function(frm) {
		frm.doc.created_by = frappe.session.user;
		if (!frm.doc.revised_on) {
			frm.doc.revised_on = frappe.datetime.get_today();
		}
	}
});
