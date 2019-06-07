// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Regular Work Summary Group', {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Regular Work Summary'), function () {
				frappe.set_route('List', 'Regular Work Summary');
			});
		}
	}
});
