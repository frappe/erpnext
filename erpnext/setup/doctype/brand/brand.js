// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Brand", {
	setup: (frm) => {
		frm.set_query("default_warehouse", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: { company: row.company },
			};
		});

		frm.set_query("default_discount_account", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					report_type: "Profit and Loss",
					company: row.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("buying_cost_center", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		});

		frm.set_query("expense_account", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: { company: row.company },
			};
		});

		frm.set_query("default_provisional_account", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					company: row.company,
					root_type: ["in", ["Liability", "Asset"]],
					is_group: 0,
				},
			};
		});

		frm.set_query("selling_cost_center", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					is_group: 0,
					company: row.company,
				},
			};
		});

		frm.set_query("income_account", "brand_defaults", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				query: "erpnext.controllers.queries.get_income_account",
				filters: { company: row.company },
			};
		});
	},
});
