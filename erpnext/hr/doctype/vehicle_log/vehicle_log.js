// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Log", {
	refresh: function(frm) {

		if(frm.doc.license_plate && frm.doc.__islocal){
			frm.events.set_vehicle_details(frm)
		}

		if(frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Expense Claim'), function() {
				frm.events.expense_claim(frm)
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},

	license_plate: function(frm){
		if(frm.doc.license_plate){
			frm.events.set_vehicle_details(frm)
		}
	},

	set_vehicle_details: function(frm){
		frappe.call({
			method: "erpnext.hr.doctype.vehicle_log.vehicle_log.get_make_model",
			args: {
				license_plate: frm.doc.license_plate
			},
			callback: function(r) {
				frappe.model.set_value(cur_frm.doctype, cur_frm.docname, "model", r.message[0]);
				frappe.model.set_value(cur_frm.doctype, cur_frm.docname, "make", r.message[1]);
				frappe.model.set_value(cur_frm.doctype, cur_frm.docname, "last_odometer", r.message[2]);
				frappe.model.set_value(cur_frm.doctype, cur_frm.docname, "employee", r.message[3]);
			}
		});
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

