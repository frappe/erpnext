// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('DATEV Settings', {
	refresh: function(frm) {
		frm.add_custom_button('Show Report', () => frappe.set_route('query-report', 'DATEV'), "fa fa-table");
	}
});
