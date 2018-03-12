// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Restaurant Menu', {
	setup: function(frm) {
		frm.add_fetch('item', 'standard_rate', 'rate');
	},
});
