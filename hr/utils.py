# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

@webnotes.whitelist()
def get_leave_approver_list():
	roles = [r[0] for r in webnotes.conn.sql("""select distinct parent from `tabUserRole`
		where role='Leave Approver'""")]
	if not roles:
		webnotes.msgprint(_("No Leave Approvers. Please assign 'Leave Approver' Role to atleast one user."))
		
	return roles


@webnotes.whitelist()
def get_expense_approver_list():
	roles = [r[0] for r in webnotes.conn.sql("""select distinct parent from `tabUserRole`
		where role='Expense Approver'""")]
	if not roles:
		webnotes.msgprint("No Expense Approvers. Please assign 'Expense Approver' \
			Role to atleast one user.")
	return roles
