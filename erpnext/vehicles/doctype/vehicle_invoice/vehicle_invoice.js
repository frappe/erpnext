// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleInvoiceController = class VehicleInvoiceController extends erpnext.vehicles.VehicleTransactionController {
	setup_queries() {
		super.setup_queries();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {
				invoice_status: 'Not Received'
			};

			if (me.frm.doc.supplier) {
				filters['supplier'] = ['in', ['', me.frm.doc.supplier]];
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					invoice_status: 'Not Received',
					status: ['!=', 'Cancelled Booking'],
					docstatus: 1,
				}
			};
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleInvoiceController({frm: cur_frm}));
