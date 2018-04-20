// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Department', {
	onload: function(frm) {
		frm.set_query("leave_approver", "leave_approvers", function(doc) {
			return {
				query:"erpnext.hr.doctype.department_approver.department_approver.get_department_approvers",
				filters:{
					user: doc.user_id
				}
			};
		});
		frm.set_query("expense_approver", "expense_approvers", function(doc) {
			return {
				query:"erpnext.hr.doctype.department_approver.department_approver.get_department_approvers",
				filters:{
					user: doc.user_id
				}
			};
		});
	}
});
