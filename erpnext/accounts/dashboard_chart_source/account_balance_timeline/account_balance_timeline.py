# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import add_to_date, date_diff, getdate, nowdate, get_last_day, formatdate
from erpnext.accounts.report.general_ledger.general_ledger import execute
from frappe.core.page.dashboard.dashboard import cache_source, get_from_date_from_timespan
from frappe.desk.doctype.dashboard_chart.dashboard_chart import get_period_ending

from frappe.utils.nestedset import get_descendants_of

@frappe.whitelist()
@cache_source
def get(chart_name=None, from_date = None, to_date = None):
	chart = frappe.get_doc('Dashboard Chart', chart_name)
	timespan = chart.timespan
	timegrain = chart.time_interval
	filters = json.loads(chart.filters_json)

	account = filters.get("account")
	company = filters.get("company")

	if not to_date:
		to_date = nowdate()
	if not from_date:
		if timegrain in ('Monthly', 'Quarterly'):
			from_date = get_from_date_from_timespan(to_date, timespan)

	# fetch dates to plot
	dates = get_dates_from_timegrain(from_date, to_date, timegrain)

	# get all the entries for this account and its descendants
	gl_entries = get_gl_entries(account, get_period_ending(to_date, timegrain))

	# compile balance values
	result = build_result(account, dates, gl_entries)

	return {
		"labels": [formatdate(r[0].strftime('%Y-%m-%d')) for r in result],
		"datasets": [{
			"name": account,
			"values": [r[1] for r in result]
		}]
	}

def build_result(account, dates, gl_entries):
	result = [[getdate(date), 0.0] for date in dates]
	root_type = frappe.db.get_value('Account', account, 'root_type')

	# start with the first date
	date_index = 0

	# get balances in debit
	for entry in gl_entries:

		# entry date is after the current pointer, so move the pointer forward
		while getdate(entry.posting_date) > result[date_index][0]:
			date_index += 1

		result[date_index][1] += entry.debit - entry.credit

	# if account type is credit, switch balances
	if root_type not in ('Asset', 'Expense'):
		for r in result:
			r[1] = -1 * r[1]

	# for balance sheet accounts, the totals are cumulative
	if root_type in ('Asset', 'Liability', 'Equity'):
		for i, r in enumerate(result):
			if i > 0:
				r[1] = r[1] + result[i-1][1]

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

	dates = [get_period_ending(from_date, timegrain)]
	while getdate(dates[-1]) < getdate(to_date):
		date = get_period_ending(add_to_date(dates[-1], years=years, months=months, days=days), timegrain)
		dates.append(date)
	return dates
