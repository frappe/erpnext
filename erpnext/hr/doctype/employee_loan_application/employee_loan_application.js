// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Loan Application', {
	refresh: function(frm) {
		frm.trigger("toggle_fields")
		frm.trigger("add_toolbar_buttons")
	},
	repayment_method: function(frm) {
		frm.doc.repayment_amount = frm.doc.repayment_periods = ""
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("repayment_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
	},
	add_toolbar_buttons: function(frm) {
		if (frm.doc.status == "Approved") {
			frm.add_custom_button(__('Employee Loan'), function() {
				frappe.call({
					type: "GET",
					method: "erpnext.hr.doctype.employee_loan_application.employee_loan_application.make_employee_loan",
					args: {
						"source_name": frm.doc.name
					},
					callback: function(r) {
						if(!r.exc) {
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					}
				});
			})
		}
	}
});
