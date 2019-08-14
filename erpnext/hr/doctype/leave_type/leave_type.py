# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import calendar
import frappe
from datetime import datetime
from frappe.utils import today
from frappe import _

from frappe.model.document import Document

class LeaveType(Document):
	def validate(self):
		if self.is_lwp:
			leave_allocation = frappe.get_all("Leave Allocation", filters={
				'leave_type': self.name,
				'from_date': ("<=", today()),
				'to_date': (">=", today())
			}, fields=['name'])
			leave_allocation = [l['name'] for l in leave_allocation]
			if leave_allocation:
				frappe.throw(_('Leave application is linked with leave allocations {0}. Leave application cannot be set as leave without pay').format(", ".join(leave_allocation))) #nosec
