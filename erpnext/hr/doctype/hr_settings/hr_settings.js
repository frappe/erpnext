// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('HR Settings', {
	restrict_backdated_leave_application: function(frm) {
		frm.toggle_reqd("role_allowed_to_create_backdated_leave_application", frm.doc.restrict_backdated_leave_application);
	}
});