// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.hr");

frappe.ui.form.on('Expense Receipt', {
	on_load: function(frm) {
		frm.fields_dict.employee.get_query = function() {
			return {
				query: "erpnext.controllers.queries.employee_query"
			};
		};
		frm.add_fetch('employee','employee_name','employee_name');
		frm.add_fetch('employee', 'company', 'company');
	}
});
