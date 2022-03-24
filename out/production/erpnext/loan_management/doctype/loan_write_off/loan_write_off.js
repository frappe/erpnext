// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/loan_management/loan_common.js' %};

frappe.ui.form.on('Loan Write Off', {
	loan: function(frm) {
		frm.trigger('show_pending_principal_amount');
	},
	onload: function(frm) {
		frm.trigger('show_pending_principal_amount');
	},
	refresh: function(frm) {
		frm.set_query('write_off_account', function(){
			return {
				filters: {
					'company': frm.doc.company,
					'root_type': 'Expense',
					'is_group': 0
				}
			}
		});
	},
	show_pending_principal_amount: function(frm) {
		if (frm.doc.loan && frm.doc.docstatus === 0) {
			frappe.db.get_value('Loan', frm.doc.loan, ['total_payment', 'total_interest_payable',
				'total_principal_paid', 'written_off_amount'], function(values) {
				frm.set_df_property('write_off_amount', 'description',
					"Pending principal amount is " + cstr(flt(values.total_payment - values.total_interest_payable
						- values.total_principal_paid - values.written_off_amount, 2)));
				frm.refresh_field('write_off_amount');
			});

		}
	}
});
