# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import comma_and, date_diff, formatdate, getdate

from erpnext.hr.utils import validate_active_employee


class AdditionalSalary(Document):
	def on_submit(self):
		self.update_return_amount_in_employee_advance()
		self.update_employee_referral()

	def on_cancel(self):
		self.update_return_amount_in_employee_advance()
		self.update_employee_referral(cancel=True)

	def validate(self):
		validate_active_employee(self.employee)
		self.validate_dates()
		self.validate_salary_structure()
		self.validate_recurring_additional_salary_overlap()
		self.validate_employee_referral()

		if self.amount < 0:
			frappe.throw(_("Amount should not be less than zero"))

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

	def validate_employee_referral(self):
		if self.ref_doctype == "Employee Referral":
			referral_details = frappe.db.get_value("Employee Referral", self.ref_docname,
				["is_applicable_for_referral_bonus", "status"], as_dict=1)

			if not referral_details.is_applicable_for_referral_bonus:
				frappe.throw(_("Employee Referral {0} is not applicable for referral bonus.").format(
					self.ref_docname))

			if self.type == "Deduction":
				frappe.throw(_("Earning Salary Component is required for Employee Referral Bonus."))

			if referral_details.status != "Accepted":
				frappe.throw(_("Additional Salary for referral bonus can only be created against Employee Referral with status {0}").format(
					frappe.bold("Accepted")))

	def update_return_amount_in_employee_advance(self):
		if self.ref_doctype == "Employee Advance" and self.ref_docname:
			return_amount = frappe.db.get_value("Employee Advance", self.ref_docname, "return_amount")

			if self.docstatus == 2:
				return_amount -= self.amount
			else:
				return_amount += self.amount

			frappe.db.set_value("Employee Advance", self.ref_docname, "return_amount", return_amount)

	def update_employee_referral(self, cancel=False):
		if self.ref_doctype == "Employee Referral":
			status = "Unpaid" if cancel else "Paid"
			frappe.db.set_value("Employee Referral", self.ref_docname, "referral_payment_status", status)

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

def get_additional_salaries(employee, start_date, end_date, component_type):
	additional_salary_list = frappe.db.sql("""
		select name, salary_component as component, type, amount,
		overwrite_salary_structure_amount as overwrite,
		deduct_full_tax_on_selected_payroll_date
		from `tabAdditional Salary`
		where employee=%(employee)s
			and docstatus = 1
			and (
					payroll_date between %(from_date)s and %(to_date)s
				or
					from_date <= %(to_date)s and to_date >= %(to_date)s
				)
		and type = %(component_type)s
		order by salary_component, overwrite ASC
	""", {
		'employee': employee,
		'from_date': start_date,
		'to_date': end_date,
		'component_type': "Earning" if component_type == "earnings" else "Deduction"
	}, as_dict=1)

	additional_salaries = []
	components_to_overwrite = []

	for d in additional_salary_list:
		if d.overwrite:
			if d.component in components_to_overwrite:
				frappe.throw(_("Multiple Additional Salaries with overwrite property exist for Salary Component {0} between {1} and {2}.").format(
					frappe.bold(d.component), start_date, end_date), title=_("Error"))

			components_to_overwrite.append(d.component)

		additional_salaries.append(d)

	return additional_salaries
