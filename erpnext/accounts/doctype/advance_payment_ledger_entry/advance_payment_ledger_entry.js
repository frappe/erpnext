// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Advance Payment Ledger Entry", {
	refresh(frm) {
		frm.set_currency_labels(["amount"], frm.doc.currency);
		frm.set_currency_labels(["base_amount"], erpnext.get_currency(frm.doc.company));
	},
});
