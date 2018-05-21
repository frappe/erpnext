# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import date_diff, getdate
from frappe.model.document import Document

class PayrollPeriod(Document):
	pass

def get_payroll_period_days(start_date, end_date, company):
	payroll_period_dates = frappe.db.sql("""
	select ppd.start_date, ppd.end_date from `tabPayroll Period Date` ppd, `tabPayroll Period` pp
	where pp.company=%(company)s
	and ppd.parent = pp.name
	and (
		(%(start_date)s between ppd.start_date and ppd.end_date)
		or (%(end_date)s between ppd.start_date and ppd.end_date)
		or (ppd.start_date between %(start_date)s and %(end_date)s)
	)""", {
		'company': company,
		'start_date': start_date,
		'end_date': end_date
	})

	if len(payroll_period_dates) > 0:
		return date_diff(getdate(payroll_period_dates[0][1]), getdate(payroll_period_dates[0][0])) + 1
