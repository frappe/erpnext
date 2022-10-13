// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleMovementController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
		this.show_stock_ledger()
	},

	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {};
			filters['warehouse'] = ['is', 'set'];

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {};
			filters['delivery_status'] = 'In Stock';
			filters['status'] = ['!=', 'Cancelled Booking'];
			filters['docstatus'] = 1;

			return {
				filters: filters
			};
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleMovementController({frm: cur_frm}));
