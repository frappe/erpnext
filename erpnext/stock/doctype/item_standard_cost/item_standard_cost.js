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

	refresh(frm) {
		frm.trigger("show_backdated_block_warning");
	},

	item_code(frm) {
		frm.trigger("show_backdated_block_warning");
	},

	effective_date(frm) {
		frm.trigger("show_backdated_block_warning");
	},

	show_backdated_block_warning(frm) {
		if (frm.doc.docstatus !== 0 || !frm.doc.item_code || !frm.doc.effective_date) {
			frm.set_intro("");
			return;
		}
		frm.set_intro(
			__(
				"On submission, stock transactions for Item {0} cannot be posted with a date before {1} — backdated entries will be blocked.",
				[
					frappe.utils.escape_html(frm.doc.item_code).bold(),
					frappe.datetime.str_to_user(frm.doc.effective_date).bold(),
				]
			),
			"yellow"
		);
	},
});
