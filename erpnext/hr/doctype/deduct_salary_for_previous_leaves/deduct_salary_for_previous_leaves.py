# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, rounded, getdate, get_first_day, get_last_day
import calendar
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from frappe.model.document import Document

class DeductSalaryforPreviousLeaves(Document):
	def validate(self):
		self.additional_salary = None
		self.calculate_total_leaves()
		self.calculate_deduction_amount()

	def on_submit(self):
		self.create_additional_salary()
		self.create_leave_applications()

	def on_cancel(self):
		self.cancel_additional_salary()
		self.cancel_leave_applications()

	def calculate_total_leaves(self):
		self.total_leaves, self.total_leaves_without_pay = 0.0, 0.0
		for d in self.leave_periods:
			if cint(d.is_lwp):
				self.total_leaves_without_pay += flt(d.total_days)
			self.total_leaves += flt(d.total_days)

	def calculate_deduction_amount(self):
		self.total_deduction_amount = 0.0
		for d in self.leave_periods:
			salary_structure = frappe.db.sql("""
				select salary_structure
				from `tabSalary Structure Assignment`
				where employee=%s and docstatus=1
					and from_date < %s
				order by from_date desc
				limit 1
			""", (self.employee, d.from_date))

			dt = getdate(d.from_date)
			days_in_month = cint(calendar.monthrange(cint(dt.year) ,cint(dt.month))[1])
			month_start_date = get_first_day(dt)
			month_end_date = get_last_day(dt)

			salary_slip = make_salary_slip(salary_structure[0][0], employee=self.employee,
				from_date=month_start_date, to_date=month_end_date)

			amount = 0.0
			for e in salary_slip.earnings:
				if e.prorated_based_on_attendance or (d.is_lwp and e.depends_on_lwp):
					amount += flt(e.default_amount)

			for f in salary_slip.deductions:
				if f.prorated_based_on_attendance or (d.is_lwp and f.depends_on_lwp):
					amount -= flt(f.default_amount)

			prorated_amount = rounded(amount * d.total_days / days_in_month)

			self.total_deduction_amount += prorated_amount

	def create_additional_salary(self):
		addl_salary = frappe.new_doc("Additional Salary")
		addl_salary.company = self.company
		addl_salary.employee = self.employee
		addl_salary.salary_component = self.salary_component
		addl_salary.payroll_date = self.payroll_date
		addl_salary.amount = self.total_deduction_amount
		addl_salary.submit()

		self.db_set("additional_salary", addl_salary.name)

	def create_leave_applications(self):
		for d in self.leave_periods:
			leave = frappe.new_doc("Leave Application")
			leave.employee = self.employee
			leave.leave_type = d.leave_type
			leave.from_date = d.from_date
			leave.to_date = d.to_date
			leave.status = "Approved"
			leave.save()
			leave.submit()

	def cancel_additional_salary(self):
		if self.additional_salary:
			addl_salary = frappe.get_doc("Additional Salary", self.additional_salary)
			addl_salary.cancel()

	def cancel_leave_applications(self):
		for d in self.leave_periods:
			leave_applications = frappe.db.sql_list("""
				select name from `tabLeave Application`
				where employee=%s and from_date=%s and to_date=%s and leave_type=%s
			""", (self.employee, d.from_date, d.to_date, d.leave_type))
			for l in leave_applications:
				la = frappe.get_doc("Leave Application", l)
				la.cancel()