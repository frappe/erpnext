// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tax Exemption 80G Certificate', {
	refresh: function(frm) {

	},

	get_payments: function(frm) {
		return frappe.call({
			method: 'get_payments',
			doc: frm.doc,
			callback: function(r) {
				frm.refresh_fields();
			}
		});
	}
});
