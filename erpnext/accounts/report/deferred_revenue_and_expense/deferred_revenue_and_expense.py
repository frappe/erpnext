# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _, qb
from frappe.query_builder import Column, functions
from frappe.utils import add_days, date_diff, flt, get_first_day, get_last_day, getdate, rounded

from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.utils import get_fiscal_year


class Deferred_Item:
	"""
	Helper class for processing items with deferred revenue/expense
	"""

	def __init__(self, item, inv, gle_entries):
		self.name = item
		self.parent = inv.name
		self.item_name = gle_entries[0].item_name
		self.service_start_date = gle_entries[0].service_start_date
		self.service_end_date = gle_entries[0].service_end_date
		self.base_net_amount = gle_entries[0].base_net_amount
		self.filters = inv.filters
		self.period_list = inv.period_list

		if gle_entries[0].deferred_revenue_account:
			self.type = "Deferred Sale Item"
			self.deferred_account = gle_entries[0].deferred_revenue_account
		elif gle_entries[0].deferred_expense_account:
			self.type = "Deferred Purchase Item"
			self.deferred_account = gle_entries[0].deferred_expense_account

		self.gle_entries = []
		# holds period wise total for item
		self.period_total = []
		self.last_entry_date = self.service_start_date

		if gle_entries:
			self.gle_entries = gle_entries
			for x in self.gle_entries:
				if self.get_amount(x):
					self.last_entry_date = x.gle_posting_date

	def report_data(self):
		"""
		Generate report data for output
		"""
		ret_data = frappe._dict({"name": self.item_name})
		for period in self.period_total:
			ret_data[period.key] = period.total
			ret_data.indent = 1
		return ret_data

	def get_amount(self, entry):
		"""
		For a given GL/Journal posting, get balance based on item type
		"""
		if self.type == "Deferred Sale Item":
			return flt(entry.debit) - flt(entry.credit)
		elif self.type == "Deferred Purchase Item":
			return -(flt(entry.credit) - flt(entry.debit))
		return 0

	def get_item_total(self):
		"""
		Helper method - calculate booked amount. Includes simulated postings as well
		"""
		total = 0
		for gle_posting in self.gle_entries:
			total += self.get_amount(gle_posting)

		return total

	def calculate_amount(self, start_date, end_date):
		"""
		start_date, end_date - datetime.datetime.date
		return - estimated amount to post for given period
		Calculated based on already booked amount and item service period
		"""
		total_months = (
			(self.service_end_date.year - self.service_start_date.year) * 12
			+ (self.service_end_date.month - self.service_start_date.month)
			+ 1
		)

		prorate = date_diff(self.service_end_date, self.service_start_date) / date_diff(
			get_last_day(self.service_end_date), get_first_day(self.service_start_date)
		)

		actual_months = rounded(total_months * prorate, 1)

		already_booked_amount = self.get_item_total()
		base_amount = self.base_net_amount / actual_months

		if base_amount + already_booked_amount > self.base_net_amount:
			base_amount = self.base_net_amount - already_booked_amount

		if not (get_first_day(start_date) == start_date and get_last_day(end_date) == end_date):
			partial_month = flt(date_diff(end_date, start_date)) / flt(
				date_diff(get_last_day(end_date), get_first_day(start_date))
			)
			base_amount *= rounded(partial_month, 1)

		return base_amount

	def make_dummy_gle(self, name, date, amount):
		"""
		return - frappe._dict() of a dummy gle entry
		"""
		entry = frappe._dict(
			{"name": name, "gle_posting_date": date, "debit": 0, "credit": 0, "posted": "not"}
		)
		if self.type == "Deferred Sale Item":
			entry.debit = amount
		elif self.type == "Deferred Purchase Item":
			entry.credit = amount
		return entry

	def simulate_future_posting(self):
		"""
		simulate future posting by creating dummy gl entries. starts from the last posting date.
		"""
		if (
			self.service_start_date != self.service_end_date
			and add_days(self.last_entry_date, 1) < self.service_end_date
		):
			self.estimate_for_period_list = get_period_list(
				self.filters.from_fiscal_year,
				self.filters.to_fiscal_year,
				add_days(self.last_entry_date, 1),
				self.service_end_date,
				"Date Range",
				"Monthly",
				company=self.filters.company,
			)

			for period in self.estimate_for_period_list:
				amount = self.calculate_amount(period.from_date, period.to_date)
				gle = self.make_dummy_gle(period.key, period.to_date, amount)
				self.gle_entries.append(gle)

	def calculate_item_revenue_expense_for_period(self):
		"""
		calculate item postings for each period and update period_total list
		"""
		for period in self.period_list:
			period_sum = 0
			actual = 0
			for posting in self.gle_entries:
				# if period.from_date <= posting.posting_date <= period.to_date:
				if period.from_date <= getdate(posting.gle_posting_date) <= period.to_date:
					period_sum += self.get_amount(posting)
					if posting.posted == "posted":
						actual += self.get_amount(posting)

			self.period_total.append(frappe._dict({"key": period.key, "total": period_sum, "actual": actual}))
		return self.period_total


class Deferred_Invoice:
	def __init__(self, invoice, items, filters, period_list):
		"""
		Helper class for processing invoices with deferred revenue/expense items
		invoice - string : invoice name
		items - list : frappe._dict() with item details. Refer Deferred_Item for required fields
		"""
		self.name = invoice
		self.posting_date = items[0].posting_date
		self.filters = filters
		self.period_list = period_list
		# holds period wise total for invoice
		self.period_total = []

		if items[0].deferred_revenue_account:
			self.type = "Sales"
		elif items[0].deferred_expense_account:
			self.type = "Purchase"

		self.items = []
		# for each uniq items
		self.uniq_items = set([x.item for x in items])
		for item in self.uniq_items:
			self.items.append(Deferred_Item(item, self, [x for x in items if x.item == item]))

	def calculate_invoice_revenue_expense_for_period(self):
		"""
		calculate deferred revenue/expense for all items in invoice
		"""
		# initialize period_total list for invoice
		for period in self.period_list:
			self.period_total.append(frappe._dict({"key": period.key, "total": 0, "actual": 0}))

		for item in self.items:
			item_total = item.calculate_item_revenue_expense_for_period()
			# update invoice total
			for idx in range(len(self.period_list)):
				self.period_total[idx].total += item_total[idx].total
				self.period_total[idx].actual += item_total[idx].actual
		return self.period_total

	def estimate_future(self):
		"""
		create dummy GL entries for upcoming months for all items in invoice
		"""
		[item.simulate_future_posting() for item in self.items]

	def report_data(self):
		"""
		generate report data for invoice, includes invoice total
		"""
		ret_data = []
		inv_total = frappe._dict({"name": self.name})
		for x in self.period_total:
			inv_total[x.key] = x.total
			inv_total.indent = 0
		ret_data.append(inv_total)
		list(map(lambda item: ret_data.append(item.report_data()), self.items))
		return ret_data


class Deferred_Revenue_and_Expense_Report:
	def __init__(self, filters=None):
		"""
		Initialize deferred revenue/expense report with user provided filters or system defaults, if none is provided
		"""

		# If no filters are provided, get user defaults
		if not filters:
			fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date=getdate()))
			self.filters = frappe._dict(
				{
					"company": frappe.defaults.get_user_default("Company"),
					"filter_based_on": "Fiscal Year",
					"period_start_date": fiscal_year.year_start_date,
					"period_end_date": fiscal_year.year_end_date,
					"from_fiscal_year": fiscal_year.year,
					"to_fiscal_year": fiscal_year.year,
					"periodicity": "Monthly",
					"type": "Revenue",
					"with_upcoming_postings": True,
				}
			)
		else:
			self.filters = frappe._dict(filters)

		self.period_list = None
		self.deferred_invoices = []
		# holds period wise total for report
		self.period_total = []

	def get_period_list(self):
		"""
		Figure out selected period based on filters
		"""
		self.period_list = get_period_list(
			self.filters.from_fiscal_year,
			self.filters.to_fiscal_year,
			self.filters.period_start_date,
			self.filters.period_end_date,
			self.filters.filter_based_on,
			self.filters.periodicity,
			company=self.filters.company,
		)

	def get_invoices(self):
		"""
		Get all sales and purchase invoices which has deferred revenue/expense items
		"""
		gle = qb.DocType("GL Entry")
		# column doesn't have an alias option
		posted = Column("posted")

		if self.filters.type == "Revenue":
			inv = qb.DocType("Sales Invoice")
			inv_item = qb.DocType("Sales Invoice Item")
			deferred_flag_field = inv_item["enable_deferred_revenue"]
			deferred_account_field = inv_item["deferred_revenue_account"]

		elif self.filters.type == "Expense":
			inv = qb.DocType("Purchase Invoice")
			inv_item = qb.DocType("Purchase Invoice Item")
			deferred_flag_field = inv_item["enable_deferred_expense"]
			deferred_account_field = inv_item["deferred_expense_account"]

		query = (
			qb.from_(inv_item)
			.join(inv)
			.on(inv.name == inv_item.parent)
			.left_join(gle)
			.on((inv_item.name == gle.voucher_detail_no) & (deferred_account_field == gle.account))
			.select(
				inv.name.as_("doc"),
				inv.posting_date,
				inv_item.name.as_("item"),
				inv_item.item_name,
				inv_item.service_start_date,
				inv_item.service_end_date,
				inv_item.base_net_amount,
				deferred_account_field,
				gle.posting_date.as_("gle_posting_date"),
				functions.Sum(gle.debit).as_("debit"),
				functions.Sum(gle.credit).as_("credit"),
				posted,
			)
			.where(
				(inv.docstatus == 1)
				& (deferred_flag_field == 1)
				& (
					(
						(self.period_list[0].from_date >= inv_item.service_start_date)
						& (inv_item.service_end_date >= self.period_list[0].from_date)
					)
					| (
						(inv_item.service_start_date >= self.period_list[0].from_date)
						& (inv_item.service_start_date <= self.period_list[-1].to_date)
					)
				)
			)
			.groupby(inv.name, inv_item.name, gle.posting_date)
			.orderby(gle.posting_date)
		)
		self.invoices = query.run(as_dict=True)

		uniq_invoice = set([x.doc for x in self.invoices])
		for inv in uniq_invoice:
			self.deferred_invoices.append(
				Deferred_Invoice(
					inv, [x for x in self.invoices if x.doc == inv], self.filters, self.period_list
				)
			)

	def estimate_future(self):
		"""
		For all Invoices estimate upcoming postings
		"""
		for x in self.deferred_invoices:
			x.estimate_future()

	def calculate_revenue_and_expense(self):
		"""
		calculate the deferred revenue/expense for all invoices
		"""
		# initialize period_total list for report
		for period in self.period_list:
			self.period_total.append(frappe._dict({"key": period.key, "total": 0, "actual": 0}))

		for inv in self.deferred_invoices:
			inv_total = inv.calculate_invoice_revenue_expense_for_period()
			# calculate total for whole report
			for idx in range(len(self.period_list)):
				self.period_total[idx].total += inv_total[idx].total
				self.period_total[idx].actual += inv_total[idx].actual

	def get_columns(self):
		columns = []
		columns.append({"label": _("Name"), "fieldname": "name", "fieldtype": "Data", "read_only": 1})
		for period in self.period_list:
			columns.append(
				{
					"label": _(period.label),
					"fieldname": period.key,
					"fieldtype": "Currency",
					"read_only": 1,
				}
			)
		return columns

	def generate_report_data(self):
		"""
		Generate report data for all invoices. Adds total rows for revenue and expense
		"""
		ret = []

		for inv in self.deferred_invoices:
			ret += inv.report_data()

		# empty row for padding
		ret += [{}]

		# add total row
		if self.filters.type == "Revenue":
			total_row = frappe._dict({"name": "Total Deferred Income"})
		elif self.filters.type == "Expense":
			total_row = frappe._dict({"name": "Total Deferred Expense"})

		for idx, period in enumerate(self.period_list, 0):
			total_row[period.key] = self.period_total[idx].total
		ret.append(total_row)

		return ret

	def prepare_chart(self):
		chart = {
			"data": {
				"labels": [period.label for period in self.period_list],
				"datasets": [
					{
						"name": _("Actual Posting"),
						"chartType": "bar",
						"values": [x.actual for x in self.period_total],
					}
				],
			},
			"type": "axis-mixed",
			"height": 500,
			"axisOptions": {"xAxisMode": "Tick", "xIsSeries": True},
			"barOptions": {"stacked": False, "spaceRatio": 0.5},
		}

		if self.filters.with_upcoming_postings:
			chart["data"]["datasets"].append(
				{"name": _("Expected"), "chartType": "line", "values": [x.total for x in self.period_total]}
			)

		return chart

	def run(self, *args, **kwargs):
		"""
		Run report and generate data
		"""
		self.deferred_invoices.clear()
		self.get_period_list()
		self.get_invoices()

		if self.filters.with_upcoming_postings:
			self.estimate_future()
		self.calculate_revenue_and_expense()


def execute(filters=None):
	report = Deferred_Revenue_and_Expense_Report(filters=filters)
	report.run()

	columns = report.get_columns()
	data = report.generate_report_data()
	message = []
	chart = report.prepare_chart()

	return columns, data, message, chart
