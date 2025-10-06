// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontracting BOM", {
	setup: (frm) => {
		frm.trigger("set_queries");
	},

	set_queries: (frm) => {
		frm.set_query("finished_good", () => {
			return {
				filters: {
					disabled: 0,
					is_stock_item: 1,
					default_bom: ["!=", ""],
					is_sub_contracted_item: 1,
				},
			};
		});

		frm.set_query("finished_good_bom", () => {
			return {
				filters: {
					docstatus: 1,
					is_active: 1,
					item: frm.doc.finished_good,
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
