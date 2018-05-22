# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class DuplicateAssignment(frappe.ValidationError): pass

class SalaryStructureAssignment(Document):
	def validate(self):
		self.validate_dates()
		self.validate_duplicate_assignments()

	def validate_dates(self):
		joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])

		if self.from_date:
			if joining_date and getdate(self.from_date) < joining_date:
				frappe.throw(_("From Date {0} cannot be before employee's joining Date {1}")
					.format(self.from_date, joining_date))

			# flag - old_employee is for migrating the old employees data via patch
			if relieving_date and getdate(self.from_date) > relieving_date and not self.flags.old_employee:
				frappe.throw(_("From Date {0} cannot be after employee's relieving Date {1}")
					.format(self.from_date, relieving_date))

		if self.to_date:
			if self.from_date and getdate(self.from_date) > getdate(self.to_date):
				frappe.throw(_("From Date {0} cannot be after To Date {1}")
					.format(self.from_date, self.to_date))
			if relieving_date and getdate(self.to_date) > getdate(relieving_date) and not self.flags.old_employee:
				frappe.throw(_("To Date {0} cannot be after employee's relieving Date {1}")
					.format(self.to_date, relieving_date))

	def validate_duplicate_assignments(self):
		if not self.name:
 			# hack! if name is null, it could cause problems with !=
 			self.name = "New "+self.doctype
		assignment = frappe.db.sql("""
			select name from `tabSalary Structure Assignment`
			where employee=%(employee)s
			and name != %(name)s
			and docstatus != 2
			and (
				(%(from_date)s between from_date and ifnull(to_date, '2199-12-31'))
				or (%(to_date)s between from_date and ifnull(to_date, '2199-12-31'))
				or (from_date between %(from_date)s and %(to_date)s)
			)""", {
				'employee': self.employee,
				'from_date': self.from_date,
				'to_date': (self.to_date or '2199-12-31'),
				'name': self.name
			})

		if assignment:
			frappe.throw(_("Active Salary Structure Assignment {0} found for employee {1} for the given dates").
				format(assignment[0][0], self.employee), DuplicateAssignment)

def get_assigned_salary_structure(employee, on_date):
	if not employee or not on_date:
		return None

	salary_structure = frappe.db.sql("""
		select salary_structure from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and (
			(%(on_date)s between from_date and ifnull(to_date, '2199-12-31'))
		)""", {
			'employee': employee,
			'on_date': on_date,
		})

	return salary_structure[0][0] if salary_structure else None
