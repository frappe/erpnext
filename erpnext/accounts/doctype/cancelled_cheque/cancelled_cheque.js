// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cancelled Cheque", {
	setup(frm) {
		frm.set_query("cheque_book", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("payment_entry", () => ({
			filters: { cheque_book: frm.doc.cheque_book, docstatus: 2 },
		}));
	},
});
