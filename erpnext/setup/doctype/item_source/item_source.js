// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Source', {
	refresh: function(frm) {
		erpnext.utils.set_item_naming_series_options(frm);
	}
});
