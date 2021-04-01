// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Retention Bonus', {
	setup: function(frm) {
		frm.set_query("employee", function() {
			if (!frm.doc.company) {
				frappe.msgprint(__("Please Select Company First"));
			}
			return {
				filters: {
					"status": "Active",
					"company": frm.doc.company
				}
			};
		});

		frm.set_query("salary_component", function() {
			return {
				filters: {
					"type": "Earning"
				}
			};
		});
	},

	employee: function(frm) {
		if (frm.doc.employee) {
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
	}
});
