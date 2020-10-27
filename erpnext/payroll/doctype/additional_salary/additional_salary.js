// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Salary', {
	setup: function(frm) {
		frm.add_fetch("salary_component", "deduct_full_tax_on_selected_payroll_date", "deduct_full_tax_on_selected_payroll_date");

		frm.set_query("employee", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});

		if(!frm.doc.currency) return;
		frm.set_query("salary_component", function() {
			return {
				query : "erpnext.payroll.doctype.salary_structure.salary_structure.get_earning_deduction_components",
				filters: {type: "earning", currency: frm.doc.currency, company: frm.doc.company}
			};
		});
	},

	employee: function(frm) {
		if (frm.doc.employee) {
			frm.trigger('get_employee_details');
		} else {
			frm.set_value("company", null);
		}
	},

	get_employee_details: function(frm) {
		frappe.call({
			method: "get_employee_details",
			args: {
				employee: frm.doc.employee,
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value('currency', r.message['currency']);
					frm.set_value('company', r.message['company']);
					frm.refresh_fields();
				}
			}
		});
	},
});
