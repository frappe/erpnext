// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Log", {
	refresh: function(frm,cdt,cdn) {
		vehicle_log=frappe.model.get_doc(cdt,cdn);
		if (vehicle_log.license_plate) {
			frappe.call({
				method: "erpnext.fleet_management.doctype.vehicle_log.vehicle_log.get_make_model",
				args: {
					license_plate: vehicle_log.license_plate
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, ("model"), r.message[0]);
					frappe.model.set_value(cdt, cdn, ("make"), r.message[1]);
				}
			})
		}
	},
	expense_claim: function(frm){
			frappe.call({
				method: "erpnext.fleet_management.doctype.vehicle_log.vehicle_log.make_expense_claim",
				args:{
					docname: frm.doc.name
				},
				callback: function(r){
					var doc = frappe.model.sync(r.message);
					frappe.set_route('Form', 'Expense Claim', r.message.name);
					}
			})
	}
});

