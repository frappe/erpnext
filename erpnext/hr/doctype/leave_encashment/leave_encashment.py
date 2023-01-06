# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, add_days, today
from erpnext.hr.utils import set_employee_name
from erpnext.hr.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure,\
	get_salary_structure_assignment
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry,\
	delete_expired_leave_ledger_entry, get_leave_allocation
from erpnext.hr.doctype.leave_application.leave_application import get_leaves_for_period
import datetime


class LeaveEncashment(Document):
	def __init__(self, *args, **kwargs):
		super(LeaveEncashment, self).__init__(*args, **kwargs)
		self.whitelisted_globals = {
			"int": int,
			"float": float,
			"long": int,
			"round": round,
			"date": datetime.date,
			"getdate": getdate,
			"date_diff": frappe.utils.date_diff
		}

	def validate(self):
		set_employee_name(self)
		self.get_leave_details_for_encashment()

		if not self.encashment_date:
			self.encashment_date = getdate(nowdate())

	def before_submit(self):
		if self.encashment_amount <= 0:
			frappe.throw(_("You can only submit Leave Encashment for a valid encashment amount"))

	def on_submit(self):
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.company = frappe.get_value("Employee", self.employee, "company")
		additional_salary.employee = self.employee
		additional_salary.salary_component = frappe.get_value("Leave Type", self.leave_type, "earning_component")
		additional_salary.payroll_date = self.encashment_date
		additional_salary.amount = self.encashment_amount
		additional_salary.submit()

		self.db_set("additional_salary", additional_salary.name)

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

	def get_leave_details_for_encashment(self):
		self.salary_structure = get_assigned_salary_structure(self.employee, self.encashment_date or getdate(nowdate()))
		if not self.salary_structure:
			frappe.throw(_("No Salary Structure assigned for Employee {0} on given date {1}").format(self.employee, self.encashment_date))

		self.date_of_joining = frappe.db.get_value("Employee", self.employee, 'date_of_joining')

		if not frappe.db.get_value("Leave Type", self.leave_type, 'allow_encashment'):
			frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

		allocation = self.get_leave_allocation()
		if not allocation:
			frappe.throw(_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(self.employee, self.leave_type))

		self.total_leaves_allocated = allocation.total_leaves_allocated
		self.leaves_taken = -1 * get_leaves_for_period(self.employee, self.leave_type, allocation.from_date, self.encashment_date)
		self.leave_balance = self.total_leaves_allocated - allocation.carry_forwarded_leaves_count - self.leaves_taken

		encashable_days = self.leave_balance - frappe.db.get_value('Leave Type', self.leave_type, 'encashment_threshold_days')
		self.encashable_days = encashable_days if encashable_days > 0 else 0

		self.leave_encashment_amount_per_day = self.get_encashment_amount_per_day()
		self.encashment_amount = flt(self.encashable_days * self.leave_encashment_amount_per_day, self.precision('encashment_amount'))\
			if self.leave_encashment_amount_per_day > 0 else 0

		self.leave_allocation = allocation.name

	def get_leave_allocation(self):
		leave_allocation = get_leave_allocation(self.employee, self.leave_type, getdate(self.encashment_date),
			fields=["name", "from_date", "to_date", "total_leaves_allocated", "carry_forwarded_leaves_count"])

		return leave_allocation

	def create_leave_ledger_entry(self, submit=True):
		args = frappe._dict(
			leaves=self.encashable_days * -1,
			from_date=self.encashment_date,
			to_date=self.encashment_date,
			is_carry_forward=0
		)
		create_leave_ledger_entry(self, args, submit)
		delete_expired_leave_ledger_entry(self.leave_allocation)

	def get_encashment_amount_per_day(self):
		if not self.salary_structure:
			return 0

		data = self.get_data_for_eval()
		salary_structure = frappe.get_doc("Salary Structure", self.salary_structure)

		try:
			condition = salary_structure.leave_encashment_condition.strip().replace("\n", " ")\
				if salary_structure.leave_encashment_condition else None
			if condition:
				if not frappe.safe_eval(condition, self.whitelisted_globals, data):
					return 0

			amount_per_day = salary_structure.leave_encashment_amount_per_day
			if salary_structure.leave_encashment_based_on_formula:
				formula = salary_structure.leave_encashment_formula.strip().replace("\n", " ")\
					if salary_structure.leave_encashment_formula else None
				if formula:
					amount_per_day = flt(frappe.safe_eval(formula, self.whitelisted_globals, data))

			return amount_per_day

		except NameError as err:
			frappe.throw(_("Name error: {0}".format(err)))
		except SyntaxError as err:
			frappe.throw(_("Syntax error in formula or condition: {0}".format(err)))
		except Exception as e:
			frappe.throw(_("Error in formula or condition: {0}".format(e)))
			raise

	def get_data_for_eval(self):
		'''Returns data for evaluating formula'''
		data = frappe._dict()

		salary_structure_assignment = get_salary_structure_assignment(self.employee, self.salary_structure,
			self.encashment_date)
		data.update(frappe.get_doc("Salary Structure Assignment", salary_structure_assignment).as_dict())

		data.update(frappe.get_doc("Employee", self.employee).as_dict())
		data.update(self.as_dict())

		return data


def auto_generate_leave_encashment():
	if frappe.db.get_single_value('HR Settings', 'auto_leave_encashment'):
		generate_leave_encashment()


def generate_leave_encashment(date=None):
	if not date:
		date = add_days(today(), -1)

	leave_allocations = frappe.db.sql("""
		select la.employee, la.leave_type, la.to_date, la.total_leaves_allocated,
			la.new_leaves_allocated
		from `tabLeave Allocation` la
		inner join `tabEmployee` emp on emp.name = la.employee
		inner join `tabLeave Type` lt on lt.name = la.leave_type
		where la.to_date = %(date)s and lt.allow_encashment = 1 and la.docstatus = 1
			and (ifnull(emp.relieving_date, '0000-00-00') = '0000-00-00' or emp.relieving_date >= %(date)s)
	""", {'date': date}, as_dict=1)

	for allocation in leave_allocations:
		if not get_assigned_salary_structure(allocation.employee, allocation.to_date):
			continue

		leave_encashment = frappe.get_doc(dict(
			doctype="Leave Encashment",
			employee=allocation.employee,
			leave_type=allocation.leave_type,
			encashment_date=allocation.to_date
		))
		leave_encashment.insert(ignore_permissions=True)