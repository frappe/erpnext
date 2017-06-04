// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee', 'employee_name', 'employee_name');

frappe.ui.form.on('Grievance', {
	refresh: function(frm) {
		if (user_roles.indexOf("HR User")==-1 || user_roles.indexOf("HR Manager")==-1  ){
			frm.set_df_property("employee", "read_only", frm.doc.__islocal ? 0 : 1);
			frm.set_df_property("status", "read_only", frm.doc.reports_to == frappe.session.user ? 0 : 1);
		}
	},
	onload: function(frm)
	{
		
	}
});
cur_frm.set_query("reports_to", function() {
			return {
				query: "erpnext.hr.doctype.leave_application.leave_application.get_approvers",
				filters: {
					employee: cur_frm.doc.employee
				}
			};
		});
