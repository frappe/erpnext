// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Restaurant', {
	refresh: function(frm) {
		frm.add_custom_button(__('Order Entry'), () => {
			frappe.set_route('Form', 'Restaurant Order Entry');
		});
	}
});
