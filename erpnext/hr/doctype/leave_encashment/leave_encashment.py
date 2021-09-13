# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from erpnext.hr.doctype.leave_allocation.leave_allocation import get_unused_leaves
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry
from erpnext.hr.utils import set_employee_name, validate_active_employee
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	get_assigned_salary_structure,
)


class LeaveEncashment(Document):
	def validate(self):
		set_employee_name(self)
		validate_active_employee(self.employee)
		self.get_leave_details_for_encashment()
		self.validate_salary_structure()

		if not self.encashment_date:
			self.encashment_date = getdate(nowdate())

	def validate_salary_structure(self):
		if not frappe.db.exists('Salary Structure Assignment', {'employee': self.employee}):
			frappe.throw(_("There is no Salary Structure assigned to {0}. First assign a Salary Stucture.").format(self.employee))


	def before_submit(self):
		if self.encashment_amount <= 0:
			frappe.throw(_("You can only submit Leave Encashment for a valid encashment amount"))

	def on_submit(self):
		if not self.leave_allocation:
			self.leave_allocation = self.get_leave_allocation().get('name')
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.company = frappe.get_value("Employee", self.employee, "company")
		additional_salary.employee = self.employee
		additional_salary.currency = self.currency
		earning_component = frappe.get_value("Leave Type", self.leave_type, "earning_component")
		if not earning_component:
			frappe.throw(_("Please set Earning Component for Leave type: {0}.").format(self.leave_type))
		additional_salary.salary_component = earning_component
		additional_salary.payroll_date = self.encashment_date
		additional_salary.amount = self.encashment_amount
		additional_salary.ref_doctype = self.doctype
		additional_salary.ref_docname = self.name
		additional_salary.submit()

		# Set encashed leaves in Allocation
		frappe.db.set_value("Leave Allocation", self.leave_allocation, "total_leaves_encashed",
				frappe.db.get_value('Leave Allocation', self.leave_allocation, 'total_leaves_encashed') + self.encashable_days)

		self.create_leave_ledger_entry()

	def on_cancel(self):
		if self.additional_salary:
			frappe.get_doc("Additional Salary", self.additional_salary).cancel()
			self.db_set("additional_salary", "")

		if self.leave_allocation:
			frappe.db.set_value("Leave Allocation", self.leave_allocation, "total_leaves_encashed",
				frappe.db.get_value('Leave Allocation', self.leave_allocation, 'total_leaves_encashed') - self.encashable_days)
		self.create_leave_ledger_entry(submit=False)

	@frappe.whitelist()
	def get_leave_details_for_encashment(self):
		salary_structure = get_assigned_salary_structure(self.employee, self.encashment_date or getdate(nowdate()))
		if not salary_structure:
			frappe.throw(_("No Salary Structure assigned for Employee {0} on given date {1}").format(self.employee, self.encashment_date))

		if not frappe.db.get_value("Leave Type", self.leave_type, 'allow_encashment'):
			frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

		allocation = self.get_leave_allocation()

		if not allocation:
			frappe.throw(_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(self.employee, self.leave_type))

		self.leave_balance = allocation.total_leaves_allocated - allocation.carry_forwarded_leaves_count\
			- get_unused_leaves(self.employee, self.leave_type, allocation.from_date, self.encashment_date)

		encashable_days = self.leave_balance - frappe.db.get_value('Leave Type', self.leave_type, 'encashment_threshold_days')
		self.encashable_days = encashable_days if encashable_days > 0 else 0

		per_day_encashment = frappe.db.get_value('Salary Structure', salary_structure , 'leave_encashment_amount_per_day')
		self.encashment_amount = self.encashable_days * per_day_encashment if per_day_encashment > 0 else 0

		self.leave_allocation = allocation.name
		return True

	def get_leave_allocation(self):
		leave_allocation = frappe.db.sql("""select name, to_date, total_leaves_allocated, carry_forwarded_leaves_count from `tabLeave Allocation` where '{0}'
		between from_date and to_date and docstatus=1 and leave_type='{1}'
		and employee= '{2}'""".format(self.encashment_date or getdate(nowdate()), self.leave_type, self.employee), as_dict=1) #nosec

		return leave_allocation[0] if leave_allocation else None

	def create_leave_ledger_entry(self, submit=True):
		args = frappe._dict(
			leaves=self.encashable_days * -1,
			from_date=self.encashment_date,
			to_date=self.encashment_date,
			is_carry_forward=0
		)
		create_leave_ledger_entry(self, args, submit)

		# create reverse entry for expired leaves
		leave_allocation = self.get_leave_allocation()
		if not leave_allocation:
			return

		to_date = leave_allocation.get('to_date')
		if to_date < getdate(nowdate()):
			args = frappe._dict(
				leaves=self.encashable_days,
				from_date=to_date,
				to_date=to_date,
				is_carry_forward=0
			)
			create_leave_ledger_entry(self, args, submit)


def create_leave_encashment(leave_allocation):
	''' Creates leave encashment for the given allocations '''
	for allocation in leave_allocation:
		if not get_assigned_salary_structure(allocation.employee, allocation.to_date):
			continue
		leave_encashment = frappe.get_doc(dict(
			doctype="Leave Encashment",
			leave_period=allocation.leave_period,
			employee=allocation.employee,
			leave_type=allocation.leave_type,
			encashment_date=allocation.to_date
		))
		leave_encashment.insert(ignore_permissions=True)
