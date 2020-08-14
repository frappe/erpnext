# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import flt
from math import floor

from frappe.utils import get_datetime
class Gratuity(Document):
	def validate(self):
		calculate_work_experience_and_amount(self.employee, self.gratuity_rule)

	def before_submit(self):
		self.status = "Unpaid"
		if self.pay_via_salary_slip:
			self.status = "Paid"

	def on_submit(self):
		if self.pay_via_salary_slip:
			additional_salary = frappe.new_doc('Additional Salary')
			additional_salary.employee = self.employee
			additional_salary.salary_component = self.salary_component
			additional_salary.overwrite_salary_structure_amount = 0
			additional_salary.amount = self.amount
			additional_salary.payroll_date = self.payroll_date
			additional_salary.company = self.company
			additional_salary.ref_doctype = self.doctype
			additional_salary.ref_docname = self.name
			additional_salary.submit()


	def set_total_advance_paid(self):
		paid_amount = frappe.db.sql("""
			select ifnull(sum(debit_in_account_currency), 0) as paid_amount
			from `tabGL Entry`
			where against_voucher_type = 'Gratuity'
				and against_voucher = %s
				and party_type = 'Employee'
				and party = %s
		""", (self.name, self.employee), as_dict=1)[0].paid_amount

		if flt(paid_amount) > self.amount:
			frappe.throw(_("Row {0}# Paid Amount cannot be greater than Total amount"),
				EmployeeAdvanceOverPayment)


		self.db_set("paid_amount", paid_amount)
		if self.amount == self.paid_amount:
			self.db_set("status", "Paid")


@frappe.whitelist()
def calculate_work_experience_and_amount(employee, gratuity_rule):
	current_work_experience = calculate_work_experience(employee, gratuity_rule) or 0
	gratuity_amount = calculate_gratuity_amount(employee, gratuity_rule, current_work_experience) or 0

	return {'current_work_experience': current_work_experience, "amount": gratuity_amount}

def calculate_work_experience(employee, gratuity_rule):

	total_working_days_per_year = frappe.db.get_value("Gratuity Rule", gratuity_rule, "total_working_days_per_year")

	date_of_joining, relieving_date = frappe.db.get_value('Employee', employee, ['date_of_joining', 'relieving_date'])
	if not relieving_date:
		frappe.throw(_("Please set Relieving Date for employee: {0}").format(bold(employee)))

	# time_difference = relativedelta(relieving_date, date_of_joining)
	method = frappe.db.get_value("Gratuity Rule", gratuity_rule, "work_experience_calculation_function")

	employee_total_workings_days = (get_datetime(relieving_date) - get_datetime(date_of_joining)).days

	# current_work_experience = time_difference.years

	current_work_experience = employee_total_workings_days/total_working_days_per_year or 1

	print("--->", current_work_experience)

	if method == "Round off Work Experience":
		current_work_experience = round(current_work_experience)
	else:
		current_work_experience = floor(current_work_experience)


	return current_work_experience

def calculate_gratuity_amount(employee, gratuity_rule, experience):
	applicable_earnings_component = frappe.get_all("Gratuity Applicable Component", filters= {'parent': gratuity_rule}, fields=["salary_component"])
	applicable_earnings_component = [component.salary_component for component in applicable_earnings_component]

	slabs = get_gratuity_rule_slabs(gratuity_rule)

	total_applicable_components_amount = get_total_applicable_component_amount(employee, applicable_earnings_component, gratuity_rule)



	calculate_gratuity_amount_based_on = frappe.db.get_value("Gratuity Rule", gratuity_rule, "calculate_gratuity_amount_based_on")

	gratuity_amount = 0
	fraction_to_be_paid = 0
	year_left = experience
	for slab in slabs:
		if calculate_gratuity_amount_based_on == "Single Slab":
			if experience >= slab.get("from", 0) and (slab.to == 0 or experience <= slab.to):
				gratuity_amount = total_applicable_components_amount * experience * slab.fraction_of_applicable_earnings
				if slab.fraction_of_applicable_earnings:
					break
		elif calculate_gratuity_amount_based_on == "Sum of all previous slabs":
			if slab.get("to") == 0 and slab.get("from") == 0:
				gratuity_amount += year_left * total_applicable_components_amount * slab.fraction_of_applicable_earnings
				break

			if experience > slab.get("to") and experience > slab.get("from"):
				gratuity_amount += (slab.get("to") - slab.get("from")) * total_applicable_components_amount * slab.fraction_of_applicable_earnings
				year_left -= (slab.get("to") - slab.get("from"))
				print(experience, year_left)
			elif slab.get("from") < experience < slab.get("to"):
				print(year_left)
				gratuity_amount += year_left * total_applicable_components_amount * slab.fraction_of_applicable_earnings



	return gratuity_amount

def get_total_applicable_component_amount(employee, applicable_earnings_component, gratuity_rule):
	sal_slip  = get_last_salary_slip(employee)

	if not sal_slip:
		frappe.throw(_("No Salary Slip is found for Employee: {0}").format(bold(employee)))

	component_and_amounts = frappe.get_list("Salary Detail",
		filters={
			"docstatus": 1,
			'parent': sal_slip,
			"parentfield": "earnings",
			'salary_component': ('in', applicable_earnings_component)
		},
		fields=["amount"])
	total_applicable_components_amount = 0
	if not len(component_and_amounts):
		frappe.throw("No Applicable Component is present in last month salary slip")
	for data in component_and_amounts:
		total_applicable_components_amount += data.amount

	return total_applicable_components_amount

def get_gratuity_rule_slabs(gratuity_rule):
	return frappe.get_all("Gratuity Rule Slab", filters= {'parent': gratuity_rule}, fields = ["*"])

def get_salary_structure(employee):
	return frappe.get_list("Salary Structure Assignment", filters = {"employee": employee, 'docstatus': 1}, fields=["from_date", "salary_structure"], order_by = "from_date desc")[0].salary_structure

def get_last_salary_slip(employee):
	return frappe.get_list("Salary Slip", filters = {"employee": employee, 'docstatus': 1}, order_by = "start_date desc")[0].name




