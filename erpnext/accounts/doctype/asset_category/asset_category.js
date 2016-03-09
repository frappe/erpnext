// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.fields_dict['accounts'].grid.get_field('fixed_asset_account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		"filters": {
			"account_type": "Fixed Asset",
			"root_type": "Asset",
			"is_group": 0,
			"company": d.company
		}
	};
}

cur_frm.fields_dict['accounts'].grid.get_field('accumulated_depreciation_account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		"filters": {
			"root_type": "Asset",
			"is_group": 0,
			"company": d.company
		}
	};
}

cur_frm.fields_dict['accounts'].grid.get_field('depreciation_expense_account').get_query = function(doc, cdt, cdn) {
	var d  = locals[cdt][cdn];
	return {
		"filters": {
			"root_type": "Expense",
			"is_group": 0,
			"company": d.company
		}
	};
}