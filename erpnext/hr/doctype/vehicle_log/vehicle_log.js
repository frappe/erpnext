// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Log", {
	refresh: function(frm,cdt,cdn) {
		var vehicle_log=frappe.model.get_doc(cdt,cdn);
		if (vehicle_log.license_plate) {
			frappe.call({
				method: "erpnext.hr.doctype.vehicle_log.vehicle_log.get_make_model",
				args: {
					license_plate: vehicle_log.license_plate
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, ("model"), r.message[0]);
					frappe.model.set_value(cdt, cdn, ("make"), r.message[1]);
				}
			})
		}

		if(frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Expense Claim'), function() {
				frm.events.expense_claim(frm)
			}, __("Make"));
			frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
	},

	expense_claim: function(frm){
		frappe.call({
			method: "erpnext.hr.doctype.vehicle_log.vehicle_log.make_expense_claim",
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

