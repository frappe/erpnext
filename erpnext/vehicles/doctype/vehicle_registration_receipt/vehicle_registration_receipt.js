// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleRegistrationReceiptController = erpnext.vehicles.VehicleTransactionController.extend({
	setup_queries: function () {
		this._super();

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					status: ['!=', 'Cancelled Booking'],
					docstatus: 1
				}
			};
		});
	},

	vehicle_license_plate: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_license_plate');
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationReceiptController({frm: cur_frm}));
