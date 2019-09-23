// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Type', {
	refresh: function(frm) {
		if(!frm.is_new()) {
			frm.add_custom_button(__('Update Loan Security Price'), function() {
				frm.trigger('update_price');
			});
		}
	},
});
