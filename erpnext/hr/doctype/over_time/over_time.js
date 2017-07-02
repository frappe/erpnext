// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

frappe.ui.form.on('Over Time', {
	load: function(frm) {
		frm.set_query("employee", erpnext.queries.employee);

		
	


	}
});
