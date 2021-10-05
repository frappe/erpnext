# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class LeavePolicy(Document):
	def validate(self):
		self.validate_leave_type()
		
		if self.leave_policy_details:
			for lp_detail in self.leave_policy_details:
				if lp_detail.leave_type in leaves:
					frappe.throw(_("Leave Policy {} is selected in row {}".format(lp_detail.leave_type)))
				max_leaves_allowed = frappe.db.get_value("Leave Type", lp_detail.leave_type, "max_leaves_allowed")
				if max_leaves_allowed > 0 and lp_detail.annual_allocation > max_leaves_allowed:
					frappe.throw(_("Maximum leave allowed in the leave type {0} is {1}").format(lp_detail.leave_type, max_leaves_allowed))
	
	def validate_leave_type(self):
		leaves = {row.leave_type for row in self.leave_policy_details}

		if len(leaves) != len(self.leave_policy_details):
			frappe.throw(_("Cannot set multiple Leave Type for a leave policy."))