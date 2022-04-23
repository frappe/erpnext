# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, getdate, formatdate, cint, month_diff, flt, add_months
from frappe.model.document import Document
from erpnext.hr.utils import get_holidays_for_employee

class PayrollPeriod(Document):
	def validate(self):
		self.validate_dates()
		self.validate_overlap()

	def validate_dates(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("End date can not be less than start date"))

	def validate_overlap(self):
		query = """
			select name
			from `tab{0}`
			where name != %(name)s
			and company = %(company)s and (start_date between %(start_date)s and %(end_date)s \
				or end_date between %(start_date)s and %(end_date)s \
				or (start_date < %(start_date)s and end_date > %(end_date)s))
			"""
		if not self.name:
			# hack! if name is null, it could cause problems with !=
			self.name = "New "+self.doctype

		overlap_doc = frappe.db.sql(query.format(self.doctype),{
				"start_date": self.start_date,
				"end_date": self.end_date,
				"name": self.name,
				"company": self.company
			}, as_dict = 1)

		if overlap_doc:
			msg = _("A {0} exists between {1} and {2} (").format(self.doctype,
				formatdate(self.start_date), formatdate(self.end_date)) \
				+ """ <b><a href="/app/Form/{0}/{1}">{1}</a></b>""".format(self.doctype, overlap_doc[0].name) \
				+ _(") for {0}").format(self.company)
			frappe.throw(msg)

def get_payroll_period_days(start_date, end_date, employee, company=None):
	if not company:
		company = frappe.db.get_value("Employee", employee, "company")
	payroll_period = frappe.db.sql("""
		select name, start_date, end_date
		from `tabPayroll Period`
		where
			company=%(company)s
			and %(start_date)s between start_date and end_date
			and %(end_date)s between start_date and end_date
	""", {
		'company': company,
		'start_date': start_date,
		'end_date': end_date
	})

	if len(payroll_period) > 0:
		actual_no_of_days = date_diff(getdate(payroll_period[0][2]), getdate(payroll_period[0][1])) + 1
		working_days = actual_no_of_days
		if not cint(frappe.db.get_value("Payroll Settings", None, "include_holidays_in_total_working_days")):
			holidays = get_holidays_for_employee(employee, getdate(payroll_period[0][1]), getdate(payroll_period[0][2]))
			working_days -= len(holidays)
		return payroll_period[0][0], working_days, actual_no_of_days
	return False, False, False

def get_payroll_period(from_date, to_date, company):
	payroll_period = frappe.db.sql("""
		select name, start_date, end_date
		from `tabPayroll Period`
		where start_date<=%s and end_date>= %s and company=%s
	""", (from_date, to_date, company), as_dict=1)

	return payroll_period[0] if payroll_period else None

def get_period_factor(employee, start_date, end_date, payroll_frequency, payroll_period, depends_on_payment_days=0):
	# TODO if both deduct checked update the factor to make tax consistent
	period_start, period_end = payroll_period.start_date, payroll_period.end_date
	joining_date, relieving_date = frappe.db.get_value("Employee", employee, ["date_of_joining", "relieving_date"])

	if getdate(joining_date) > getdate(period_start):
		period_start = joining_date
	if relieving_date and getdate(relieving_date) < getdate(period_end):
		period_end = relieving_date
		if month_diff(period_end, start_date) > 1:
			start_date = add_months(start_date, - (month_diff(period_end, start_date)+1))

	total_sub_periods, remaining_sub_periods = 0.0, 0.0

	if payroll_frequency ==  "Monthly" and not depends_on_payment_days:
		total_sub_periods = month_diff(payroll_period.end_date, payroll_period.start_date)
		remaining_sub_periods = month_diff(period_end, start_date)
	else:
		salary_days = date_diff(end_date, start_date) + 1

		days_in_payroll_period = date_diff(payroll_period.end_date, payroll_period.start_date) + 1
		total_sub_periods = flt(days_in_payroll_period) / flt(salary_days)

		remaining_days_in_payroll_period = date_diff(period_end, start_date) + 1
		remaining_sub_periods = flt(remaining_days_in_payroll_period) / flt(salary_days)

	return total_sub_periods, remaining_sub_periods
