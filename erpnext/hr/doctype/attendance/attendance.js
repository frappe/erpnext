// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.ui.form.on("Attendance", {
	setup: function(frm) {
		frm.set_query("remaining_half_day_status", function() {
			return {
				filters: {
					is_half_day: 0,
					is_leave: 0,
				}
			};
		});

		frm.set_query("employee", erpnext.queries.employee);
	},
});

cur_frm.add_fetch('employee', 'company', 'company');
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.__islocal) cur_frm.set_value("attendance_date", frappe.datetime.get_today());
};
