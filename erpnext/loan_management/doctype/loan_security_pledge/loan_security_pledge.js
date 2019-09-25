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

frappe.ui.form.on("Pledge", {
	qty: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.loan_security_price);

		let amount = 0;
		let maximum_amount = 0;
		$.each(frm.doc.securities || [], function(i, item){
			amount += item.amount;
			maximum_amount += item.amount - (item.amount * item.haircut/100);
		});

		frm.set_value('total_security_value', amount);
		frm.set_value('maximum_loan_value', maximum_amount);
	}
});