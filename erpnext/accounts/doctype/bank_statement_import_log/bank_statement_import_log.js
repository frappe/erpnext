// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Statement Import Log", {
	refresh(frm) {
		frm.set_intro(
			__(
				"Go to <a href='/banking/statement-importer' target='_blank' style='text-decoration: underline;'>Bank Statement Importer</a> in the Banking module to use this importer."
			)
		);
	},
});
