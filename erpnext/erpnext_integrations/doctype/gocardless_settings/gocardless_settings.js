// Copyright (c) 2018, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('GoCardless Settings', {
	refresh: function(frm) {
		erpnext.utils.check_payments_app();
	}
});
