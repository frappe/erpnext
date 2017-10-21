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

frappe.ui.form.on('Asset Category', {
	depreciation_method: function(frm) {
			frm.toggle_display("total_number_of_depreciations", frm.doc.depreciation_method != "Non-Depreciable Asset");
			frm.set_df_property("total_number_of_depreciations", "reqd", frm.doc.depreciation_method != "Non-Depreciable Asset");
			frm.set_value("total_number_of_depreciations", 0);
			
			frm.set_df_property("frequency_of_depreciation", "reqd", frm.doc.depreciation_method != "Non-Depreciable Asset");
			frm.toggle_display("frequency_of_depreciation", frm.doc.depreciation_method != "Non-Depreciable Asset");
			frm.set_value("frequency_of_depreciation", 0);
	}
});
