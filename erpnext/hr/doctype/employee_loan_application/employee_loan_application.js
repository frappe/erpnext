// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee','department','department');
frappe.ui.form.on('Employee Loan Application', {
	refresh: function(frm) {
		frm.trigger("toggle_fields")
		frm.trigger("add_toolbar_buttons")
	},
	workflow_state: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
    validate: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
	repayment_method: function(frm) {
		frm.doc.repayment_amount = frm.doc.repayment_periods = ""
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("repayment_amount", frm.doc.repayment_method=="Repay Once")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay over Number of Months")
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
