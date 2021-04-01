// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefit Claim', {
	setup: function(frm) {
		frm.set_query("earning_component", function() {
			return {
				query : "erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application.get_earning_components",
				filters: {date: frm.doc.claim_date, employee: frm.doc.employee}
			};
		});
	},
	employee: function(frm) {
		frm.set_value("earning_component", null);
		if (frm.doc.employee) {
			frappe.call({
				method: "erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_employee_currency",
				args: {
					employee: frm.doc.employee,
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('currency', r.message);
					}
				}
			});
		}
		if (!frm.doc.earning_component) {
			frm.doc.max_amount_eligible = null;
			frm.doc.claimed_amount = null;
		}
		frm.refresh_fields();
	}
});
