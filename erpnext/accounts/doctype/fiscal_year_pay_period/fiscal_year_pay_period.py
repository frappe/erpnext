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

	# `frequency_key` contains the maximum number of iterations for each key in the dict
	loop_keys = get_frequency_loop_values()
	frequency_kwarg = get_frequency_kwargs()

	for _ in range(loop_keys.get(payroll_frequency)):
		end = add_to_date(start, **frequency_kwarg.get(payroll_frequency))
		dates.append(
			{
				'start_date': start.strftime(DATE_FORMAT),
				'end_date': add_to_date(end, days=-1).strftime(DATE_FORMAT),
			}
		)

		if end > getdate(payroll_end):
			break
		else:
			start = end

	return dates


def get_frequency_kwargs():
	return {
		'bimonthly': {'years': 0, 'months': 2, 'days': 0},
		'monthly': {'years': 0, 'months': 1, 'days': 0},
		'fortnightly': {'years': 0, 'months': 0, 'days': 14},
		'weekly': {'years': 0, 'months': 0, 'days': 7},
		'daily': {'years': 0, 'months': 0, 'days': 1}
	}


def get_frequency_loop_values():
	return {
		'monthly': 12, 'bimonthly': 6,
		'fortnightly': 27, 'weekly': 52,
		'daily': 366
	}
