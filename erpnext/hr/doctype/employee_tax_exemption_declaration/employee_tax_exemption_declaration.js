// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Tax Exemption Declaration', {
	setup: function(frm) {
		frm.set_query('employee', function() {
			return {
				filters: {
					'status': "Active"
				}
			}
		});
		frm.set_query('payroll_period', function() {
			const fields = {'employee': 'Employee', 'company': 'Company'};

			for (let [field, label] of Object.entries(fields)) {
				if (!frm.doc[field]) {
					frappe.msgprint(__("Please select {0}", [label]))
				}
			};

			if (frm.doc.employee && frm.doc.company){
				return {
					filters: {
						'company': frm.doc.company
					}
				}
			}
		});
		frm.set_query('exemption_sub_category', 'declarations', function() {
			return {
				filters: {
					'is_active': 1
				}
			}
		});
	}
});
