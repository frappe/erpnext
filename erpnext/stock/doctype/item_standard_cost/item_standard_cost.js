// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Standard Cost", {
	setup(frm) {
		// Only allow items whose effective valuation method is "Standard Cost".
		frm.set_query("item_code", () => {
			return {
				query: "erpnext.stock.doctype.item_standard_cost.item_standard_cost.get_standard_cost_items",
				filters: {
					company: frm.doc.company,
				},
			};
		});
	},
});
