# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.hr.doctype.employee_benefit_application.employee_benefit_application import get_max_benefits
from erpnext.hr.utils import get_payroll_period
from erpnext.hr.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure

class EmployeeBenefitClaim(Document):
	def validate(self):
		max_benefits = get_max_benefits(self.employee, self.claim_date)
		payroll_period = get_payroll_period(self.claim_date, self.claim_date, frappe.db.get_value("Employee", self.employee, "company"))
		self.validate_max_benefit_for_component(payroll_period)
		self.validate_max_benefit_for_sal_struct(max_benefits)
		self.validate_benefit_claim_amount(max_benefits, payroll_period)
		if not self.is_pro_rata_applicable:
			self.validate_non_pro_rata_benefit_claim(max_benefits, payroll_period)

	def validate_benefit_claim_amount(self, max_benefits, payroll_period):
		claimed_amount = self.claimed_amount
		claimed_amount += self.get_previous_claimed_amount(payroll_period)
		if max_benefits < claimed_amount:
			frappe.throw(_("Maximum benefit of employee {0} exceeds {1} by the sum {2} of previous claimed\
			amount").format(self.employee, max_benefits, claimed_amount-max_benefits))

	def validate_max_benefit_for_sal_struct(self, max_benefits):
		if self.claimed_amount > max_benefits:
			frappe.throw(_("Maximum benefit amount of employee {0} exceeds {1}").format(self.employee, max_benefits))

	def validate_max_benefit_for_component(self, payroll_period):
		claimed_amount = self.claimed_amount
		claimed_amount += self.get_previous_claimed_amount(payroll_period, self.earning_component)
		if claimed_amount > self.max_amount_eligible:
			frappe.throw(_("Maximum amount eligible for the component {0} exceeds {1}").format(self.earning_component, self.max_amount_eligible))

	def validate_non_pro_rata_benefit_claim(self, max_benefits, payroll_period):
		claimed_amount = self.claimed_amount
		pro_rata_amount = self.get_pro_rata_amount_in_application(payroll_period.name)
		if not pro_rata_amount:
			# Get pro_rata_amount if there is no application,
			# get salary structure for the date and calculate pro-rata amount
			pro_rata_amount = self.get_benefit_pro_rata_ratio_amount()
		if not pro_rata_amount:
			pro_rata_amount = 0

		claimed_amount += self.get_previous_claimed_amount(payroll_period, True)
		if max_benefits < pro_rata_amount + claimed_amount:
			frappe.throw(_("Maximum benefit of employee {0} exceeds {1} by the sum {2} of benefit application pro-rata component\
			amount and previous claimed amount").format(self.employee, max_benefits, pro_rata_amount+claimed_amount-max_benefits))

	def get_benefit_pro_rata_ratio_amount(self):
		sal_struct_name = get_assigned_salary_structure(self.employee, self.claim_date)
		if sal_struct_name:
			sal_struct = frappe.get_doc("Salary Structure", sal_struct_name)
			total_pro_rata_max = 0
			benefit_amount_total = 0
			for sal_struct_row in sal_struct.get("earnings"):
				is_pro_rata_applicable, max_benefit_amount = frappe.db.get_value("Salary Component", sal_struct_row.salary_component, ["is_pro_rata_applicable", "max_benefit_amount"])
				if sal_struct_row.is_flexible_benefit == 1 and is_pro_rata_applicable == 1:
					total_pro_rata_max += max_benefit_amount
			if total_pro_rata_max > 0:
				for sal_struct_row in sal_struct.get("earnings"):
					is_pro_rata_applicable, max_benefit_amount = frappe.db.get_value("Salary Component", sal_struct_row.salary_component, ["is_pro_rata_applicable", "max_benefit_amount"])
					if sal_struct_row.is_flexible_benefit == 1 and is_pro_rata_applicable == 1:
						component_max = max_benefit_amount
						benefit_amount = component_max * sal_struct.max_benefits / total_pro_rata_max
						if benefit_amount > component_max:
							benefit_amount = component_max
						benefit_amount_total += benefit_amount
				return benefit_amount_total
		return False

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

	def get_previous_claimed_amount(self, payroll_period, non_pro_rata=False, component=False):
		total_claimed_amount = 0
		query = """
		select sum(claimed_amount) as 'total_amount'
		from `tabEmployee Benefit Claim`
		where employee=%(employee)s
		and docstatus = 1
		and (claim_date between %(start_date)s and %(end_date)s)
		"""
		if non_pro_rata:
			query += "and is_pro_rata_applicable = 0"
		if component:
			query += "and earning_component = %(component)s"

		sum_of_claimed_amount = frappe.db.sql(query, {
			'employee': self.employee,
			'start_date': payroll_period.start_date,
			'end_date': payroll_period.end_date,
			'component': component
		}, as_dict=True)
		if sum_of_claimed_amount and sum_of_claimed_amount[0].total_amount > 0:
			total_claimed_amount = sum_of_claimed_amount[0].total_amount
		return total_claimed_amount

def get_benefit_claim_amount(employee, start_date, end_date, struct_row):
	benefit_claim_details = frappe.db.sql("""
	select claimed_amount from `tabEmployee Benefit Claim`
	where employee=%(employee)s
	and docstatus = 1 and is_pro_rata_applicable = 0
	and earning_component = %(earning_component)s
	and (claim_date between %(start_date)s and %(end_date)s)
	""", {
		'employee': employee,
		'start_date': start_date,
		'end_date': end_date,
		'earning_component': struct_row.salary_component
	}, as_dict = True)

	if benefit_claim_details:
		claimed_amount = 0
		for claim_detail in benefit_claim_details:
			claimed_amount += claim_detail.claimed_amount
		return claimed_amount
	return False
