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

		if(!frm.doc.currency) return;
		frm.set_query("salary_component", function() {
		return {
			query : "erpnext.payroll.doctype.salary_structure.salary_structure.get_earning_deduction_components",
			filters: {type: "earning", currency: frm.doc.currency, company: frm.doc.company}
		};
		});

	},

	employee: function(frm) {
		frm.trigger("get_leave_details_for_encashment");
		if (frm.doc.employee) {
			frappe.call({
				method: "erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment.get_payroll_payable_account_currency",
				args: {
					employee: frm.doc.employee,
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value('currency', r.message);
						frm.set_df_property('currency', 'hidden', 0);
					}
				}
			});
			frappe.call({
				method: "frappe.client.get_value",
				args:{
					doctype: "Employee",
					fieldname: "company",
					filters:{
						name: frm.doc.employee
					}
				},
				callback: function(data) {
					if(data.message){
						frm.set_value("company", data.message.company);
					}
				}
			});
		} else {
			frm.set_value("company", null);
		}
	},
});
