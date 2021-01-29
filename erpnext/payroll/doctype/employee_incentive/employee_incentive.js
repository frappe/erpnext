// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Incentive', {
	setup: function(frm) {
		frm.set_query("employee", function() {
			return {
				filters: {
					"status": "Active"
				}
			};
		});
		frm.trigger('set_earning_component');
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
					frm.trigger('set_earning_component');
				}
			}
		});
	},

	set_earning_component: function(frm) {
		if (!frm.doc.company) return;
		frm.set_query("salary_component", function() {
			return {
				filters: {type: "earning", company: frm.doc.company}
			};
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
