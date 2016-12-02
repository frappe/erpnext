// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Loan', {
	onload: function(frm) {
		frm.set_query("employee_loan_application", function() {
			return {
				"filters": {
					"employee": frm.doc.employee
				}
			};
		});
	},

	refresh: function(frm) {
		frm.trigger("toggle_fields")
	},

	employee_loan_application: function(frm) {
		return frm.call({
			method: "get_employee_loan_application",
			doc: frm.doc,
			callback: function(r){
				frm.reload_doc();
			}
		})
	},

	repayment_method: function(frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function(frm) {
		frm.toggle_enable("emi_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
	}
});
