// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Allocation', {
	refresh: function(frm) {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
	},

	onload: function(frm) {
		frm.set_query("item_code", function() {
			return erpnext.queries.item({"is_vehicle": 1, "include_in_vehicle_booking": 1, "vehicle_allocation_required": 1});
		});
	},

	item_code: function (frm) {
		if (frm.doc.item_code && frm.doc.company) {
			return frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_vehicle_default_supplier",
				args: {
					item_code: frm.doc.item_code,
					company: frm.doc.company
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("supplier", r.message);
					}
				}
			});
		}
	}
});
