# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document


class LeavePolicy(Document):
	def validate(self):
		self.validate_maximum_leaves()
		self.validate_late_deduction_policy()

	def validate_maximum_leaves(self):
		if self.leave_policy_details:
			for lp_detail in self.leave_policy_details:
				max_leaves_allowed = frappe.db.get_value("Leave Type", lp_detail.leave_type, "max_leaves_allowed")
				if max_leaves_allowed > 0 and lp_detail.annual_allocation > max_leaves_allowed:
					frappe.throw(_("Maximum leave allowed in the leave type {0} is {1}").format(lp_detail.leave_type, max_leaves_allowed))

	def validate_late_deduction_policy(self):
		if self.late_deduction_policy == "n Late Days = 1 Leave Without Pay":
			if cint(self.lwp_per_late_days) <= 0:
				frappe.throw(_("Please enter 'No of Late Days as One Leave Without Pay'"))

		elif self.late_deduction_policy == "Late Days Threshold Rules":
			if not self.late_days_threshold:
				frappe.throw(_("Please add 'Late Days Threshold' rules"))

			for d in self.late_days_threshold:
				if d.late_days <= 0:
					frappe.throw(_("Row #{0}: No of Late Days must be greater than 0"))
				if d.lwp < 0:
					frappe.throw(_("Row #{0}: No of Leave Without Pay cannot be negative"))

	def get_lwp_from_late_days(self, late_days):
		late_days = cint(late_days)

		if self.late_deduction_policy == "n Late Days = 1 Leave Without Pay":
			return late_days // self.lwp_per_late_days if self.lwp_per_late_days else 0
		elif self.late_deduction_policy == "Late Days Threshold Rules":
			applicable_rows = [d for d in self.late_days_threshold if d.late_days <= late_days]
			if applicable_rows:
				max_row = max(applicable_rows, key=lambda d: d.late_days)
				return max_row.lwp

		return 0
