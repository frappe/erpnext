// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Encashment', {
	onload: function(frm) {
		// Ignore cancellation of doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];
	},
	setup: function(frm) {
		frm.set_query("leave_type", function() {
			return {
				filters: {
					allow_encashment: 1
				}
			}
		})
	},
	refresh: function(frm) {
		cur_frm.set_intro("");
		if(frm.doc.__islocal && !in_list(frappe.user_roles, "Employee")) {
			frm.set_intro(__("Fill the form and save it"));
		}
	},
	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.run_serially([
				() => 	frm.trigger('get_employee_currency'),
				() => 	frm.trigger('get_leave_details_for_encashment')
			]);
		}
	},
	leave_type: function(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},
	encashment_date: function(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},
	get_leave_details_for_encashment: function(frm) {
		if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type) {
			return frappe.call({
				method: "get_leave_details_for_encashment",
				doc: frm.doc,
				callback: function(r) {
					frm.refresh_fields();
				}
			});
		}
	},

	get_employee_currency: function(frm) {
		frappe.call({
			method: "erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
			args: {
				employee: frm.doc.employee,
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('currency', r.message);
					frm.refresh_fields();
				}
			}
		});
	},
});
