# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
