// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cancelled Cheque", {
	setup(frm) {
		frm.set_query("cheque_book", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("payment_entry", () => {
			const filters = { docstatus: 2, cheque_book: ["is", "set"] };
			if (frm.doc.cheque_book) filters.cheque_book = frm.doc.cheque_book;
			const cheque_no = (frm.doc.cheque_no || "").trim();
			if (cheque_no) {
				filters.reference_no = /^\d+$/.test(cheque_no)
					? BigInt(cheque_no).toString().padStart(6, "0")
					: cheque_no;
			}
			return { filters };
		});
	},

	async payment_entry(frm) {
		const payment_entry = frm.doc.payment_entry;
		if (!payment_entry) return;
		const { message } = await frappe.db.get_value("Payment Entry", payment_entry, [
			"cheque_book",
			"reference_no",
		]);
		if (payment_entry !== frm.doc.payment_entry) return;
		await frm.set_value({ cheque_book: message.cheque_book, cheque_no: message.reference_no });
	},
});
