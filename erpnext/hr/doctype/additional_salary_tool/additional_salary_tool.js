// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Salary Tool', {
	employee: function(frm) {
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
					})
					refresh_field("earnings");
					refresh_field("deductions");
				}
			}
		});
	}
});