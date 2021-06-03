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

	refresh: function(frm) {
		if(frm.doc.docstatus === 0) {
			let filters = {
				docstatus: 1,
				company: frm.doc.company
			};
			if(frm.doc.employee) filters["employee"] = frm.doc.employee;
			if(frm.doc.payroll_period) filters["payroll_period"] = frm.doc.payroll_period;

			frm.add_custom_button(__('Get Details From Declaration'), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.payroll.doctype.employee_tax_exemption_declaration.employee_tax_exemption_declaration.make_proof_submission",
					source_doctype: "Employee Tax Exemption Declaration",
					target: frm,
					date_field: "creation",
					setters: {
						employee: frm.doc.employee || undefined
					},
					get_query_filters: filters
				});
			});
		}
	},

	currency: function(frm) {
		frm.refresh_fields();
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
	},
});
