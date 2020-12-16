# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, bold
from frappe.utils import getdate, date_diff, comma_and, formatdate

class AdditionalSalary(Document):

	def on_submit(self):
		if self.ref_doctype == "Employee Advance" and self.ref_docname:
			frappe.db.set_value("Employee Advance", self.ref_docname, "return_amount", self.amount)

	def before_insert(self):
		if frappe.db.exists("Additional Salary", {"employee": self.employee, "salary_component": self.salary_component,
			"amount": self.amount, "payroll_date": self.payroll_date, "company": self.company, "docstatus": 1}):

			frappe.throw(_("Additional Salary Component Exists."))

	def validate(self):
		self.validate_dates()
		self.validate_salary_structure()
		self.validate_recurring_additional_salary_overlap()
		if self.amount < 0:
			frappe.throw(_("Amount should not be less than zero."))

	def validate_salary_structure(self):
		if not frappe.db.exists('Salary Structure Assignment', {'employee': self.employee}):
			frappe.throw(_("There is no Salary Structure assigned to {0}. First assign a Salary Stucture.").format(self.employee))

	def validate_recurring_additional_salary_overlap(self):
		if self.is_recurring:
			additional_salaries = frappe.db.sql("""
				SELECT
					name
				FROM `tabAdditional Salary`
				WHERE
					employee=%s
					AND name <> %s
					AND docstatus=1
					AND is_recurring=1
					AND salary_component = %s
					AND to_date >= %s
					AND from_date <= %s""",
				(self.employee, self.name, self.salary_component, self.from_date, self.to_date), as_dict = 1)

			additional_salaries = [salary.name for salary in additional_salaries]

			if additional_salaries and len(additional_salaries):
				frappe.throw(_("Additional Salary: {0} already exist for Salary Component: {1} for period {2} and {3}").format(
					bold(comma_and(additional_salaries)),
					bold(self.salary_component),
					bold(formatdate(self.from_date)),
					bold(formatdate(self.to_date)
				)))


	def validate_dates(self):
		date_of_joining, relieving_date = frappe.db.get_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])

		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date can not be greater than To Date."))

		if date_of_joining:
			if self.payroll_date and getdate(self.payroll_date) < getdate(date_of_joining):
				frappe.throw(_("Payroll date can not be less than employee's joining date."))
			elif self.from_date and getdate(self.from_date) < getdate(date_of_joining):
				frappe.throw(_("From date can not be less than employee's joining date."))

		if relieving_date:
			if self.to_date and getdate(self.to_date) > getdate(relieving_date):
				frappe.throw(_("To date can not be greater than employee's relieving date."))
			if self.payroll_date and getdate(self.payroll_date) > getdate(relieving_date):
				frappe.throw(_("Payroll date can not be greater than employee's relieving date."))

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
def get_additional_salary_component(employee, start_date, end_date, component_type):
	additional_salaries = frappe.db.sql("""
		select name, salary_component, type, amount, overwrite_salary_structure_amount, deduct_full_tax_on_selected_payroll_date
		from `tabAdditional Salary`
		where employee=%(employee)s
			and docstatus = 1
			and (
					payroll_date between %(from_date)s and %(to_date)s
				or
					from_date <= %(to_date)s and to_date >= %(to_date)s
				)
		and type = %(component_type)s
		order by salary_component, overwrite_salary_structure_amount DESC
	""", {
		'employee': employee,
		'from_date': start_date,
		'to_date': end_date,
		'component_type': "Earning" if component_type == "earnings" else "Deduction"
	}, as_dict=1)

	existing_salary_components= []
	salary_components_details = {}
	additional_salary_details = []

	overwrites_components = [ele.salary_component for ele in additional_salaries if ele.overwrite_salary_structure_amount == 1]

	component_fields = ["depends_on_payment_days", "salary_component_abbr", "is_tax_applicable", "variable_based_on_taxable_salary", 'type']
	for d in additional_salaries:

		if d.salary_component not in existing_salary_components:
			component = frappe.get_all("Salary Component", filters={'name': d.salary_component}, fields=component_fields)
			struct_row = frappe._dict({'salary_component': d.salary_component})
			if component:
				struct_row.update(component[0])

			struct_row['deduct_full_tax_on_selected_payroll_date'] = d.deduct_full_tax_on_selected_payroll_date
			struct_row['is_additional_component'] = 1

			salary_components_details[d.salary_component] = struct_row


		if overwrites_components.count(d.salary_component) > 1:
			frappe.throw(_("Multiple Additional Salaries with overwrite property exist for Salary Component: {0} between {1} and {2}.".format(d.salary_component, start_date, end_date)), title=_("Error"))
		else:
			additional_salary_details.append({
				'name': d.name,
				'component': d.salary_component,
				'amount': d.amount,
				'type': d.type,
				'overwrite': d.overwrite_salary_structure_amount,
			})

		existing_salary_components.append(d.salary_component)

	return salary_components_details, additional_salary_details
