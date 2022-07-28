// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Log", {
	refresh: function(frm) {

	},

	vehicle: function (frm) {
		frm.events.get_last_odometer(frm);
	},
	date: function (frm) {
		frm.events.get_last_odometer(frm);
	},

	get_last_odometer(frm) {
		if (frm.doc.vehicle && frm.doc.date) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_log.vehicle_log.get_vehicle_odometer",
				args: {
					vehicle: frm.doc.vehicle,
					date: frm.doc.date
				},
				callback: function (r) {
					if (!r.exc) {
						frm.set_value("last_odometer", cint(r.message));
					}
				}
			});
		}
	},
});

