# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import add_to_date, formatdate, get_link_to_form, getdate, nowdate, cint
from frappe.utils.dashboard import cache_source
from frappe.utils.dateutils import get_from_date_from_timespan, get_period_ending
from frappe.utils.nestedset import get_descendants_of
from erpnext import get_company_currency, get_default_currency


class AccountBalanceTimeline(object):
	def __init__(self, chart_name, chart, from_date, to_date, filters=None, timespan=None, time_interval=None):
		if chart_name:
			self.chart = frappe.get_doc("Dashboard Chart", chart_name)
		else:
			self.chart = frappe._dict(frappe.parse_json(chart))

		self.chart_name = self.chart.name or self.chart.chart_name or chart_name

		self.filters = frappe.parse_json(filters) or frappe.parse_json(self.chart.filters_json) or frappe._dict()
		
		self.timespan = timespan or self.chart.timespan
		self.timegrain = time_interval or self.chart.time_interval

		self.from_date = from_date
		self.to_date = to_date

	def run(self):
		self.validate_filters()

		self.accounts = self.get_accounts()
		self.dates = get_dates_from_timegrain(self.from_date, self.to_date, self.timegrain)
		self.gl_entries = self.get_gl_entries()
		self.get_currency()

		# compile balance values
		labels = [formatdate(date) for date in self.dates]
		datasets = self.build_result()

		return {
			"labels": labels,
			"datasets": datasets,
			"fieldtype": "Currency",
			"options": self.currency,
		}

	def validate_filters(self):
		self.filters.accumulated_values = cint(self.filters.accumulated_values)

		if self.filters.account and not frappe.db.exists("Account", self.filters.account):
			frappe.throw(
				_("Account {0} does not exists in the dashboard chart {1}").format(
					self.filters.account, get_link_to_form("Dashboard Chart", self.chart_name)
				)
			)

		if self.timespan == "Select Date Range":
			self.from_date = self.from_date or self.chart.from_date
			self.to_date = self.to_date or self.chart.to_date

		if not self.to_date:
			self.to_date = nowdate()
		if not self.from_date:
			self.from_date = get_from_date_from_timespan(self.to_date, self.timespan)

	def get_accounts(self):
		accounts_filters = {}
		if self.filters.company:
			accounts_filters["company"] = self.filters.company
		if self.filters.account_type:
			accounts_filters["account_type"] = self.filters.account_type
		if self.filters.root_type:
			accounts_filters["root_type"] = ("in", self.filters.root_type)

		accounts = []
		if self.filters.account:
			accounts.append(self.filters.account)

		if not accounts and accounts_filters:
			accounts = frappe.get_all("Account", filters=accounts_filters, pluck='name')

		for account in accounts[:]:
			child_accounts = get_descendants_of("Account", account, ignore_permissions=True)
			for child_account in child_accounts:
				if child_account not in accounts:
					accounts.append(child_accounts)

		if not accounts:
			frappe.throw(
				_("Account is not set for Dashboard Chart {0}").format(
					get_link_to_form("Dashboard Chart", self.chart_name)
				)
			)

		return accounts

	def get_gl_entries(self):
		from_date = self.dates[0]
		to_date = self.dates[-1]

		conditions = []
		conditions.append("account in %(accounts)s")
		conditions.append("voucher_type != 'Period Closing Voucher'")
		conditions.append("posting_date <= %(to_date)s")

		if not self.filters.accumulated_values:
			conditions.append("posting_date >= %(from_date)s")

		filter_values = {
			"accounts": self.accounts,
			"from_date": from_date,
			"to_date": to_date,
		}

		conditions = " and ".join(conditions)

		gl_entries = frappe.db.sql(f"""
			select gle.posting_date, gle.account, gle.debit, gle.credit, a.root_type
			from `tabGL Entry` gle
			inner join `tabAccount` a on gle.account = a.name
			where {conditions}
			order by posting_date
		""", filter_values, as_dict=1)

		return gl_entries

	def build_result(self):
		datasets = []

		if self.filters.group_by == "Account":
			gle_map = {}
			for gle in self.gl_entries:
				gle_map.setdefault(gle.account, []).append(gle)

			for account, filtered_gles in gle_map.items():
				if filtered_gles:
					dataset = self.build_dataset(filtered_gles, dataset_name=account)
					# dataset["chartType"] = "bar"
					datasets.append(dataset)
		elif self.filters.group_by == "Root Type":
			gle_map = {}
			for gle in self.gl_entries:
				gle_map.setdefault(gle.root_type, []).append(gle)

			for root_type, filtered_gles in gle_map.items():
				if filtered_gles:
					dataset = self.build_dataset(filtered_gles, dataset_name=root_type, root_type=root_type)
					# dataset["chartType"] = "bar"
					datasets.append(dataset)

		# datasets = sorted(datasets, key=lambda d: d['values'][-1], reverse=True)

		total_dataset = self.build_dataset(self.gl_entries, dataset_name=self.get_dataset_name())
		# if self.filters.group_by:
		# 	total_dataset["chartType"] = "line"

		datasets.append(total_dataset)

		return datasets

	def build_dataset(self, gl_entries, dataset_name, root_type=None):
		dataset = {
			"name": dataset_name,
			"values": [{"date": getdate(date), "total": 0.0} for date in self.dates]
		}

		# start with the first date
		date_index = 0

		# get balances in debit
		for entry in gl_entries:

			# entry date is after the current pointer, so move the pointer forward
			while getdate(entry.posting_date) > dataset["values"][date_index]["date"]:
				date_index += 1

			dataset["values"][date_index]["total"] += entry.debit - entry.credit

		# if account type is credit, switch balances
		root_type = root_type or frappe.db.get_value("Account", self.accounts[0], "root_type")
		if root_type not in ("Asset", "Expense"):
			for r in dataset["values"]:
				r["total"] = -1 * r["total"]

		# for balance sheet accounts, the totals are cumulative
		if self.filters.accumulated_values:
			for i, r in enumerate(dataset["values"]):
				if i > 0:
					r["total"] += dataset["values"][i - 1]["total"]

		dataset["values"] = [d["total"] for d in dataset["values"]]

		return dataset

	def get_dataset_name(self):
		if self.filters.account:
			self.dataset_name = self.filters.account
		elif self.filters.account_type:
			self.dataset_name = _("{0} Accounts Balance".format(self.filters.account_type))
		elif self.filters.root_type and len(self.filters.root_type) == 1:
			self.dataset_name = _("{0} Accounts Balance".format(self.filters.root_type))
		else:
			self.dataset_name = self.chart_name or _("Account Balance Timeline")

	def get_currency(self):
		if self.filters.company:
			self.currency = get_company_currency(self.filters.company)
		elif self.filters.account:
			account_company = frappe.db.get_value("Account", self.filters.account, "company")
			self.currency = get_company_currency(account_company)
		elif self.accounts:
			account = self.accounts[0]
			account_company = frappe.db.get_value("Account", account, "company")
			self.currency = get_company_currency(account_company)
		else:
			self.currency = get_default_currency()


def get_dates_from_timegrain(from_date, to_date, timegrain):
	days = months = years = 0
	if timegrain == "Daily":
		days = 1
	elif timegrain == "Weekly":
		days = 7
	elif timegrain == "Monthly":
		months = 1
	elif timegrain == "Quarterly":
		months = 3

	dates = [get_period_ending(from_date, timegrain)]
	while getdate(dates[-1]) < getdate(to_date):
		date = get_period_ending(
			add_to_date(dates[-1], years=years, months=months, days=days), timegrain
		)
		dates.append(date)

	return dates


@frappe.whitelist()
@cache_source
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	return AccountBalanceTimeline(chart_name, chart, from_date, to_date, filters, timespan, time_interval).run()