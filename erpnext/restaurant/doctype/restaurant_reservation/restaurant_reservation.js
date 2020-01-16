// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Restaurant Reservation', {
	setup: function(frm) {
		frm.add_fetch('customer', 'customer_name', 'customer_name');
	},
	refresh: function(frm) {

	}
});
