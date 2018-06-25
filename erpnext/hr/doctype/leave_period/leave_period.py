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
			leave_allocation = []
			leave_allocation = self.grant_leave_alloc(self.employee, leave_allocation)
			if leave_allocation:
				self.print_message(leave_allocation)
		else:
			self.grant_leave_alloc_for_employees()

	def grant_leave_alloc_for_employees(self):
		employees = self.get_employees()
		if employees:
			leave_allocations = []
			for employee in employees:
				leave_allocations = self.grant_leave_alloc(cstr(employee[0]), leave_allocations)
			if leave_allocations:
				self.print_message(leave_allocations)
		else:
			frappe.msgprint(_("No employee found"))

	def grant_leave_alloc(self, employee, leave_allocations):
		self.validate_allocation_exists(employee)
		leave_policy = get_employee_leave_policy(employee)
		if leave_policy:
			for leave_policy_detail in leave_policy.leave_policy_details:
				if not frappe.db.get_value("Leave Type", leave_policy_detail.leave_type, "is_lwp"):
					leave_allocations.append(self.create_leave_allocation(employee, leave_policy_detail.leave_type, leave_policy_detail.annual_allocation))
		return leave_allocations

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
		# Earned Leaves and Compensatory Leaves are allocated by scheduler, initially allocate 0
		is_earned_leave, is_compensatory = frappe.db.get_value("Leave Type", leave_type, ["is_earned_leave", "is_compensatory"])
		if is_earned_leave == 1 or is_compensatory == 1:
			new_leaves_allocated = 0
		allocation.new_leaves_allocated = new_leaves_allocated
		allocation.leave_period = self.name
		if self.carry_forward_leaves:
			if frappe.db.get_value("Leave Type", leave_type, "is_carry_forward"):
				allocation.carry_forward = self.carry_forward_leaves
		allocation.save(ignore_permissions = True)
		allocation.submit()
		return allocation.name


	def print_message(self, leave_allocations):
		if leave_allocations:
			frappe.msgprint(_("Leave Allocations {0} created").format(", "
				.join(map(lambda x: """ <b><a href="#Form/Leave Allocation/{0}">{0}</a></b>""".format(x), leave_allocations))))
