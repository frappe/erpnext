# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, bold
from frappe.utils import getdate, date_diff, comma_and, formatdate
from math import ceil
import json

class LeavePolicyAssignment(Document):

	def validate(self):
		self.validate_policy_assignment_overlap()

	def validate_policy_assignment_overlap(self):
		leave_policy_assignments = frappe.db.sql("""
			SELECT
				name
			FROM `tabLeave Policy Assignment`
			WHERE
				employee=%s
				AND name <> %s
				AND docstatus=1
				AND effective_to >= %s
				AND effective_from <= %s""",
			(self.employee, self.name, self.effective_from, self.effective_to), as_dict = 1)


		print(leave_policy_assignments)

		if len(leave_policy_assignments):
			frappe.throw(_("Leave Policy: {0} already assigned for Employee {1} for period {2} to {3}")
				.format(bold(self.leave_policy), bold(self.employee), bold(formatdate(self.effective_from)), bold(formatdate(self.effective_to))))




	def grant_leave_alloc_for_employee(self):
		if self.already_allocated:
			frappe.throw(_("Leave already have been assigned for this Leave Policy Assignment"))
		else:
			leave_allocations = {}
			leave_type_details = get_leave_type_details()

			leave_policy = frappe.get_doc("Leave Policy", self.leave_policy)
			date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

			for leave_policy_detail in leave_policy.leave_policy_details:
				if not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
					leave_allocation, new_leaves_allocated = self.create_leave_allocation(
						leave_policy_detail.leave_type, leave_policy_detail.annual_allocation,
						leave_type_details, date_of_joining
					)

				leave_allocations[leave_policy_detail.leave_type] = {"name": leave_allocation, "leaves": new_leaves_allocated}

			self.db_set("already_allocated", 1)
			return leave_allocations

	def create_leave_allocation(self, leave_type, new_leaves_allocated, leave_type_details, date_of_joining):
		''' Creates leave allocation for the given employee in the provided leave period '''
		carry_forward = self.carry_forward
		if self.carry_forward and not leave_type_details.get(leave_type).is_carry_forward:
			carry_forward = 0

		# Calculate leaves at pro-rata basis for employees joining after the beginning of the given leave period
		if getdate(date_of_joining) > getdate(self.effective_from):
			remaining_period = ((date_diff(self.effective_to, date_of_joining) + 1) / (date_diff(self.effective_to, self.effective_from) + 1))
			new_leaves_allocated = ceil(new_leaves_allocated * remaining_period)

		# Earned Leaves and Compensatory Leaves are allocated by scheduler, initially allocate 0
		if leave_type_details.get(leave_type).is_earned_leave == 1 or leave_type_details.get(leave_type).is_compensatory == 1:
			new_leaves_allocated = 0

		allocation = frappe.get_doc(dict(
			doctype="Leave Allocation",
			employee=self.employee,
			leave_type=leave_type,
			from_date=self.effective_from,
			to_date=self.effective_to,
			new_leaves_allocated=new_leaves_allocated,
			leave_period=self.leave_period or None,
			leave_policy_assignment = self.name,
			leave_policy = self.leave_policy,
			carry_forward=carry_forward
			))
		allocation.save(ignore_permissions = True)
		allocation.submit()
		return allocation.name, new_leaves_allocated

@frappe.whitelist()
def grant_leave_for_multiple_employees(leave_policy_assignments):
	leave_policy_assignments = json.loads(leave_policy_assignments)
	not_granted = []
	for assignment in leave_policy_assignments:
		try:
			frappe.get_doc("Leave Policy Assignment", assignment).grant_leave_alloc_for_employee()
		except:
			not_granted.append(assignment)

		if len(not_granted):
			msg = "Leave not Granted for Assignments:"+ bold(comma_and(not_granted)) + ". Please Check documents"
		else:
			msg = "Leave granted Successfully"
	frappe.msgprint(msg)

@frappe.whitelist()
def create_assignment_for_multiple_employees(employees, data):
	employees= json.loads(employees)
	data = frappe._dict(json.loads(data))
	for employee in employees:
		assignment = frappe.new_doc("Leave Policy Assignment")
		assignment.employee = employee
		assignment.assignment_based_on = data.assignment_based_on
		assignment.leave_policy = data.leave_policy
		assignment.effective_from = getdate(data.effective_from)
		assignment.effective_to = getdate(data.effective_to)
		assignment.leave_period = data.leave_period or None
		assignment.carry_forward = data.carry_forward

		assignment.save()
		assignment.submit()


def get_leave_type_details():
	leave_type_details = frappe._dict()
	leave_types = frappe.get_all("Leave Type",
		fields=["name", "is_lwp", "is_earned_leave", "is_compensatory", "is_carry_forward", "expire_carry_forwarded_leaves_after_days"])
	for d in leave_types:
		leave_type_details.setdefault(d.name, d)
	return leave_type_details

