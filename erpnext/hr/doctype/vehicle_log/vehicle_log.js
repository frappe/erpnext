// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Log", {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1 && !frm.doc.is_opening) {
			frm.add_custom_button(__('Expense Claim'), function() {
				frm.events.expense_claim(frm);
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},

	odometer: function(frm){
		if (!frm.doc.license_plate){
			frappe.throw(__("Please set License Plate"));
		}
		if(frm.doc.last_odometer){
			cur_frm.set_value("distance_covered", frm.doc.odometer - frm.doc.last_odometer);
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

