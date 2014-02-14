# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

@frappe.whitelist()
def get_leave_approver_list():
	roles = [r[0] for r in frappe.conn.sql("""select distinct parent from `tabUserRole`
		where role='Leave Approver'""")]
	if not roles:
		frappe.msgprint(_("No Leave Approvers. Please assign 'Leave Approver' Role to atleast one user."))
		
	return roles


@frappe.whitelist()
def get_expense_approver_list():
	roles = [r[0] for r in frappe.conn.sql("""select distinct parent from `tabUserRole`
		where role='Expense Approver'""")]
	if not roles:
		frappe.msgprint("No Expense Approvers. Please assign 'Expense Approver' \
			Role to atleast one user.")
	return roles
