// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Loan Application', {
	refresh: function(frm) {
		frm.trigger("toggle_fields")
	},
	repayment_method: function(frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function(frm) {
		frm.toggle_enable("repayment_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
	}
});
