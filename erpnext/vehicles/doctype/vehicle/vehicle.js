// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleController = frappe.ui.form.Controller.extend({
	setup: function () {
		this.frm.set_query("item_code", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'is_vehicle': 1}
			};
		});
		this.frm.set_query("sales_order", function() {
			return {
				filters: {'docstatus': ['!=', 2]}
			};
		});
	},

	refresh: function () {

	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleController({frm: cur_frm}));