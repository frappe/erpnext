// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Allocation Creation Tool', {
	refresh: function(frm) {
		frm.disable_save();
		frm.events.set_primary_action(frm);
		erpnext.hide_company();
	},

	onload: function(frm) {
		frm.set_query("item_code", function() {
			return erpnext.queries.item({"is_vehicle": 1, "include_in_vehicle_booking": 1, "vehicle_allocation_required": 1});
		});
	},

	set_primary_action: function(frm) {
		frm.page.set_primary_action(__("Create"), function() {
			frm.call({
				method: "create",
				doc: frm.doc,
				freeze: 1,
				freeze_message: __("Creating Vehicle Allocations..."),
				callback: function(r) {
					frm.refresh_fields();
				}
			});
		});
	},

	determine_delivery_periods: function (frm) {
		frm.call({
			method: "determine_delivery_periods",
			doc: frm.doc,
			freeze: 1,
			callback: function(r) {
				frm.refresh_fields();
			}
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
