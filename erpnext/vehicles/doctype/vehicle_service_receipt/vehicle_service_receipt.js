// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleServiceReceiptController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
	},

	setup_queries: function () {
		this._super();

		var me = this;

		me.frm.set_query("project", function() {
			var filters = {};

			filters['vehicle_status'] = 'Not Received';

			return {
				filters: filters
			};
		});
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleServiceReceiptController({frm: cur_frm}));
