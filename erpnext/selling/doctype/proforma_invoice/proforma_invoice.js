// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Proforma Invoice", {
	refresh(frm) {
		frm.page.btn_primary.toggle(frm.doc.docstatus !== 2);
	},
});
