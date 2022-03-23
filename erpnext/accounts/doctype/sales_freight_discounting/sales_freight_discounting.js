// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Freight Discounting', {
	refresh: function(frm) {
		if (frm.doc.journal_entry_name){
			frm.set_df_property('journal_entry_name', 'hidden',0)
		}
		// else {
		// 	frm.set_df_property('journal_entry_name', 'hidden',1)
		// }
		
		// cur_frm.set_query("freight_account", function() {
		// 	return {
		// 		"filters":{
		// 			"parent_account": "Freight Charges - BAL",
		// 		}
		// 	};
		// });
	},
	get_invoices: function(frm){
		frm.clear_table("delivery_details")
		frm.call({
			method: 'get_invoices',
			doc:frm.doc,
			callback: function (r) {
				if (r.message) {
					refresh_field('delivery details')
					refresh_field('total_freight')
				}
			}
		})
	},

	start_date: function(frm) {
		if (frm.doc.start_date && frm.doc.docstatus === 0) {
			frm.set_value('end_date', frappe.datetime.add_months(frm.doc.start_date, 1));
			refresh_field('end_date')
		}
	},

	before_save: function(frm){
		frm.call({
			method: 'add_amount_for_total_freight',
			doc:frm.doc,
			callback:function(r){
				if (r.message){
					refresh_field('total_freight')
				}
			}
		})
	}
});

