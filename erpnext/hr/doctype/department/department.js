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
	},
	refresh: function(frm) {
		// read-only for root department
		if(!frm.doc.parent_department) {
			cur_frm.set_read_only();
			cur_frm.set_intro(__("This is a root customer group and cannot be edited."));
		}
	},
	validate: function(frm) {
		if(frm.doc.name=="All Departments") {
			frappe.throw(__("You cannot edit root node."));
		}
	}
});
