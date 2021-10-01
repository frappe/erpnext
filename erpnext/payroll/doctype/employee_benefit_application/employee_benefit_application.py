# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, cstr, date_diff, getdate, rounded

from erpnext.hr.utils import (
	get_holiday_dates_for_employee,
	get_previous_claimed_amount,
	get_sal_slip_total_benefit_given,
	validate_active_employee,
)
from erpnext.payroll.doctype.payroll_period.payroll_period import (
	get_payroll_period_days,
	get_period_factor,
)
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	get_assigned_salary_structure,
)


class EmployeeBenefitApplication(Document):
	def validate(self):
		validate_active_employee(self.employee)
		self.validate_duplicate_on_payroll_period()
		if not self.max_benefits:
			self.max_benefits = get_max_benefits_remaining(self.employee, self.date, self.payroll_period)
		if self.max_benefits and self.max_benefits > 0:
			self.validate_max_benefit_for_component()
			self.validate_prev_benefit_claim()
			if self.remaining_benefit > 0:
				self.validate_remaining_benefit_amount()
		else:
			frappe.throw(_("As per your assigned Salary Structure you cannot apply for benefits").format(self.employee))

	def validate_prev_benefit_claim(self):
		if self.employee_benefits:
			for benefit in self.employee_benefits:
				if benefit.pay_against_benefit_claim == 1:
					payroll_period = frappe.get_doc("Payroll Period", self.payroll_period)
					benefit_claimed = get_previous_claimed_amount(self.employee, payroll_period, component = benefit.earning_component)
					benefit_given = get_sal_slip_total_benefit_given(self.employee, payroll_period, component = benefit.earning_component)
					benefit_claim_remining = benefit_claimed - benefit_given
					if benefit_claimed > 0 and benefit_claim_remining > benefit.amount:
						frappe.throw(_("An amount of {0} already claimed for the component {1}, set the amount equal or greater than {2}").format(
							benefit_claimed, benefit.earning_component, benefit_claim_remining))

	def validate_remaining_benefit_amount(self):
		# check salary structure earnings have flexi component (sum of max_benefit_amount)
		# without pro-rata which satisfy the remaining_benefit
		# else pro-rata component for the amount
		# again comes the same validation and satisfy or throw
		benefit_components = []
		if self.employee_benefits:
			for employee_benefit in self.employee_benefits:
				benefit_components.append(employee_benefit.earning_component)
		salary_struct_name = get_assigned_salary_structure(self.employee, self.date)
		if salary_struct_name:
			non_pro_rata_amount = 0
			pro_rata_amount = 0
			salary_structure = frappe.get_doc("Salary Structure", salary_struct_name)
			if salary_structure.earnings:
				for earnings in salary_structure.earnings:
					if earnings.is_flexible_benefit == 1 and earnings.salary_component not in benefit_components:
						pay_against_benefit_claim, max_benefit_amount = frappe.db.get_value("Salary Component", earnings.salary_component, ["pay_against_benefit_claim", "max_benefit_amount"])
						if pay_against_benefit_claim != 1:
							pro_rata_amount += max_benefit_amount
						else:
							non_pro_rata_amount += max_benefit_amount

			if pro_rata_amount == 0  and non_pro_rata_amount == 0:
				frappe.throw(_("Please add the remaining benefits {0} to any of the existing component").format(self.remaining_benefit))
			elif non_pro_rata_amount > 0 and non_pro_rata_amount < rounded(self.remaining_benefit):
				frappe.throw(_("You can claim only an amount of {0}, the rest amount {1} should be in the application as pro-rata component").format(
					non_pro_rata_amount, self.remaining_benefit - non_pro_rata_amount))
			elif non_pro_rata_amount == 0:
				frappe.throw(_("Please add the remaining benefits {0} to the application as pro-rata component").format(
					self.remaining_benefit))

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
		prev_sal_slip_flexi_amount = get_sal_slip_total_benefit_given(self.employee, frappe.get_doc("Payroll Period", self.payroll_period), earning_component_name)
		benefit_amount += prev_sal_slip_flexi_amount
		if rounded(benefit_amount, 2) > max_benefit_amount:
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
	sal_struct = get_assigned_salary_structure(employee, on_date)
	if sal_struct:
		max_benefits = frappe.db.get_value("Salary Structure", sal_struct, "max_benefits")
		if max_benefits > 0:
			return max_benefits
	return False

@frappe.whitelist()
def get_max_benefits_remaining(employee, on_date, payroll_period):
	max_benefits = get_max_benefits(employee, on_date)
	if max_benefits and max_benefits > 0:
		have_depends_on_payment_days = False
		per_day_amount_total = 0
		payroll_period_days = get_payroll_period_days(on_date, on_date, employee)[1]
		payroll_period_obj = frappe.get_doc("Payroll Period", payroll_period)

		# Get all salary slip flexi amount in the payroll period
		prev_sal_slip_flexi_total = get_sal_slip_total_benefit_given(employee, payroll_period_obj)

		if prev_sal_slip_flexi_total > 0:
			# Check salary structure hold depends_on_payment_days component
			# If yes then find the amount per day of each component and find the sum
			sal_struct_name = get_assigned_salary_structure(employee, on_date)
			if sal_struct_name:
				sal_struct = frappe.get_doc("Salary Structure", sal_struct_name)
				for sal_struct_row in sal_struct.get("earnings"):
					salary_component = frappe.get_doc("Salary Component", sal_struct_row.salary_component)
					if salary_component.depends_on_payment_days == 1 and salary_component.pay_against_benefit_claim != 1:
						have_depends_on_payment_days = True
						benefit_amount = get_benefit_amount_based_on_pro_rata(sal_struct, salary_component.max_benefit_amount)
						amount_per_day = benefit_amount / payroll_period_days
						per_day_amount_total += amount_per_day

			# Then the sum multiply with the no of lwp in that period
			# Include that amount to the prev_sal_slip_flexi_total to get the actual
			if have_depends_on_payment_days and per_day_amount_total > 0:
				holidays = get_holiday_dates_for_employee(employee, payroll_period_obj.start_date, on_date)
				working_days = date_diff(on_date, payroll_period_obj.start_date) + 1
				leave_days = calculate_lwp(employee, payroll_period_obj.start_date, holidays, working_days)
				leave_days_amount = leave_days * per_day_amount_total
				prev_sal_slip_flexi_total += leave_days_amount

			return max_benefits - prev_sal_slip_flexi_total
	return max_benefits

def calculate_lwp(employee, start_date, holidays, working_days):
	lwp = 0
	holidays = "','".join(holidays)
	for d in range(working_days):
		dt = add_days(cstr(getdate(start_date)), d)
		leave = frappe.db.sql("""
			select t1.name, t1.half_day
			from `tabLeave Application` t1, `tabLeave Type` t2
			where t2.name = t1.leave_type
			and t2.is_lwp = 1
			and t1.docstatus = 1
			and t1.employee = %(employee)s
			and CASE WHEN t2.include_holiday != 1 THEN %(dt)s not in ('{0}') and %(dt)s between from_date and to_date
			WHEN t2.include_holiday THEN %(dt)s between from_date and to_date
			END
			""".format(holidays), {"employee": employee, "dt": dt})
		if leave:
			lwp = cint(leave[0][1]) and (lwp + 0.5) or (lwp + 1)
	return lwp

def get_benefit_component_amount(employee, start_date, end_date, salary_component, sal_struct, payroll_frequency, payroll_period):
	if not payroll_period:
		frappe.msgprint(_("Start and end dates not in a valid Payroll Period, cannot calculate {0}")
			.format(salary_component))
		return False

	# Considering there is only one application for a year
	benefit_application = frappe.db.sql("""
		select name
		from `tabEmployee Benefit Application`
		where
			payroll_period=%(payroll_period)s
			and employee=%(employee)s
			and docstatus = 1
	""", {
		'employee': employee,
		'payroll_period': payroll_period.name
	})

	current_benefit_amount = 0.0
	component_max_benefit, depends_on_payment_days = frappe.db.get_value("Salary Component",
		salary_component, ["max_benefit_amount", "depends_on_payment_days"])

	benefit_amount = 0
	if benefit_application:
		benefit_amount = frappe.db.get_value("Employee Benefit Application Detail",
			{"parent": benefit_application[0][0], "earning_component": salary_component}, "amount")
	elif component_max_benefit:
		benefit_amount = get_benefit_amount_based_on_pro_rata(sal_struct, component_max_benefit)

	current_benefit_amount = 0
	if benefit_amount:
		total_sub_periods = get_period_factor(employee,
			start_date, end_date, payroll_frequency, payroll_period, depends_on_payment_days)[0]

		current_benefit_amount = benefit_amount / total_sub_periods

	return current_benefit_amount

def get_benefit_amount_based_on_pro_rata(sal_struct, component_max_benefit):
	max_benefits_total = 0
	benefit_amount = 0
	for d in sal_struct.get("earnings"):
		if d.is_flexible_benefit == 1:
			component = frappe.db.get_value("Salary Component", d.salary_component, ["max_benefit_amount", "pay_against_benefit_claim"], as_dict=1)
			if not component.pay_against_benefit_claim:
				max_benefits_total += component.max_benefit_amount

	if max_benefits_total > 0:
		benefit_amount = sal_struct.max_benefits * component.max_benefit_amount / max_benefits_total
		if benefit_amount > component_max_benefit:
			benefit_amount = component_max_benefit

	return benefit_amount

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_earning_components(doctype, txt, searchfield, start, page_len, filters):
	if len(filters) < 2:
		return {}

	salary_structure = get_assigned_salary_structure(filters['employee'], filters['date'])

	if salary_structure:
		return frappe.db.sql("""
			select salary_component
			from `tabSalary Detail`
			where parent = %s and is_flexible_benefit = 1
			order by name
		""", salary_structure)
	else:
		frappe.throw(_("Salary Structure not found for employee {0} and date {1}")
			.format(filters['employee'], filters['date']))

@frappe.whitelist()
def get_earning_components_max_benefits(employee, date, earning_component):
	salary_structure = get_assigned_salary_structure(employee, date)
	amount = frappe.db.sql("""
			select amount
			from `tabSalary Detail`
			where parent = %s and is_flexible_benefit = 1
			and salary_component = %s
			order by name
		""", salary_structure, earning_component)

	return amount if amount else 0
