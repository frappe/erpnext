// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Terms Template', {
	setup: function(frm) {
		frm.add_fetch("payment_term", "description", "description");
		frm.add_fetch("payment_term", "invoice_portion", "invoice_portion");
		frm.add_fetch("payment_term", "due_date_based_on", "due_date_based_on");
		frm.add_fetch("payment_term", "credit_days", "credit_days");
		frm.add_fetch("payment_term", "credit_months", "credit_months");
		frm.add_fetch("payment_term", "mode_of_payment", "mode_of_payment");
	}
});
