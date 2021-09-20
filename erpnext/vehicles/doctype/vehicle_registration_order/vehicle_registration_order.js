// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleRegistrationOrderController = erpnext.vehicles.VehicleAdditionalServiceController.extend({

});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationOrderController({frm: cur_frm}));
