// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Allocation', {
	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
	},

	onload: function(frm) {
		frm.set_query("item_code", function() {
			return erpnext.queries.item({"is_vehicle": 1, "include_item_in_vehicle_booking": 1});
		});
	},
});
