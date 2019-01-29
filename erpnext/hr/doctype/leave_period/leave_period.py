# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, cstr
from frappe.model.document import Document
from erpnext.hr.utils import validate_overlap, get_employee_leave_policy
from frappe.utils.background_jobs import enqueue
from six import iteritems

class LeavePeriod(Document):
	def get_employees(self, args):
		conditions, values = [], []
		for field, value in iteritems(args):
			if value:
				conditions.append("{0}=%s".format(field))
				values.append(value)

		condition_str = " and " + " and ".join(conditions) if len(conditions) else ""

		employees = frappe.db.sql_list("select name from tabEmployee where status='Active' {condition}"
			.format(condition=condition_str), tuple(values))

		return employees

	def validate(self):
		self.validate_dates()
		validate_overlap(self, self.from_date, self.to_date, self.company)

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To date can not be equal or less than from date"))


	def grant_leave_allocation(self, grade=None, department=None, designation=None,
			employee=None, carry_forward_leaves=0):
		employees = self.get_employees({
			"grade": grade,
			"department": department, 
			"designation": designation, 
			"name": employee
		})

		if employees:
			if len(employees) > 20:
				frappe.enqueue(grant_leave_alloc_for_employees, timeout=600,
					employees=employees, leave_period=self, carry_forward_leaves=carry_forward_leaves)
			else:
				grant_leave_alloc_for_employees(employees, self, carry_forward_leaves)
		else:
			frappe.msgprint(_("No Employee Found"))

def grant_leave_alloc_for_employees(employees, leave_period, carry_forward_leaves=0):
	leave_allocations = []
	existing_allocations_for = get_existing_allocations(employees, leave_period.name)
	leave_type_details = get_leave_type_details()
	count=0
	for employee in employees:
		if employee in existing_allocations_for:
			continue
		count +=1
		leave_policy = get_employee_leave_policy(employee)
		if leave_policy:
			for leave_policy_detail in leave_policy.leave_policy_details:
				if not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
					leave_allocation = create_leave_allocation(employee, leave_policy_detail.leave_type,
						leave_policy_detail.annual_allocation, leave_type_details, leave_period, carry_forward_leaves)
					leave_allocations.append(leave_allocation)
		frappe.db.commit()
		frappe.publish_progress(count*100/len(set(employees) - set(existing_allocations_for)), title = _("Allocating leaves..."))

	if leave_allocations:
		frappe.msgprint(_("Leaves has been granted sucessfully"))

def get_existing_allocations(employees, leave_period):
	leave_allocations = frappe.db.sql_list("""
		select distinct employee from `tabLeave Allocation` 
		where leave_period=%s and employee in (%s) and docstatus=1
	""" % ('%s', ', '.join(['%s']*len(employees))), [leave_period] + employees)
	if leave_allocations:
		frappe.msgprint(_("Skipping Leave Allocation for the following employees, as Leave Allocation records already exists against them. {0}")
			.format("\n".join(leave_allocations)))
	return leave_allocations

def get_leave_type_details():
	leave_type_details = frappe._dict()
	leave_types = frappe.get_all("Leave Type", fields=["name", "is_lwp", "is_earned_leave", "is_compensatory", "is_carry_forward"])
	for d in leave_types:
		leave_type_details.setdefault(d.name, d)
	return leave_type_details

def create_leave_allocation(employee, leave_type, new_leaves_allocated, leave_type_details, leave_period, carry_forward_leaves):
	allocation = frappe.new_doc("Leave Allocation")
	allocation.employee = employee
	allocation.leave_type = leave_type
	allocation.from_date = leave_period.from_date
	allocation.to_date = leave_period.to_date
	# Earned Leaves and Compensatory Leaves are allocated by scheduler, initially allocate 0
	if leave_type_details.get(leave_type).is_earned_leave == 1 or leave_type_details.get(leave_type).is_compensatory == 1:
		new_leaves_allocated = 0

	allocation.new_leaves_allocated = new_leaves_allocated
	allocation.leave_period = leave_period.name
	if carry_forward_leaves:
		if leave_type_details.get(leave_type).is_carry_forward:
			allocation.carry_forward = carry_forward_leaves
	allocation.save(ignore_permissions = True)
	allocation.submit()
	return allocation.name


