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

		$.each(frm.doc.loan_security_pledges || [], function(i, item){
			amount += item.amount
		});

		frm.set_value('total_security_value', amount);
	}
})