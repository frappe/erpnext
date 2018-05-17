# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.hr.doctype.employee_benefit_application.employee_benefit_application import get_max_benefits
from erpnext.hr.utils import get_payroll_period

class EmployeeBenefitClaim(Document):
	def validate(self):
		max_benefits = get_max_benefits(self.employee, self.claim_date)
		self.validate_max_benefit_for_component()
		self.validate_max_benefit_for_sal_struct(max_benefits)
		payroll_period = get_payroll_period(self.claim_date, self.claim_date, frappe.db.get_value("Employee", self.employee, "company"))
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

	def validate_max_benefit_for_component(self):
		if self.claimed_amount > self.max_amount_eligible:
			frappe.throw(_("Maximum amount eligible for the component {0} exceeds {1}").format(self.earning_component, self.max_amount_eligible))

	def validate_non_pro_rata_benefit_claim(self, max_benefits, payroll_period):
		claimed_amount = self.claimed_amount
		pro_rata_amount = self.get_pro_rata_amount_in_application(payroll_period.name)
		claimed_amount += self.get_previous_claimed_amount(payroll_period, True)
		if max_benefits < pro_rata_amount + claimed_amount:
			frappe.throw(_("Maximum benefit of employee {0} exceeds {1} by the sum {2} of benefit application pro-rata component\
			amount and previous claimed amount").format(self.employee, max_benefits, pro_rata_amount+claimed_amount-max_benefits))

	def get_pro_rata_amount_in_application(self, payroll_period):
		pro_rata_dispensed_amount = 0
		application = frappe.db.exists(
			"Employee Benefit Application",
			{
				'employee': self.employee,
				'payroll_period': payroll_period,
				'docstatus': 1
			}
		)
		if application:
			pro_rata_dispensed_amount = frappe.db.get_value("Employee Benefit Application", application, "pro_rata_dispensed_amount")
		return pro_rata_dispensed_amount

	def get_previous_claimed_amount(self, payroll_period, non_pro_rata=False):
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

		sum_of_claimed_amount = frappe.db.sql(query, {
			'employee': self.employee,
			'start_date': payroll_period.start_date,
			'end_date': payroll_period.end_date
		}, as_dict=True)
		if sum_of_claimed_amount:
			total_claimed_amount = sum_of_claimed_amount[0].total_amount
		return total_claimed_amount

def get_employee_benefit_claim(employee, start_date, end_date):
	employee_benefits = frappe.db.sql("""
	select name from `tabEmployee Benefit Claim`
	where employee=%(employee)s
	and docstatus = 1 and is_pro_rata_applicable = 0
	and (claim_date between %(start_date)s and %(end_date)s)
	""", {
		'employee': employee,
		'start_date': start_date,
		'end_date': end_date
	})

	if employee_benefits:
		salary_components_array = []
		for employee_benefit in employee_benefits:
			struct_row = {}
			salary_components_dict = {}
			group_component_amount = {}

			employee_benefit_claim = frappe.get_doc("Employee Benefit Claim", employee_benefit[0])
			amount = employee_benefit_claim.claimed_amount
			sc = frappe.get_doc("Salary Component", employee_benefit_claim.earning_component)

			salary_component = sc
			if sc.earning_component_group and not sc.is_group and not sc.flexi_default:
				salary_component = frappe.get_doc("Salary Component", sc.earning_component_group)
				if group_component_amount and group_component_amount.has_key(sc.earning_component_group):
					group_component_amount[sc.earning_component_group] += amount
				else:
					group_component_amount[sc.earning_component_group] = amount
				amount = group_component_amount[sc.earning_component_group]

			struct_row['depends_on_lwp'] = salary_component.depends_on_lwp
			struct_row['salary_component'] = salary_component.name
			struct_row['abbr'] = salary_component.salary_component_abbr
			struct_row['do_not_include_in_total'] = salary_component.do_not_include_in_total
			salary_components_dict['amount'] = amount
			salary_components_dict['struct_row'] = struct_row
			salary_components_array.append(salary_components_dict)

		if len(salary_components_array) > 0:
			return salary_components_array
	return False
