// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleServiceReceiptController = class VehicleServiceReceiptController extends erpnext.vehicles.VehicleTransactionController{
	refresh() {
		super.refresh();
	}

	setup_queries() {
		super.setup_queries();

		var me = this;

		me.frm.set_query("project", function() {
			var filters = {};

			filters['vehicle_status'] = 'Not Received';

			return {
				filters: filters
			};
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleServiceReceiptController({frm: cur_frm}));
