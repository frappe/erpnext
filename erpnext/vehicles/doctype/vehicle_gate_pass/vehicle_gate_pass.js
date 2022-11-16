// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleGatePass = class VehicleGatePass extends erpnext.vehicles.VehicleTransactionController {
	refresh() {
		super.refresh();
	}

	setup_queries() {
		super.setup_queries();

		var me = this;

		me.frm.set_query("project", function() {
			var filters = {};

			filters['vehicle_status'] = 'In Workshop';

			return {
				filters: filters
			};
		});

		me.frm.set_query("sales_invoice", function() {
			var filters = {"docstatus": ['<', 2]};

			filters['project'] = me.frm.doc.project;

			return {
				filters: filters
			};
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleGatePass({frm: cur_frm}));
