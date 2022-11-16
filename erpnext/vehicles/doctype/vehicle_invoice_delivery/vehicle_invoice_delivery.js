// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleInvoiceDeliveryController = class VehicleInvoiceDeliveryController extends erpnext.vehicles.VehicleTransactionController {
	setup_queries () {
		super.setup_queries();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {};

			if (!cint(me.frm.doc.is_copy)) {
				filters['invoice_status'] = 'In Hand';
			}
			if (me.frm.doc.supplier) {
				filters['supplier'] = ['in', ['', me.frm.doc.supplier]];
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {};

			if (!cint(me.frm.doc.is_copy)) {
				filters['invoice_status'] = 'In Hand';
			}

			filters['status'] = ['!=', 'Cancelled Booking'];
			filters['docstatus'] = 1;

			return {
				filters: filters
			};
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleInvoiceDeliveryController({frm: cur_frm}));
