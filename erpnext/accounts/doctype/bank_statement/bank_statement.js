// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

var acc_currency_map = {},
	statement_date_overlap,
	statement_first_validate = true

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
		if (frm.doc.bank){
			frm.trigger('bank');
		}
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
	},
	statement_start_date: (frm)=>{
		frappe.call({
			method: "check_end_date",
			doc: frm.doc,
			callback: function(d){
				if (d.message){	
					statement_date_overlap = d.message.gap
				}
			}
		})
	},
	validate: (frm)=>{
		if ((statement_date_overlap) && (statement_first_validate)){
			frappe.confirm(
				"There is a gap in the previous statement's end date and the specified start date (" + statement_date_overlap + " days). <br><b>Continue</b>?",
				()=>{statement_first_validate=false;frm.save();},
				()=>show_alert('Document save cancelled')
			)
			frappe.validated = false
			return false
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