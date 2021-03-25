// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleController = frappe.ui.form.Controller.extend({
	setup: function () {
		var me = this;

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

		this.frm.set_query("insurance_company", function(doc) {
			return {filters: {is_insurance_company: 1}};
		});

		this.frm.set_query("color", function() {
			return erpnext.queries.vehicle_color({item_code: me.frm.doc.item_code});
		});
	},

	refresh: function () {

	},

	unregistered: function () {
		if (this.frm.doc.unregistered) {
			this.frm.set_value("license_plate", "");
		}
	},

	chassis_no: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'chassis_no');
		erpnext.utils.validate_duplicate_vehicle(this.frm.doc, 'chassis_no');
	},
	engine_no: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'engine_no');
		erpnext.utils.validate_duplicate_vehicle(this.frm.doc, 'engine_no');
	},
	license_plate: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'license_plate');
		erpnext.utils.validate_duplicate_vehicle(this.frm.doc, 'license_plate');
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleController({frm: cur_frm}));