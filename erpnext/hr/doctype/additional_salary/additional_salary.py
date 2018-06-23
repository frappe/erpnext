# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, date_diff

class AdditionalSalary(Document):
	def validate(self):
		self.validate_dates()
		if self.amount <= 0:
			frappe.throw(_("Amount should be greater than zero."))

	def validate_dates(self):
 		date_of_joining, relieving_date = frappe.db.get_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])
 		if getdate(self.from_date) > getdate(self.to_date):
 			frappe.throw(_("To date can not be less than from date"))
 		elif date_of_joining and getdate(self.from_date) < getdate(date_of_joining):
 			frappe.throw(_("From date can not be less than employee's joining date"))
 		elif relieving_date and getdate(self.to_date) > getdate(relieving_date):
 			frappe.throw(_("To date can not greater than employee's relieving date"))

	def get_amount(self, sal_start_date, sal_end_date):
		start_date = getdate(sal_start_date)
		end_date = getdate(sal_end_date)
		total_days = date_diff(getdate(self.to_date), getdate(self.from_date)) + 1
		amount_per_day = self.amount / total_days
		if getdate(sal_start_date) <= getdate(self.from_date):
			start_date = getdate(self.from_date)
		if getdate(sal_end_date) > getdate(self.to_date):
			end_date = getdate(self.to_date)
		no_of_days = date_diff(getdate(end_date), getdate(start_date)) + 1
		return amount_per_day * no_of_days

@frappe.whitelist()
def get_additional_salary_component(employee, start_date, end_date):
	additional_components = frappe.db.sql("""
	select name from `tabAdditional Salary`
	where employee=%(employee)s
	and docstatus = 1
	and (
		(%(from_date)s between from_date and to_date)
		or (%(to_date)s between from_date and to_date)
		or (from_date between %(from_date)s and %(to_date)s)
	)""", {
		'employee': employee,
		'from_date': start_date,
		'to_date': end_date
	})

	if additional_components:
		additional_components_array = []
		for additional_component in additional_components:
			struct_row = {}
			additional_components_dict = {}
			additional_component_obj = frappe.get_doc("Additional Salary", additional_component[0])
			amount = additional_component_obj.get_amount(start_date, end_date)
			salary_component = frappe.get_doc("Salary Component", additional_component_obj.salary_component)
			struct_row['depends_on_lwp'] = salary_component.depends_on_lwp
			struct_row['salary_component'] = salary_component.name
			struct_row['abbr'] = salary_component.salary_component_abbr
			struct_row['do_not_include_in_total'] = salary_component.do_not_include_in_total
			struct_row['is_tax_applicable'] = salary_component.is_tax_applicable
			struct_row['variable_based_on_taxable_salary'] = salary_component.variable_based_on_taxable_salary
			struct_row['is_additional_component'] = salary_component.is_additional_component
			additional_components_dict['amount'] = amount
			additional_components_dict['struct_row'] = struct_row
			additional_components_dict['type'] = salary_component.type
			additional_components_array.append(additional_components_dict)

		if len(additional_components_array) > 0:
			return additional_components_array
	return False
