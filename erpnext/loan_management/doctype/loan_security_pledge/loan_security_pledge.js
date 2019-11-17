// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pledge", {

	loan_security: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.loan_management.doctype.loan_security_price.loan_security_price.get_loan_security_price",
			args: {
				loan_security: row.loan_security
			},
			callback: function(r) {
				frappe.model.set_value(cdt, cdn, 'loan_security_price', r.message);
			}
		})
	},

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