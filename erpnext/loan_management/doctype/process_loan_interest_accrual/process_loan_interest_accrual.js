// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Loan Interest Accrual', {
	// refresh: function(frm) {

	// }
	on_submit: function(frm) {
		frappe.call({
			method: "erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_manual_loan_interest",
			args: {
				posting_date: frm.doc.posting_date,
				process_loan_interest: frm.doc.name
			}
		});
	}
});
