// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleInvoiceDeliveryController = erpnext.vehicles.VehicleTransactionController.extend({
	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {
				item_code: me.frm.doc.item_code,
			};

			if (me.frm.doc.supplier) {
				filters['supplier'] = ['in', ['', me.frm.doc.supplier]];
			}
			if (!cint(me.frm.doc.is_copy)) {
				filters['invoice_status'] = 'In Hand';
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {
				docstatus: 1,
				status: ['!=', 'Cancelled Booking'],
			}

			if (!cint(me.frm.doc.is_copy)) {
				filters['invoice_status'] = 'In Hand';
			}

			return {
				filters: filters
			};
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleInvoiceDeliveryController({frm: cur_frm}));
