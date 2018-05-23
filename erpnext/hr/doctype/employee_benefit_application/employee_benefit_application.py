# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, date_diff, getdate
from frappe.model.document import Document
from erpnext.hr.doctype.payroll_period.payroll_period import get_payroll_period_days
from frappe.desk.reportview import get_match_cond

class EmployeeBenefitApplication(Document):
	def validate(self):
		self.validate_duplicate_on_payroll_period()
		if self.max_benefits <= 0:
			frappe.throw(_("Employee {0} has no maximum benefit amount").format(self.employee))
		self.validate_max_benefit_for_component()
		if self.remainig_benefits > 0:
			self.validate_remaining_benefit_amount()

	def validate_remaining_benefit_amount(self):
		# check salary structure earnings have flexi component (sum of max_benefit_amount)
		# without pro-rata which satisfy the remainig_benefits
		# else pro-rata component for the amount
		# again comes the same validation and satisfy or throw
		benefit_components = []
		if self.employee_benefits:
			for employee_benefit in self.employee_benefits:
				benefit_components.append(employee_benefit.earning_component)
		salary_struct_name = get_assigned_salary_sturecture(self.employee, self.date)
		if len(salary_struct_name) > 0:
			non_pro_rata_amount = 0
			pro_rata_amount = 0
			salary_structure = frappe.get_doc("Salary Structure", salary_struct_name[0][0])
			if salary_structure.earnings:
				for earnings in salary_structure.earnings:
					if earnings.is_flexible_benefit == 1 and earnings.salary_component not in benefit_components:
						is_pro_rata_applicable, max_benefit_amount = frappe.db.get_value("Salary Component", earnings.salary_component, ["is_pro_rata_applicable", "max_benefit_amount"])
						if is_pro_rata_applicable == 1:
							pro_rata_amount += max_benefit_amount
						else:
							non_pro_rata_amount += max_benefit_amount
			if pro_rata_amount == 0  and non_pro_rata_amount == 0:
				frappe.throw(_("Please add the remainig benefits {0} to any of the existing component").format(self.remainig_benefits))
			elif non_pro_rata_amount > 0 and non_pro_rata_amount < self.remainig_benefits:
				frappe.throw(_("You can claim only an amount of {0}, the rest amount {1} should be in the application \
				as pro-rata component").format(non_pro_rata_amount, self.remainig_benefits - non_pro_rata_amount))
			elif non_pro_rata_amount == 0:
				frappe.throw(_("Please add the remainig benefits {0} to the application as \
				pro-rata component").format(self.remainig_benefits))

	def validate_max_benefit_for_component(self):
		if self.employee_benefits:
			max_benefit_amount = 0
			for employee_benefit in self.employee_benefits:
				self.validate_max_benefit(employee_benefit.earning_component)
				max_benefit_amount += employee_benefit.amount
			if max_benefit_amount > self.max_benefits:
				frappe.throw(_("Maximum benefit amount of employee {0} exceeds {1}").format(self.employee, self.max_benefits))

	def validate_max_benefit(self, earning_component_name):
		max_benefit_amount = frappe.db.get_value("Salary Component", earning_component_name, "max_benefit_amount")
		benefit_amount = 0
		for employee_benefit in self.employee_benefits:
			if employee_benefit.earning_component == earning_component_name:
				benefit_amount += employee_benefit.amount
		if benefit_amount > max_benefit_amount:
			frappe.throw(_("Maximum benefit amount of component {0} exceeds {1}").format(earning_component_name, max_benefit_amount))

	def validate_duplicate_on_payroll_period(self):
		application = frappe.db.exists(
			"Employee Benefit Application",
			{
				'employee': self.employee,
				'payroll_period': self.payroll_period,
				'docstatus': 1
			}
		)
		if application:
			frappe.throw(_("Employee {0} already submited an apllication {1} for the payroll period {2}").format(self.employee, application, self.payroll_period))

@frappe.whitelist()
def get_max_benefits(employee, on_date):
	sal_struct = get_assigned_salary_sturecture(employee, on_date)
	if sal_struct:
		max_benefits = frappe.db.get_value("Salary Structure", sal_struct[0][0], "max_benefits")
		if max_benefits > 0:
			return max_benefits
		else:
			frappe.throw(_("Employee {0} has no max benefits in salary structure {1}").format(employee, sal_struct[0][0]))
	else:
		frappe.throw(_("Employee {0} has no salary structure assigned").format(employee))


@frappe.whitelist()
def get_assigned_salary_sturecture(employee, _date):
	if not _date:
		_date = nowdate()
	salary_structure = frappe.db.sql("""
		select salary_structure from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and (
			(%(_date)s between from_date and ifnull(to_date, '2199-12-31'))
		)""", {
			'employee': employee,
			'_date': _date,
		})
	if salary_structure:
		return salary_structure

def get_employee_benefit_application(employee, start_date, end_date):
	employee_benefits = frappe.db.sql("""
	select name from `tabEmployee Benefit Application`
	where employee=%(employee)s
	and docstatus = 1
	and (date between %(start_date)s and %(end_date)s)
	""", {
		'employee': employee,
		'start_date': start_date,
		'end_date': end_date
	})

	if employee_benefits:
		for employee_benefit in employee_benefits:
			employee_benefit_obj = frappe.get_doc("Employee Benefit Application", employee_benefit[0])
			return get_benefit_components(employee_benefit_obj, employee, start_date, end_date)

def get_benefit_components(employee_benefit_application, employee, start_date, end_date):
	salary_components_array = []
	group_component_amount = {}
	payroll_period_days = get_payroll_period_days(start_date, end_date, frappe.db.get_value("Employee", employee, "company"))
	for employee_benefit in employee_benefit_application.employee_benefits:
		if employee_benefit.is_pro_rata_applicable == 1:
			struct_row = {}
			salary_components_dict = {}
			amount = get_amount(payroll_period_days, start_date, end_date, employee_benefit.amount)
			sc = frappe.get_doc("Salary Component", employee_benefit.earning_component)
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

def get_amount(payroll_period_days, start_date, end_date, amount):
	salary_slip_days = date_diff(getdate(end_date), getdate(start_date)) + 1
	amount_per_day = amount / payroll_period_days
	total_amount = amount_per_day * salary_slip_days
	return total_amount

def get_earning_components(doctype, txt, searchfield, start, page_len, filters):
	if len(filters) < 2:
		return {}
	employee = filters['employee']
	date = filters['date']
	salary_structure = get_assigned_salary_sturecture(employee, date)

	if len(salary_structure) > 0:
		query = """select salary_component from `tabSalary Detail` where parent = '{salary_structure}'
		and is_flexible_benefit = 1
		order by name"""

		return frappe.db.sql(query.format(**{
			"salary_structure": salary_structure[0][0]
		}))

	return {}
