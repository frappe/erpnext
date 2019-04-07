# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from itertools import groupby
from operator import itemgetter
import frappe
from frappe.core.page.dashboard.dashboard import cache_source
from frappe.utils import add_to_date, date_diff, getdate, nowdate
from erpnext.accounts.report.general_ledger.general_ledger import execute

@frappe.whitelist()
@cache_source
def get(filters=None):
	timespan = filters.get("timespan")
	timegrain = filters.get("timegrain")
	account = filters.get("account")
	company = filters.get("company")

	from_date = get_from_date_from_timespan(timespan)
	to_date = nowdate()
	filters = frappe._dict({
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
		"account": account,
		"group_by": "Group by Voucher (Consolidated)"
	})
	report_results = execute(filters=filters)[1]

	interesting_fields = ["posting_date", "balance"]

	_results = []
	for row in report_results[1:-2]:
		_results.append([row[key] for key in interesting_fields])

	_results = add_opening_balance(from_date, _results, report_results[0])
	grouped_results = groupby(_results, key=itemgetter(0))
	results = [list(values)[-1] for key, values in grouped_results]
	results = add_missing_dates(results, from_date, to_date)
	results = granulate_results(results, from_date, to_date, timegrain)

	return {
		"labels": [result[0] for result in results],
		"datasets": [{
			"name": account,
			"values": [result[1] for result in results]
		}]
	}

def get_from_date_from_timespan(timespan):
	days = months = years = 0
	if "Last Week" == timespan:
		days = -7
	if "Last Month" == timespan:
		months = -1
	elif "Last Quarter" == timespan:
		months = -3
	elif "Last Year" == timespan:
		years = -1
	return add_to_date(None, years=years, months=months, days=days,
		as_string=True, as_datetime=True)


def add_opening_balance(from_date, _results, opening):
	if not _results or (_results[0][0] != getdate(from_date)):
		_results.insert(0, [from_date, opening.balance])
	return _results

def add_missing_dates(incomplete_results, from_date, to_date):
	day_count = date_diff(to_date, from_date)

	results_dict = dict(incomplete_results)
	last_balance = incomplete_results[0][1]
	results = []
	for date in (add_to_date(getdate(from_date), days=n) for n in range(day_count + 1)):
		if date in results_dict:
			last_balance = results_dict[date]
		results.append([date, last_balance])
	return results

def get_dates_from_timegrain(from_date, to_date, timegrain):
	days = months = years = 0
	if "Daily" == timegrain:
		days = 1
	elif "Weekly" == timegrain:
		days = 7
	elif "Monthly" == timegrain:
		months = 1
	elif "Quarterly" == timegrain:
		months = 3

	dates = [from_date]
	while dates[-1] <= to_date:
		dates.append(add_to_date(dates[-1], years=years, months=months, days=days))
	return dates

def granulate_results(incomplete_results, from_date, to_date, timegrain):
	dates = set(get_dates_from_timegrain(getdate(from_date), getdate(to_date), timegrain))
	return list(filter(lambda x: x[0] in dates,incomplete_results))
