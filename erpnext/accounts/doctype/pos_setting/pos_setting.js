// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("POS Setting", "onload", function(frm) {
	frm.set_query("selling_price_list", function() {
		return { filter: { selling: 1 } };
	});

	frm.call({
		method: "erpnext.accounts.doctype.pos_setting.pos_setting.get_series",
		callback: function(r) {
			if(!r.exc) {
				set_field_options("naming_series", r.message);
			}
		}
	});
});

//cash bank account
//------------------------------------
cur_frm.fields_dict['cash_bank_account'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{
			'report_type': "Balance Sheet",
			'group_or_ledger': "Ledger",
			'company': doc.company
		}
	}
}

// Income Account
// --------------------------------
cur_frm.fields_dict['income_account'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{
			'group_or_ledger': "Ledger",
			'company': doc.company,
			'account_type': "Income Account"
		}
	}
}


// Cost Center
// -----------------------------
cur_frm.fields_dict['cost_center'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{
			'company': doc.company,
			'group_or_ledger': "Ledger"
		}
	}
}


// Expense Account
// -----------------------------
cur_frm.fields_dict["expense_account"].get_query = function(doc) {
	return {
		filters: {
			"report_type": "Profit and Loss",
			"company": doc.company,
			"group_or_ledger": "Ledger"
		}
	}
}

// ------------------ Get Print Heading ------------------------------------
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return{
		filters:[
			['Print Heading', 'docstatus', '!=', 2]
		]
	}
}


cur_frm.fields_dict.user.get_query = function(doc,cdt,cdn) {
	return{	query:"frappe.core.doctype.user.user.user_query"}
}

cur_frm.fields_dict.write_off_account.get_query = function(doc) {
	return{
		filters:{
			'report_type': 'Profit and Loss',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}
}

// Write off cost center
//-----------------------
cur_frm.fields_dict.write_off_cost_center.get_query = function(doc) {
	return{
		filters:{
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}
}
