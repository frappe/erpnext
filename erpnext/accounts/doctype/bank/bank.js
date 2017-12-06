// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


cur_frm.fields_dict["bank_accounts"].grid.get_field("gl_account").get_query = function(doc){
	return {
		"filters":{
			"account_type": "Bank",
		}
	}
}
cur_frm.refresh_field('bank_accounts');

frappe.ui.form.on('Bank Account', {
	'bank_accounts_add': (frm, dt, dn)=>{
		cur_frm.fields_dict["bank_accounts"].grid.get_field("gl_account").get_query = function(doc){
			return {
				"filters":{
					"account_type": "Bank",
					"account_currency": locals[dt][dn].currency
				}
			}
		}
		cur_frm.refresh_field('bank_accounts');
	},
	'currency': (frm, dt, dn)=>{
		cur_frm.fields_dict["bank_accounts"].grid.get_field("gl_account").get_query = function(doc){
			return {
				"filters":{
					"account_type": "Bank",
					"account_currency": locals[dt][dn].currency
				}
			}
		}
		cur_frm.refresh_field('bank_accounts');
	}
});

frappe.ui.form.on('Bank', {
	refresh: function(frm) {

	}
});
