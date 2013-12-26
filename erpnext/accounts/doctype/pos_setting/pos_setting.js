// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc,cdt,cdn){
	return $c_obj(make_doclist(cdt,cdn),'get_series','',function(r,rt){
		if(r.message) set_field_options('naming_series', r.message);
	});
	
	cur_frm.set_query("selling_price_list", function() {
		return { filters: { buying_or_selling: "Selling" } };
	});
}

//cash bank account
//------------------------------------
cur_frm.fields_dict['cash_bank_account'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{
			'debit_or_credit': "Debit",
			'is_pl_account': "No",
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
			'debit_or_credit': "Credit",
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
			"is_pl_account": "Yes",
			"debit_or_credit": "Debit",
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
	return{	query:"core.doctype.profile.profile.profile_query"}
}
