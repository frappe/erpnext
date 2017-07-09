# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, DATE_FORMAT, add_months, add_to_date
from six.moves import range


class FiscalYearPayPeriod(Document):
	pass


@frappe.whitelist()
def get_pay_period_dates(payroll_start, payroll_end, payroll_frequency):
	dates = []
	payroll_frequency = payroll_frequency.lower()
	start = getdate(payroll_start)

	key = {'monthly': 12, 'bimonthly': 6, 'fortnightly': 27, 'weekly': 52, 'daily': 366}
	for _ in range(key.get(payroll_frequency)):
		end = getdate(add_months(start, 1))
		dates.append(
			{
				'start_date': start.strftime(DATE_FORMAT),
				'end_date': add_to_date(end, days=-1).strftime(DATE_FORMAT),
			}
		)

		if end >= getdate(payroll_end):
			break
		else:
			start = end

	return dates
