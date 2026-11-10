// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontracting BOM", {
	setup: (frm) => {
		frm.trigger("set_queries");
	},

	set_queries: (frm) => {
		frm.set_query("finished_good", () => {
			return {
				query: "erpnext.controllers.queries.subcontracted_item_query",
			};
		});

		frm.set_query("finished_good_bom", () => {
			return {
				query: "erpnext.subcontracting.doctype.subcontracting_bom.subcontracting_bom.finished_good_bom_query",
				filters: {
					finished_good: frm.doc.finished_good,
				},
			};
		});

		frm.set_query("service_item", () => {
			return {
				filters: {
					disabled: 0,
					is_stock_item: 0,
				},
			};
		});
	},
});
