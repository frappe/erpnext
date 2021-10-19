// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleRegistrationReceiptController = erpnext.vehicles.VehicleTransactionController.extend({
	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {};

			if (me.frm.doc.item_code) {
				filters['item_code'] = me.frm.doc.item_code;
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					docstatus: 1,
					status: ['!=', 'Cancelled Booking']
				}
			};
		});
	},

	vehicle_license_plate: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_license_plate');
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationReceiptController({frm: cur_frm}));
