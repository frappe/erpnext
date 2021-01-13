# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application import get_max_benefits
from erpnext.hr.utils import get_previous_claimed_amount
from erpnext.payroll.doctype.payroll_period.payroll_period import get_payroll_period
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure

class EmployeeBenefitClaim(Document):
	def validate(self):
		max_benefits = get_max_benefits(self.employee, self.claim_date)
		if not max_benefits or max_benefits <= 0:
			frappe.throw(_("Employee {0} has no maximum benefit amount").format(self.employee))
		payroll_period = get_payroll_period(self.claim_date, self.claim_date, frappe.db.get_value("Employee", self.employee, "company"))
		if not payroll_period:
			frappe.throw(_("{0} is not in a valid Payroll Period").format(frappe.format(self.claim_date, dict(fieldtype='Date'))))
		self.validate_max_benefit_for_component(payroll_period)
		self.validate_max_benefit_for_sal_struct(max_benefits)
		self.validate_benefit_claim_amount(max_benefits, payroll_period)
		if self.pay_against_benefit_claim:
			self.validate_non_pro_rata_benefit_claim(max_benefits, payroll_period)

	def validate_benefit_claim_amount(self, max_benefits, payroll_period):
		claimed_amount = self.claimed_amount
		claimed_amount += get_previous_claimed_amount(self.employee, payroll_period)
		if max_benefits < claimed_amount:
			frappe.throw(_("Maximum benefit of employee {0} exceeds {1} by the sum {2} of previous claimed\
			amount").format(self.employee, max_benefits, claimed_amount-max_benefits))

	def validate_max_benefit_for_sal_struct(self, max_benefits):
		if self.claimed_amount > max_benefits:
			frappe.throw(_("Maximum benefit amount of employee {0} exceeds {1}").format(self.employee, max_benefits))

	def validate_max_benefit_for_component(self, payroll_period):
		if self.max_amount_eligible:
			claimed_amount = self.claimed_amount
			claimed_amount += get_previous_claimed_amount(self.employee,
				payroll_period, component = self.earning_component)
			if claimed_amount > self.max_amount_eligible:
				frappe.throw(_("Maximum amount eligible for the component {0} exceeds {1}")
					.format(self.earning_component, self.max_amount_eligible))

	def validate_non_pro_rata_benefit_claim(self, max_benefits, payroll_period):
		claimed_amount = self.claimed_amount
		pro_rata_amount = self.get_pro_rata_amount_in_application(payroll_period.name)
		if not pro_rata_amount:
			pro_rata_amount = 0
			# Get pro_rata_amount if there is no application,
			# get salary structure for the date and calculate pro-rata amount
			sal_struct_name = get_assigned_salary_structure(self.employee, self.claim_date)
			if sal_struct_name:
				sal_struct = frappe.get_doc("Salary Structure", sal_struct_name)
				pro_rata_amount = get_benefit_pro_rata_ratio_amount(self.employee, self.claim_date, sal_struct)

		claimed_amount += get_previous_claimed_amount(self.employee, payroll_period, non_pro_rata = True)
		if max_benefits < pro_rata_amount + claimed_amount:
			frappe.throw(_("Maximum benefit of employee {0} exceeds {1} by the sum {2} of benefit application pro-rata component\
			amount and previous claimed amount").format(self.employee, max_benefits, pro_rata_amount+claimed_amount-max_benefits))

	def get_pro_rata_amount_in_application(self, payroll_period):
		application = frappe.db.exists(
			"Employee Benefit Application",
			{
				'employee': self.employee,
				'payroll_period': payroll_period,
				'docstatus': 1
			}
		)
		if application:
			return frappe.db.get_value("Employee Benefit Application", application, "pro_rata_dispensed_amount")
		return False

def get_benefit_pro_rata_ratio_amount(employee, on_date, sal_struct):
	total_pro_rata_max = 0
	benefit_amount_total = 0
	for sal_struct_row in sal_struct.get("earnings"):
		try:
			pay_against_benefit_claim, max_benefit_amount = frappe.db.get_value("Salary Component", sal_struct_row.salary_component, ["pay_against_benefit_claim", "max_benefit_amount"])
		except TypeError:
			# show the error in tests?
			frappe.throw(_("Unable to find Salary Component {0}").format(sal_struct_row.salary_component))
		if sal_struct_row.is_flexible_benefit == 1 and pay_against_benefit_claim != 1:
			total_pro_rata_max += max_benefit_amount
	if total_pro_rata_max > 0:
		for sal_struct_row in sal_struct.get("earnings"):
			pay_against_benefit_claim, max_benefit_amount = frappe.db.get_value("Salary Component", sal_struct_row.salary_component, ["pay_against_benefit_claim", "max_benefit_amount"])

			if sal_struct_row.is_flexible_benefit == 1 and pay_against_benefit_claim != 1:
				component_max = max_benefit_amount
				benefit_amount = component_max * sal_struct.max_benefits / total_pro_rata_max
				if benefit_amount > component_max:
					benefit_amount = component_max
				benefit_amount_total += benefit_amount
	return benefit_amount_total

def get_benefit_claim_amount(employee, start_date, end_date, salary_component=None):
	query = """
		select sum(claimed_amount)
		from `tabEmployee Benefit Claim`
		where
			employee=%(employee)s
			and docstatus = 1
			and pay_against_benefit_claim = 1
			and claim_date between %(start_date)s and %(end_date)s
	"""

	if salary_component:
		query += " and earning_component = %(earning_component)s"

	claimed_amount = flt(frappe.db.sql(query, {
		'employee': employee,
		'start_date': start_date,
		'end_date': end_date,
		'earning_component': salary_component
	})[0][0])

	return claimed_amount

def get_total_benefit_dispensed(employee, sal_struct, sal_slip_start_date, payroll_period):
	pro_rata_amount = 0
	claimed_amount = 0
	application = frappe.db.exists(
		"Employee Benefit Application",
		{
			'employee': employee,
			'payroll_period': payroll_period.name,
			'docstatus': 1
		}
	)
	if application:
		application_obj = frappe.get_doc("Employee Benefit Application", application)
		pro_rata_amount = application_obj.pro_rata_dispensed_amount + application_obj.max_benefits - application_obj.remaining_benefit
	else:
		pro_rata_amount = get_benefit_pro_rata_ratio_amount(employee, sal_slip_start_date, sal_struct)

	claimed_amount += get_benefit_claim_amount(employee, payroll_period.start_date, payroll_period.end_date)

	return claimed_amount + pro_rata_amount

def get_last_payroll_period_benefits(employee, sal_slip_start_date, sal_slip_end_date, payroll_period,  sal_struct):
	max_benefits = get_max_benefits(employee, payroll_period.end_date)
	if not max_benefits:
		max_benefits = 0
	remaining_benefit = max_benefits - get_total_benefit_dispensed(employee, sal_struct, sal_slip_start_date, payroll_period)
	if remaining_benefit > 0:
		have_remaining = True
		# Set the remaining benefits to flexi non pro-rata component in the salary structure
		salary_components_array = []
		for d in sal_struct.get("earnings"):
			if d.is_flexible_benefit == 1:
				salary_component = frappe.get_doc("Salary Component", d.salary_component)
				if salary_component.pay_against_benefit_claim == 1:
					claimed_amount = get_benefit_claim_amount(employee, payroll_period.start_date, sal_slip_end_date, d.salary_component)
					amount_fit_to_component = salary_component.max_benefit_amount - claimed_amount
					if amount_fit_to_component > 0:
						if remaining_benefit > amount_fit_to_component:
							amount = amount_fit_to_component
							remaining_benefit -= amount_fit_to_component
						else:
							amount = remaining_benefit
							have_remaining = False
						current_claimed_amount = get_benefit_claim_amount(employee, sal_slip_start_date, sal_slip_end_date, d.salary_component)
						amount += current_claimed_amount
						struct_row = {}
						salary_components_dict = {}
						struct_row['depends_on_payment_days'] = salary_component.depends_on_payment_days
						struct_row['salary_component'] = salary_component.name
						struct_row['abbr'] = salary_component.salary_component_abbr
						struct_row['do_not_include_in_total'] = salary_component.do_not_include_in_total
						struct_row['is_tax_applicable'] = salary_component.is_tax_applicable,
						struct_row['is_flexible_benefit'] = salary_component.is_flexible_benefit,
						struct_row['variable_based_on_taxable_salary'] = salary_component.variable_based_on_taxable_salary
						salary_components_dict['amount'] = amount
						salary_components_dict['struct_row'] = struct_row
						salary_components_array.append(salary_components_dict)
			if not have_remaining:
				break

		if len(salary_components_array) > 0:
			return salary_components_array

	return False
