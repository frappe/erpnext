// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Apply Payment Entries Without References', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['payment_entry'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{
					'docstatus': 1, 
					'unallocated_amount': [">",0]
				}
			}
		}
	},

	setup: function(frm) {
		frm.set_query("reference_name", "references", function() {
			return {
				filters: {
					'docstatus': 1, 
					'outstanding_amount': [">",0]
				}
			}
		});
	}
});
