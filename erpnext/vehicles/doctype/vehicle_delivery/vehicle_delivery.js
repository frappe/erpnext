// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleDeliveryController = class VehicleDeliveryController extends erpnext.vehicles.VehicleTransactionController {
	refresh() {
		super.refresh();
		this.show_stock_ledger()
	}

	setup_queries() {
		super.setup_queries();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {};

			if (me.frm.doc.warehouse) {
				filters['warehouse'] = me.frm.doc.warehouse;
			} else if (cint(me.frm.doc.is_return)) {
				filters['warehouse'] = ['is', 'not set'];
				filters['delivery_document_no'] = ['is', 'set'];
			} else {
				filters['warehouse'] = ['is', 'set'];
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {};

			if (cint(me.frm.doc.is_return)) {
				filters['delivery_status'] = 'Delivered';
			} else {
				filters['delivery_status'] = 'In Stock';
			}

			filters['status'] = ['!=', 'Cancelled Booking'];
			filters['docstatus'] = 1;

			return {
				filters: filters
			};
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleDeliveryController({frm: cur_frm}));
