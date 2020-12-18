// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Log", {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1 && (frm.doc.price || (frm.doc.service_detail && frm.doc.service_detail.length))) {
			frm.add_custom_button(__('Expense Claim'), function() {
				frm.events.expense_claim(frm);
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
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
				method: "erpnext.vehicles.doctype.vehicle.vehicle.get_vehicle_odometer",
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

	expense_claim: function(frm){
		frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_log.vehicle_log.make_expense_claim",
			args:{
				docname: frm.doc.name
			},
			callback: function(r){
				var doc = frappe.model.sync(r.message);
				frappe.set_route('Form', 'Expense Claim', r.message.name);
			}
		});
	}
});

