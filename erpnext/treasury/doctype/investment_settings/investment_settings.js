// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Investment Settings", {
	setup(frm) {
		for (const fieldname of erpnext.treasury.ACCOUNT_FIELDS) {
			frm.set_query(fieldname, "company_accounts", (doc, cdt, cdn) => ({
				filters: { company: locals[cdt][cdn].company, is_group: 0 },
			}));
		}
	},
});

frappe.ui.form.on("Investment Default Account", {
	company(frm, cdt, cdn) {
		// accounts of the previous company can't be used for the new one
		for (const fieldname of erpnext.treasury.ACCOUNT_FIELDS) {
			frappe.model.set_value(cdt, cdn, fieldname, null);
		}
	},
});
