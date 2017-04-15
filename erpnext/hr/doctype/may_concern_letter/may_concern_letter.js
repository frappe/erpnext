// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
cur_frm.add_fetch('employee', 'grade', 'grade');
cur_frm.add_fetch('employee', 'branch', 'branch');
cur_frm.add_fetch('employee', 'department', 'department');
cur_frm.add_fetch('employee', 'designation', 'designation');


frappe.ui.form.on('May Concern Letter', {
	refresh: function(frm) {

	}
});
