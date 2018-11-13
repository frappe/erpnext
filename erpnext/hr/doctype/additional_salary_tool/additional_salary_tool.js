// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Salary Tool', {
	setup: function(frm) {
		frm.set_query("salary_component", "earnings", function(doc, cdt, cdn) {
			return {
				filters: {
					"type": "Earning"
				}
			};
		});
		frm.set_query("salary_component", "deductions", function(doc, cdt, cdn) {
			return {
				filters: {
					"type": "Deduction"
				}
			};
		});
	},

	employee: function(frm) {
		if(frm.doc.employee) {
			frappe.call({
				"method": "erpnext.hr.doctype.additional_salary_tool.additional_salary_tool.get_additional_salary_records",
				"args": {
					"employee": frm.doc.employee
				},
				callback: function(r) {
					if(r.message) {
						frm.clear_table("earnings");
						frm.clear_table("deductions");
						// add in table
						$.each(r.message, function(i, v) {
							var child_fieldname = v.type=="Earning" ? "earnings" : "deductions";
							var row = frappe.model.add_child(frm.doc, "Additional Salary Tool Component", child_fieldname);
							row.salary_component = v.salary_component;
							row.amount = v.amount;
							row.additional_salary_id = v.name;
							row.bank = v.bank;
							row.payroll_date = v.payroll_date;
							row.is_recurring = v.is_recurring;
							row.to_date = v.to_date;
						})
						refresh_field("earnings");
						refresh_field("deductions");
					}
				}
			});
		}
	}
});