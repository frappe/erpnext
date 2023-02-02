// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Feedback', {
	setup: function(frm) {
		erpnext.setup_applies_to_fields(frm);
	}
});
