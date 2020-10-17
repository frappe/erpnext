// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/loan_management/loan_common.js' %};

frappe.ui.form.on('Loan Write Off', {
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
	}
});
