// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleTransferLetterController = class VehicleTransferLetterController extends erpnext.vehicles.VehicleTransactionController {
	refresh() {
		super.refresh();
	}

	setup_queries() {
		super.setup_queries();

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					status: ['!=', 'Cancelled Booking'],
					docstatus: 1,
				}
			};
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleTransferLetterController({frm: cur_frm}));
