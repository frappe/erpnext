// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Share Transaction", {
	async company(frm) {
		if (frm.doc.company) {
			const { message } = await frappe.db.get_value("Company", frm.doc.company, "default_currency");
			if (message) {
				await frm.set_value("currency", message.default_currency);
			}
		}
	},
});
