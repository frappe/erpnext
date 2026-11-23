// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Category", {
	onload: function (frm) {
		frm.set_query("fixed_asset_account", "accounts", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					account_type: "Fixed Asset",
					root_type: "Asset",
					is_group: 0,
					company: d.company_name,
				},
			};
		});

		frm.set_query("accumulated_depreciation_account", "accounts", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					account_type: "Accumulated Depreciation",
					is_group: 0,
					company: d.company_name,
				},
			};
		});

		frm.set_query("depreciation_expense_account", "accounts", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					account_type: "Depreciation",
					root_type: ["in", ["Expense", "Income"]],
					is_group: 0,
					company: d.company_name,
				},
			};
		});

		frm.set_query("capital_work_in_progress_account", "accounts", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					account_type: "Capital Work in Progress",
					is_group: 0,
					company: d.company_name,
				},
			};
		});
	},
});

frappe.ui.form.on("Asset Category Account", {
	company_name: function (frm, cdt, cdn) {
		const company = locals[cdt][cdn].company_name;
		frappe.model.set_value(cdt, cdn, {
			accumulated_depreciation_account:
				erpnext.utils.get_default_account(company, "ACCUMULATED_DEPRECIATION") || "",
			depreciation_expense_account:
				erpnext.utils.get_default_account(company, "DEPRECIATION_EXPENSE") || "",
		});
	},
});
