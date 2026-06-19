// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Inventory Dimension Bundle", {
	before_submit(frm) {
		// The bundle is submitted automatically when its linked voucher is submitted.
		frappe.throw(__("The user cannot submit the Inventory Dimension Bundle manually."));
	},

	before_cancel(frm) {
		// The bundle is cancelled automatically when its linked voucher is cancelled.
		frappe.throw(__("The user cannot cancel the Inventory Dimension Bundle manually."));
	},
});
