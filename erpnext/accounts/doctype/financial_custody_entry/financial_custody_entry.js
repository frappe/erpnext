// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Financial Custody Entry', {
	onload:function(frm){
		frm.set_query("employee", function() {
			return {
				query: "erpnext.controllers.queries.employee_query_custody"
			}
		});
	}
	,
	refresh: function(frm) {

	}
	,
	employee: function(frm) {
		
	}
});
