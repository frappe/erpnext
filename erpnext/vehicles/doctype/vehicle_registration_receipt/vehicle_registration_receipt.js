// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleRegistrationReceiptController = class VehicleRegistrationReceiptController extends erpnext.vehicles.VehicleTransactionController {
	setup_queries() {
		super.setup_queries();

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					status: ['!=', 'Cancelled Booking'],
					docstatus: 1
				}
			};
		});
	}

	vehicle_license_plate() {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_license_plate');
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationReceiptController({frm: cur_frm}));
