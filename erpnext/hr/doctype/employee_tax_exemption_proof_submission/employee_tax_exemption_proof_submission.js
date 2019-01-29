// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Tax Exemption Proof Submission', {
	setup: function(frm) {
		frm.set_query('employee', function() {
			return {
				filters: {
					'status': "Active"
				}
			}
		});
		frm.set_query('payroll_period', function() {
			if(frm.doc.employee && frm.doc.company){
				return {
					filters: {
						'company': frm.doc.company
					}
				}
			}else {
				frappe.msgprint(__("Please select Employee"));
			}
		});
		frm.set_query('exemption_sub_category', 'tax_exemption_proofs', function() {
			return {
				filters: {
					'is_active': 1
				}
			}
		});
	},
	employee: function(frm){
		if(frm.doc.employee){
			frm.add_fetch('employee', 'company', 'company');
		}else{
			frm.set_value('company', '');
		}
	}
});
