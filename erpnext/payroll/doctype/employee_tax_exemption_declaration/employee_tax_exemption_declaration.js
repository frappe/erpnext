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
	},

	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			frm.add_custom_button(__('Submit Proof'), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.payroll.doctype.employee_tax_exemption_declaration.employee_tax_exemption_declaration.make_proof_submission",
					frm: frm
				});
			}).addClass("btn-primary");
		}
	},

	employee: function(frm) {
		if (frm.doc.employee) {
			frm.trigger('get_employee_currency');
		}
	},

	get_employee_currency: function(frm) {
		frappe.call({
			method: "erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
			args: {
				employee: frm.doc.employee,
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('currency', r.message);
					frm.refresh_fields();
				}
			}
		});
	}
});
