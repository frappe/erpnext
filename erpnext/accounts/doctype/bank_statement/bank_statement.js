// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Statement', {
	refresh: function(frm) {

	},
	process_statement: function(frm){
		frappe.call({
			method: 'fill_table',
			doc: frm.doc,
			freeze: true,
			callback: function(r){
				frm.refresh_field('bank_statement_items');
			}
		})
	}
});

frappe.ui.form.on('Bank Statement Item', 'jl_debit_account_type', (frm, dt, dn)=>{

	cur_frm.fields_dict["bank_statement_items"].grid.get_field("jl_debit_account").get_query = function(doc){
	       return {
	               "filters":{
	                       "account_type": locals[dt][dn].jl_debit_account_type
	               }
	       }
	}
	frm.refresh_field('bank_statement_items');
});