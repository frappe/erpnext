// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Ledger Entry", {
	refresh(frm) {
		frm.page.btn_secondary.hide();
	},
});
