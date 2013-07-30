// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

cur_frm.cscript.onload = function(doc,cdt,cdn){
	return $c_obj(make_doclist(cdt,cdn),'get_series','',function(r,rt){
		if(r.message) set_field_options('naming_series', r.message);
	});
	
	cur_frm.set_query("price_list_name", function() {
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

// ------------------ Get Print Heading ------------------------------------
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
	return{
		filters:[
			['Print Heading', 'docstatus', '!=', 2]
		]	
	}	
}

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

cur_frm.fields_dict.user.get_query = function(doc,cdt,cdn) {
	return{	query:"controllers.queries.profile_query"}
}
