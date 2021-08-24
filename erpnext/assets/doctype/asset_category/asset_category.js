// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset Category', {
	onload: function(frm) {
		frm.add_fetch('company_name', 'accumulated_depreciation_account', 'accumulated_depreciation_account');
		frm.add_fetch('company_name', 'depreciation_expense_account', 'depreciation_expense_account');

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
					"account_type": "Accumulated Depreciation",
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

		frm.set_query('capital_work_in_progress_account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				"filters": {
					"account_type": "Capital Work in Progress",
					"is_group": 0,
					"company": d.company_name
				}
			};
		});

	}
});

frappe.tour['Asset Category'] = [
	{
		fieldname: 'asset_category_name',
		title: 'Asset Category Name',
		description: 'Name Asset category. You can create categories based on Asset Types. like Furniture, Property, Electronics etc.'
	},
	{
		fieldname: 'enable_cwip_accounting',
		title: 'Enable CWIP Accounting',
		description: 'Check to enable Capital Work in Progress accounting'
	},
	{
		fieldname: 'finance_books',
		title: 'Finance Book Detail',
		description: 'Add a row to define Depreciation Method and other details. Note that you can leave Finance Book blank to have it\'s accounting done in the primary books of accounts.'
	},
	{
		fieldname: 'accounts',
		title: 'Accounts',
		description: "Select the Fixed Asset and Depreciation accounts applicable for this Asset Category type"
	},
]
