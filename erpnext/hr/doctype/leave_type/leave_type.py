# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document

class LeaveType(Document):
	def validate(self):
		if self.is_carry_forward:
			self.validate_carry_forward()

	def validate_carry_forward(self):
		if (self.carry_forward_leave_expiry <1 or self.carry_forward_leave_expiry > 365):
			frappe.throw(_('Invalid entry!! Carried forward days need to expire within a year'))
