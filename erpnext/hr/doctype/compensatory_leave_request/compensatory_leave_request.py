# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, add_days
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
			date_difference = date_diff(self.work_end_date, self.work_from_date) + 1
			leave_period = get_leave_period(self.work_from_date, self.work_end_date, company)
			if leave_period:
				leave_allocation = self.exists_allocation_for_period(leave_period)
				if leave_allocation:
					leave_allocation.new_leaves_allocated += date_difference
					leave_allocation.submit()
				else:
					leave_allocation = self.create_leave_allocation(leave_period, date_difference)
				self.db_set("leave_allocation", leave_allocation.name)
			else:
				frappe.throw(_("There is no leave period in between {0} and {1}").format(self.work_from_date, self.work_end_date))

	def exists_allocation_for_period(self, leave_period):
		leave_allocation = frappe.db.sql("""
			select name
			from `tabLeave Allocation`
			where employee=%(employee)s and leave_type=%(leave_type)s
				and docstatus=1
				and (from_date between %(from_date)s and %(to_date)s
					or to_date between %(from_date)s and %(to_date)s
					or (from_date < %(from_date)s and to_date > %(to_date)s))
		""", {
			"from_date": leave_period[0].from_date,
			"to_date": leave_period[0].to_date,
			"employee": self.employee,
			"leave_type": self.leave_type
		}, as_dict=1)

		if leave_allocation:
			return frappe.get_doc("Leave Allocation", leave_allocation[0].name)
		else:
			return False

	def create_leave_allocation(self, leave_period, date_difference):
		is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")
		allocation = frappe.new_doc("Leave Allocation")
		allocation.employee = self.employee
		allocation.employee_name = self.employee_name
		allocation.leave_type = self.leave_type
		allocation.from_date = add_days(self.work_end_date, 1)
		allocation.to_date = leave_period[0].to_date
		allocation.new_leaves_allocated = date_difference
		allocation.total_leaves_allocated = date_difference
		allocation.description = self.reason
		if is_carry_forward == 1:
			allocation.carry_forward = True
		allocation.save(ignore_permissions = True)
		allocation.submit()
		return allocation
