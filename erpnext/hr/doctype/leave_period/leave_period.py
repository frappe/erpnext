# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, cstr
from frappe.model.document import Document
from erpnext.hr.utils import validate_overlap, get_employee_leave_policy

class LeavePeriod(Document):
	def get_employees(self):
		conditions, values = [], []
		for field in ["grade", "designation", "department"]:
			if self.get(field):
				conditions.append("{0}=%s".format(field))
				values.append(self.get(field))

		condition_str = " and " + " and ".join(conditions) if len(conditions) else ""

		e = frappe.db.sql("select name from tabEmployee where status='Active' {condition}"
			.format(condition=condition_str), tuple(values))

		return e

	def validate(self):
		self.validate_dates()
		validate_overlap(self, self.from_date, self.to_date, self.company)

	def grant_leave_allocation(self):
		if self.employee:
			self.grant_leave_alloc(self.employee)
		else:
			self.grant_leave_alloc_for_employees()

	def grant_leave_alloc_for_employees(self):
		employees = self.get_employees()
		if employees:
			for employee in employees:
				self.grant_leave_alloc(cstr(employee[0]))
		else:
			frappe.msgprint(_("No employee found"))

	def grant_leave_alloc(self, employee):
		self.validate_allocation_exists(employee)
		leave_policy = get_employee_leave_policy(employee)
		if leave_policy:
			for leave_policy_detail in leave_policy.leave_policy_details:
				if not frappe.db.get_value("Leave Type", leave_policy_detail.leave_type, "is_lwp"):
					self.create_leave_allocation(employee, leave_policy_detail.leave_type, leave_policy_detail.annual_allocation)

	def validate_allocation_exists(self, employee):
		leave_alloc = frappe.db.exists({
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_period": self.name,
				"docstatus": 1})
		if leave_alloc:
			frappe.throw(_("Employee {0} already have Leave Allocation {1} for this period").format(employee, leave_alloc[0][0])\
			+ """ <b><a href="#Form/Leave Allocation/{0}">{0}</a></b>""".format(leave_alloc[0][0]))

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To date can not be equal or less than from date"))

	def create_leave_allocation(self, employee, leave_type, new_leaves_allocated):
		allocation = frappe.new_doc("Leave Allocation")
		allocation.employee = employee
		allocation.employee_name = frappe.db.get_value("Employee", employee, "employee_name")
		allocation.leave_type = leave_type
		allocation.from_date = self.from_date
		allocation.to_date = self.to_date
		allocation.new_leaves_allocated = new_leaves_allocated
		allocation.leave_period = self.name
		if self.carry_forward_leaves:
			if frappe.db.get_value("Leave Type", leave_type, "is_carry_forward"):
				allocation.carry_forward = self.carry_forward_leaves
		allocation.save(ignore_permissions = True)
		allocation.submit()
		frappe.msgprint(_("Leave Allocation {0} created").format(allocation.name))
