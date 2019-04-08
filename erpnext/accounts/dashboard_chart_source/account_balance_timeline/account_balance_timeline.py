# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from itertools import groupby
from operator import itemgetter
import frappe
from frappe.core.page.dashboard.dashboard import cache_source
from frappe.utils import add_to_date, date_diff, getdate, nowdate
from erpnext.accounts.report.general_ledger.general_ledger import execute

from frappe.utils.nestedset import get_descendants_of

@frappe.whitelist()
@cache_source
def get(filters=None):
	timespan = filters.get("timespan")
	timegrain = filters.get("timegrain")
	account = filters.get("account")
	company = filters.get("company")

	from_date = get_from_date_from_timespan(timespan)
	to_date = nowdate()

	# fetch dates to plot
	dates = get_dates_from_timegrain(from_date, to_date, timegrain)

	# get all the entries for this account and its descendants
	gl_entries = get_gl_entries(account, to_date)

	# compile balance values
	result = build_result(account, dates, gl_entries)

	return {
		"labels": [r[0].strftime('%Y-%m-%d') for r in result],
		"datasets": [{
			"name": account,
			"values": [r[1] for r in result]
		}]
	}

def build_result(account, dates, gl_entries):
	result = [[getdate(date), 0.0] for date in dates]

	# start with the first date
	date_index = 0

	# get balances in debit
	for entry in gl_entries:

		# entry date is after the current pointer, so move the pointer forward
		while getdate(entry.posting_date) > result[date_index][0]:
			date_index += 1

		result[date_index][1] += entry.debit - entry.credit

	# if account type is credit, switch balances
	if frappe.db.get_value('Account', account, 'root_type') not in ('Asset', 'Expense'):
		for r in result:
			r[1] = -1 * r[1]

	return result

def get_gl_entries(account, to_date):
	child_accounts = get_descendants_of('Account', account, ignore_permissions=True)
	child_accounts.append(account)

	return frappe.db.get_all('GL Entry',
		fields = ['posting_date', 'debit', 'credit'],
		filters = [
			dict(posting_date = ('<', to_date)),
			dict(account = ('in', child_accounts))
		],
		order_by = 'posting_date asc')

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
