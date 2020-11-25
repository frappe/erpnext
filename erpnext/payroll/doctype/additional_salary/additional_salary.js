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

		if (!frm.doc.currency) return;
		frm.set_query("salary_component", function() {
			return {
				query: "erpnext.payroll.doctype.salary_structure.salary_structure.get_earning_deduction_components",
				filters: {currency: frm.doc.currency, company: frm.doc.company}
			};
		});
	},

	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.run_serially([
				() => 	frm.trigger('get_employee_currency'),
				() => 	frm.trigger('set_company')
			]);
		} else {
			frm.set_value("company", null);
		}
	},

	set_company: function(frm) {
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Employee",
				fieldname: "company",
				filters: {
					name: frm.doc.employee
				}
			},
			callback: function(data) {
				if (data.message) {
					frm.set_value("company", data.message.company);
				}
			}
		});
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
