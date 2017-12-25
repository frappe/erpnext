// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Category', {
	onload: function(frm) {
		frm.add_fetch('company_name', 'accumulated_depreciation_account', 'accumulated_depreciation_account');
		frm.add_fetch('company_name', 'depreciation_expense_account', 'accumulated_depreciation_account');

		frm.set_query('fixed_asset_account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				"filters": {
					"account_type": "Fixed Asset",
					"root_type": "Asset",
					"is_group": 0,
					"company": d.company_name
				}
			};
		});

		frm.set_query('accumulated_depreciation_account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				"filters": {
					"root_type": "Asset",
					"is_group": 0,
					"company": d.company_name
				}
			};
		});

		frm.set_query('depreciation_expense_account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				"filters": {
					"root_type": "Expense",
					"is_group": 0,
					"company": d.company_name
				}
			};
		});

	}
});