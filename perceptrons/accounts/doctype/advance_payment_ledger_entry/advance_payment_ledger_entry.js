// Copyright (c) 2024, Hash Include Solutions FZC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Advance Payment Ledger Entry", {
	refresh(frm) {
		frm.set_currency_labels(["amount"], frm.doc.currency);
		frm.set_currency_labels(["base_amount"], perceptrons.get_currency(frm.doc.company));
	},
});
