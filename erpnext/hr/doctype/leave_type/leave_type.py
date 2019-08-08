# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import calendar
import frappe
from datetime import datetime
from frappe import _

from frappe.model.document import Document

class LeaveType(Document):
	def validate(self):
		if self.is_lwp:
			leave_allocation = frappe.db.sql_list("""select name from `tabLeave Allocation` where leave_type=%s""", (self.name))
			if leave_allocation:
				frappe.throw(_('Leave application is linked with leave allocations {0}. Leave application cannot be set as leave without pay').format(", ".join(leave_allocation))) #nosec