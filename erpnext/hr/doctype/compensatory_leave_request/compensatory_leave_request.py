# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff
from frappe.model.document import Document
from erpnext.hr.utils import validate_dates, validate_overlap, get_leave_period

class CompensatoryLeaveRequest(Document):

	def validate(self):
		validate_dates(self, self.work_from_date, self.work_end_date)
		validate_overlap(self, self.work_from_date, self.work_end_date)

	def on_submit(self):
		if not self.leave_type:
			frappe.throw(_("Please select a leave type to submit the request"))
		else:
			company = frappe.db.get_value("Employee", self.employee, "company")
			leave_period = get_leave_period(self.work_from_date, self.work_end_date, company)
			if leave_period:
				self.create_leave_allocation(leave_period)
			else:
				frappe.throw(_("There is no leave period in between {0} and {1}").format(self.work_from_date, self.work_end_date))

	def create_leave_allocation(self, leave_period):
		date_difference = date_diff(self.work_end_date, self.work_from_date) + 1
		is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")
		allocation = frappe.new_doc("Leave Allocation")
		allocation.employee = self.employee
		allocation.employee_name = self.employee_name
		allocation.leave_type = self.leave_type
		allocation.from_date = self.work_from_date
		allocation.to_date = self.work_end_date
		allocation.new_leaves_allocated = date_difference
		allocation.total_leaves_allocated = date_difference
		allocation.compensatory_request = self.name
		allocation.description = self.reason
		if is_carry_forward == 1:
			allocation.carry_forward = True
		allocation.save(ignore_permissions = True)
		allocation.submit()
