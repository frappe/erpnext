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
 		if date_of_joining and getdate(self.payroll_date) < getdate(date_of_joining):
 			frappe.throw(_("Payroll date can not be less than employee's joining date"))
 		elif relieving_date and getdate(self.payroll_date) > getdate(relieving_date):
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
		select salary_component, sum(amount) as amount, overwrite_salary_structure_amount from `tabAdditional Salary`
		where employee=%(employee)s
			and docstatus = 1
			and payroll_date between %(from_date)s and %(to_date)s
		group by salary_component, overwrite_salary_structure_amount
		order by salary_component, overwrite_salary_structure_amount
	""", {
		'employee': employee,
		'from_date': start_date,
		'to_date': end_date
	}, as_dict=1)

	additional_components_list = []
	for d in additional_components:
		component = frappe.get_doc("Salary Component", d.salary_component)
		struct_row = {'salary_component': d.salary_component}
		for field in ["depends_on_lwp", "abbr", "is_tax_applicable", "variable_based_on_taxable_salary", "is_additional_component"]:
			struct_row[field] = component.get(field)

		additional_components_list.append({
			'amount': d.amount,
			'type': component.type,
			'struct_row': struct_row,
			'overwrite': d.overwrite_salary_structure_amount
		})
	return additional_components_list