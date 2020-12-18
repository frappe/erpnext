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

		this.frm.set_query("insurance_company", function(doc) {
			return {filters: {is_insurance_company: 1}};
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
		this.format_vehicle_id('chassis_no');
		this.validate_duplicate_vehicle('chassis_no');
	},
	engine_no: function () {
		this.format_vehicle_id('engine_no');
		this.validate_duplicate_vehicle('engine_no');
	},
	license_plate: function () {
		this.format_vehicle_id('license_plate');
		this.validate_duplicate_vehicle('license_plate');
	},

	format_vehicle_id: function (fieldname) {
		let value = this.frm.doc[fieldname];
		if (value) {
			value = cstr(value).replace(/\s+/g, "").toUpperCase();
			this.frm.doc[fieldname] = value;
			this.frm.refresh_field(fieldname);
		}
	},

	validate_duplicate_vehicle: function (fieldname) {
		let value = this.frm.doc[fieldname];
		if (value) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle.vehicle.validate_duplicate_vehicle",
				args: {
					fieldname: fieldname,
					value: value,
					exclude: this.frm.is_new() ? null : this.frm.doc.name
				}
			});
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleController({frm: cur_frm}));