# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, getdate, rounded, add_days, cstr, cint
from frappe.model.document import Document
from erpnext.hr.doctype.payroll_period.payroll_period import get_payroll_period_days
from erpnext.hr.doctype.salary_structure_assignment.salary_structure_assignment import get_assigned_salary_structure
from erpnext.hr.utils import get_sal_slip_total_benefit_given, get_holidays_for_employee, get_previous_claimed_amount

class EmployeeBenefitApplication(Document):
	def validate(self):
		self.validate_duplicate_on_payroll_period()
		if self.max_benefits <= 0:
			frappe.throw(_("Employee {0} has no maximum benefit amount").format(self.employee))
		self.validate_max_benefit_for_component()
		self.validate_prev_benefit_claim()
		if self.remainig_benefits > 0:
			self.validate_remaining_benefit_amount()

	def validate_prev_benefit_claim(self):
		if self.employee_benefits:
			for benefit in self.employee_benefits:
				if benefit.pay_against_benefit_claim == 1:
					payroll_period = frappe.get_doc("Payroll Period", self.payroll_period)
					benefit_claimed = get_previous_claimed_amount(self.employee, payroll_period, component = benefit.earning_component)
					benefit_given = get_sal_slip_total_benefit_given(self.employee, payroll_period, component = benefit.earning_component)
					benefit_claim_remining = benefit_claimed - benefit_given
					if benefit_claimed > 0 and benefit_claim_remining > benefit.amount:
						frappe.throw(_("An amount of {0} already claimed for the component {1},\
						 set the amount equal or greater than {2}").format(benefit_claimed, benefit.earning_component, benefit_claim_remining))

	def validate_remaining_benefit_amount(self):
		# check salary structure earnings have flexi component (sum of max_benefit_amount)
		# without pro-rata which satisfy the remainig_benefits
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
				frappe.throw(_("Please add the remainig benefits {0} to any of the existing component").format(self.remainig_benefits))
			elif non_pro_rata_amount > 0 and non_pro_rata_amount < rounded(self.remainig_benefits):
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
		have_depends_on_lwp = False
		per_day_amount_total = 0
		payroll_period_days = get_payroll_period_days(on_date, on_date, employee)
		payroll_period_obj = frappe.get_doc("Payroll Period", payroll_period)

		# Get all salary slip flexi amount in the payroll period
		prev_sal_slip_flexi_total = get_sal_slip_total_benefit_given(employee, payroll_period_obj)

		if prev_sal_slip_flexi_total > 0:
			# Check salary structure hold depends_on_lwp component
			# If yes then find the amount per day of each component and find the sum
			sal_struct_name = get_assigned_salary_structure(employee, on_date)
			if sal_struct_name:
				sal_struct = frappe.get_doc("Salary Structure", sal_struct_name)
				for sal_struct_row in sal_struct.get("earnings"):
					salary_component = frappe.get_doc("Salary Component", sal_struct_row.salary_component)
					if salary_component.depends_on_lwp == 1 and salary_component.pay_against_benefit_claim != 1:
						have_depends_on_lwp = True
						benefit_amount = get_benefit_pro_rata_ratio_amount(sal_struct, salary_component.max_benefit_amount)
						amount_per_day = benefit_amount / payroll_period_days
						per_day_amount_total += amount_per_day

			# Then the sum multiply with the no of lwp in that period
			# Include that amount to the prev_sal_slip_flexi_total to get the actual
			if have_depends_on_lwp and per_day_amount_total > 0:
				holidays = get_holidays_for_employee(employee, payroll_period_obj.start_date, on_date)
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

def get_benefit_component_amount(employee, start_date, end_date, struct_row, sal_struct, payment_days, working_days):
	# Considering there is only one application for an year
	benefit_application_name = frappe.db.sql("""
	select name from `tabEmployee Benefit Application`
	where employee=%(employee)s
	and docstatus = 1
	and (date between %(start_date)s and %(end_date)s)
	""", {
		'employee': employee,
		'start_date': start_date,
		'end_date': end_date
	})

	payroll_period_days = get_payroll_period_days(start_date, end_date, employee)
	if payroll_period_days:
		depends_on_lwp = frappe.db.get_value("Salary Component", struct_row.salary_component, "depends_on_lwp")
		if depends_on_lwp != 1:
			payment_days = working_days

		# If there is application for benefit then fetch the amount from the application.
		# else Split the max benefits to the pro-rata components with the ratio of thier max_benefit_amount
		if benefit_application_name:
			benefit_application = frappe.get_doc("Employee Benefit Application", benefit_application_name[0][0])
			return get_benefit_amount(benefit_application, struct_row, payroll_period_days, payment_days)

		# TODO: Check if there is benefit claim for employee then pro-rata devid the rest of amount (Late Benefit Application)
		else:
			component_max = frappe.db.get_value("Salary Component", struct_row.salary_component, "max_benefit_amount")
			if component_max > 0:
				benefit_amount = get_benefit_pro_rata_ratio_amount(sal_struct, component_max)
				return get_amount(payroll_period_days, benefit_amount, payment_days)
	return False

def get_benefit_pro_rata_ratio_amount(sal_struct, component_max):
	total_pro_rata_max = 0
	benefit_amount = 0
	for sal_struct_row in sal_struct.get("earnings"):
		pay_against_benefit_claim, max_benefit_amount = frappe.db.get_value("Salary Component", sal_struct_row.salary_component, ["pay_against_benefit_claim", "max_benefit_amount"])
		if sal_struct_row.is_flexible_benefit == 1 and pay_against_benefit_claim != 1:
			total_pro_rata_max += max_benefit_amount
	if total_pro_rata_max > 0:
		benefit_amount = component_max * sal_struct.max_benefits / total_pro_rata_max
		if benefit_amount > component_max:
			benefit_amount = component_max
	return benefit_amount

def get_benefit_amount(application, struct_row, payroll_period_days, payment_days):
	amount = 0
	for employee_benefit in application.employee_benefits:
		if employee_benefit.earning_component == struct_row.salary_component:
			amount += get_amount(payroll_period_days, employee_benefit.amount, payment_days)
	return amount if amount > 0 else False

def get_amount(payroll_period_days, amount, payment_days):
	amount_per_day = amount / payroll_period_days
	total_amount = amount_per_day * payment_days
	return total_amount

def get_earning_components(doctype, txt, searchfield, start, page_len, filters):
	if len(filters) < 2:
		return {}
	employee = filters['employee']
	date = filters['date']
	salary_structure = get_assigned_salary_structure(employee, date)

	if salary_structure:
		query = """select salary_component from `tabSalary Detail` where parent = '{salary_structure}'
		and is_flexible_benefit = 1
		order by name"""

		return frappe.db.sql(query.format(**{
			"salary_structure": salary_structure
		}))

	return {}
