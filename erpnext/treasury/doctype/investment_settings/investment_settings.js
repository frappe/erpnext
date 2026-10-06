// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Settings", {
	setup(frm) {
		for (const fieldname of erpnext.treasury.ACCOUNT_FIELDS) {
			frm.set_query(fieldname, () => ({
				filters: { company: frm.doc.company, is_group: 0 },
			}));
		}
	},

	company(frm) {
		// accounts of the previous company can't be used for the new one
		for (const fieldname of erpnext.treasury.ACCOUNT_FIELDS) {
			frm.set_value(fieldname, null);
		}
	},
});
