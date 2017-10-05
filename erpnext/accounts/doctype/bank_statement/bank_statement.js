// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var acc_currency_map = {}

frappe.ui.form.on('Bank Statement', {
	refresh: (frm)=>{
		var doc = frm.doc;
		frm.add_custom_button(__("Process Statement"), function() {
			frappe.call()
		});
		frm.add_custom_button(__("Upload Statement"), function() {
			frappe.call({
				method: 'fill_table',
				doc: frm.doc,
				freeze: true,
				callback: function(r){
					frm.refresh_field('bank_statement_items');
				}
			})
		});
	},
	bank: (frm)=>{
		frappe.call({
			method: "get_account_no",
			doc: frm.doc,
			callback: function(d){
				if (d.message){	
					frm.set_df_property("account_no", "options", d.message.acc_nos);
					acc_currency_map.map = d.message.currency_map
				}
			}
		})
	},
	account_no: (frm)=>{
		if (acc_currency_map.map){
			frm.set_value('account_currency', acc_currency_map.map[frm.doc.account_no])
			frm.refresh_field('account_currency')
		}
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