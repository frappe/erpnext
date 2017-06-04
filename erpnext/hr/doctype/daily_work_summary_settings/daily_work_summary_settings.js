// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Daily Work Summary Settings', {
	refresh: function(frm) {
		frm.add_custom_button(__('Daily Work Summary'), function() {
			frappe.set_route('List', 'Daily Work Summary');
		});
	}
});
