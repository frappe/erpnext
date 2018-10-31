// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Plaid Settings', {
	refresh: function(frm) {

	},

	connect_btn: function(frm) {
		frappe.set_route('bankreconciliation/synchronization');
	}
});