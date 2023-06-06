// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Reservation Entry", {
	refresh(frm) {
		// Hide "Amend" button on cancelled document
		if (frm.doc.docstatus == 2) {
			frm.page.btn_primary.hide()
		}
	},
});
