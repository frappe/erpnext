// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Pledge', {
	// refresh: function(frm) {

	// }

	qty: function(frm) {
		frm.trigger('set_amount');
	},

	set_amount: function(frm) {
		frm.set_value('amount', frm.doc.loan_security_price * frm.doc.qty);
	}
});
