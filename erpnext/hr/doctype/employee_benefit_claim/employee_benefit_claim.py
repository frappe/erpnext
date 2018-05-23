# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.hr.doctype.employee_benefit_application.employee_benefit_application import get_max_benefits

class EmployeeBenefitClaim(Document):
	def validate(self):
		if not self.is_pro_rata_applicable:
			self.validate_max_benefit_for_sal_struct()
		# TODO: Validate all cases

	def validate_max_benefit_for_sal_struct(self):
		max_benefits = get_max_benefits(self.employee, self.claim_date)
		if self.claimed_amount > max_benefits:
			frappe.throw(_("Maximum benefit amount of employee {0} exceeds {1}").format(self.employee, max_benefits))


def get_employee_benefit_claim(salary_slip):
	employee_benefits = frappe.db.sql("""
	select name from `tabEmployee Benefit Claim`
	where employee=%(employee)s
	and docstatus = 1 and is_pro_rata_applicable = 0
	and (claim_date between %(start_date)s and %(end_date)s)
	""", {
		'employee': salary_slip.employee,
		'start_date': salary_slip.start_date,
		'end_date': salary_slip.end_date
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
