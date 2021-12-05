// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleTransferLetterController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
	},

	setup_queries: function () {
		this._super();

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					status: ['!=', 'Cancelled Booking'],
					docstatus: 1,
				}
			};
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleTransferLetterController({frm: cur_frm}));
