// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Loan Security Shortfall', {
	// refresh: function(frm) {

	// }
	on_submit: function(frm) {
		frappe.call({
			method: "erpnext.loan_management.doctype.process_loan_security_shortfall.process_loan_security_shortfall.update_loan_security",
			args: {
				from_timestamp: frm.doc.from_time,
				to_timestamp: frm.doc.to_time,
				loan_security_type: frm.doc.loan_security_type,
				process_loan_security_shortfall: frm.doc.name
			}
		});
	}
});
