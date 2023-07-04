// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Repost Accounting Ledger", {
	setup: function(frm) {
		frm.fields_dict['vouchers'].grid.get_field('voucher_type').get_query = function(doc) {
			return {
				filters: {
					name: ['in', ['Purchase Invoice', 'Sales Invoice', 'Payment Entry', 'Journal Entry']]
				}
			}
		}

		frm.fields_dict['vouchers'].grid.get_field('voucher_no').get_query = function(doc) {
			if (doc.company) {
				return {
					filters: {
						company: doc.company,
						docstatus: 1
					}
				}
			}
		}
	},

	refresh: function(frm) {

	},
});
