// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontracting Receipt', {
	setup: function (frm) {
		frm.set_query('subcontracting_order', () => {
			return {
				filters: {
					docstatus: 1,
				}
			};
		});

		frm.set_query("item_code", "service_items", () => {
			return {
				filters: {
					is_stock_item: 0
				}
			};
		});
	},
});
