# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import datetime

import frappe
from frappe import qb

<<<<<<< HEAD
<<<<<<< HEAD
from frappe.query_builder import functions
<<<<<<< HEAD
from frappe.utils import add_days, date_diff, flt, get_first_day, get_last_day, rounded

from erpnext.accounts.report.financial_statements import get_period_list


class Deferred_Item(object):
	"""
	Helper class for processing items with deferred revenue/expense
	"""

=======
from frappe.query_builder import functions, queries
from frappe.utils import *

from erpnext.accounts.report.financial_statements import (
	15442b8,
	=======,
	>>>>>>>,
	add_days,
	added,
	comments,
	date_diff,
	flt,
	frappe.query_builder,
	frappe.utils,
	from,
	functions,
	get_first_day,
	get_last_day,
	get_period_list,
	import,
	rounded,
)

)
=======
from frappe.utils import date_diff, get_last_day, get_first_day, rounded, flt, add_days
>>>>>>> 217fe49 (fixed formatting issues)
from erpnext.accounts.report.financial_statements import get_period_list


class Deferred_Item(object):
<<<<<<< HEAD
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
	"""
	Helper class for processing items with deferred revenue/expense
	"""
<<<<<<< HEAD
>>>>>>> 15442b8 (added comments)
=======

>>>>>>> 217fe49 (fixed formatting issues)
	def __init__(self, item, inv):
		self.name = item.item
		self.parent = inv.name
		self.item_code = item.item_code
		self.item_name = item.item_name
		self.service_start_date = item.service_start_date
		self.service_end_date = item.service_end_date
		self.base_net_amount = item.base_net_amount
		self.filters = inv.filters
		self.period_list = inv.period_list

		if item.deferred_revenue_account:
<<<<<<< HEAD
<<<<<<< HEAD
			self.type = "Deferred Sale Item"
			self.deferred_account = item.deferred_revenue_account
		elif item.deferred_expense_account:
			self.type = "Deferred Purchase Item"
=======
			self.type = 'Deferred Sale Item'
			self.deferred_account = item.deferred_revenue_account
		elif item.deferred_expense_account:
			self.type = 'Deferred Purchase Item'
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			self.type = "Deferred Sale Item"
			self.deferred_account = item.deferred_revenue_account
		elif item.deferred_expense_account:
			self.type = "Deferred Purchase Item"
>>>>>>> 217fe49 (fixed formatting issues)
			self.deferred_account = item.deferred_expense_account

		self.gle_entries = []
		self.jre_entries = []
		self.period_total = []
		self.last_entry_date = None

	def report_data(self):
<<<<<<< HEAD
<<<<<<< HEAD
		"""
		Generate report data for output
		"""
		ret_data = frappe._dict({"name": self.item_name})
		for period in self.period_total:
=======
=======
		"""
		Generate report data for output
		"""
<<<<<<< HEAD
>>>>>>> 15442b8 (added comments)
		ret_data = frappe._dict({'name':self.item_name})
=======
		ret_data = frappe._dict({"name": self.item_name})
>>>>>>> 217fe49 (fixed formatting issues)
		for period in self.period_total:
<<<<<<< HEAD
			# ret_data[period.key] = frappe._dict({'total': period.total, 'actual': period.actual})
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
>>>>>>> 6a414f2 (bug fix - cancelled postings will not considered)
			ret_data[period.key] = period.total
			ret_data.indent = 1
		return ret_data

	def get_gl_and_journal_postings(self):
<<<<<<< HEAD
<<<<<<< HEAD
		"""
		Fetch posted entries
		"""
		# General Ledger postings
		gle = qb.DocType("GL Entry")
		query = (
			qb.from_(gle)
			.select(
				gle.name,
				gle.posting_date,
				gle.company,
				functions.Sum(gle.debit),
				functions.Sum(gle.credit),
				gle.account,
				gle.voucher_no,
				gle.voucher_detail_no,
			)
			.where(
				(gle.voucher_no == self.parent)
				& (gle.voucher_detail_no == self.name)
				& (gle.company == self.filters.company)
				& (gle.account == self.deferred_account)
			)
			.groupby(gle.posting_date)
			.orderby(gle.posting_date)
		)
		for (
			name,
			posting_date,
			company,
			debit,
			credit,
			account,
			voucher_no,
			voucher_detail_no,
		) in query.run():
			self.gle_entries.append(
				frappe._dict(
					{
						"name": name,
						"posting_date": posting_date,
						"company": company,
						"debit": debit,
						"credit": credit,
						"account": account,
						"voucher_no": voucher_no,
						"voucher_detail_no": voucher_detail_no,
						"posted": True,
					}
				)
			)

		# Journal Entry postings
		jre = qb.DocType("Journal Entry")
		jre_acc = qb.DocType("Journal Entry Account")
		query = (
			qb.from_(jre)
			.join(jre_acc)
			.on(jre.name == jre_acc.parent)
			.select(
				jre.name.as_("journal"),
				jre.posting_date,
				functions.Sum(jre_acc.debit),
				functions.Sum(jre_acc.credit),
			)
			.where(
				(jre_acc.reference_name == self.parent)
				& (jre_acc.reference_detail_no == self.name)
				& (jre_acc.account == self.deferred_account)
				& (jre.docstatus == 1)
			)
			.groupby(jre.posting_date)
			.orderby(jre.posting_date)
		)
		for name, posting_date, debit, credit in query.run():
			self.jre_entries.append(
				frappe._dict(
					{
						"name": name,
						"posting_date": posting_date,
						"debit": debit,
						"credit": credit,
						"posted": True,
					}
				)
			)

		# calculate last GL or journal posting for item
		if self.gle_entries == [] and self.jre_entries == []:
			self.last_entry_date = self.service_start_date
		elif self.calculate_item_total() == 0:
			self.last_entry_date = self.service_start_date
		else:
			self.last_entry_date = sorted(
				(self.gle_entries + self.jre_entries), key=lambda x: x.posting_date, reverse=True
			)[0].posting_date
=======
=======
		"""
		Fetch posted entries
		"""
>>>>>>> 15442b8 (added comments)
		# General Ledger postings
		gle = qb.DocType("GL Entry")
		query = (
			qb.from_(gle)
			.select(
				gle.name,
				gle.posting_date,
				gle.company,
				functions.Sum(gle.debit),
				functions.Sum(gle.credit),
				gle.account,
				gle.voucher_no,
				gle.voucher_detail_no,
			)
			.where(
				(gle.voucher_no == self.parent)
				& (gle.voucher_detail_no == self.name)
				& (gle.company == self.filters.company)
				& (gle.account == self.deferred_account)
			)
			.groupby(gle.posting_date)
			.orderby(gle.posting_date)
		)
		for (
			name,
			posting_date,
			company,
			debit,
			credit,
			account,
			voucher_no,
			voucher_detail_no,
		) in query.run():
			self.gle_entries.append(
				frappe._dict(
					{
						"name": name,
						"posting_date": posting_date,
						"company": company,
						"debit": debit,
						"credit": credit,
						"account": account,
						"voucher_no": voucher_no,
						"voucher_detail_no": voucher_detail_no,
						"posted": True,
					}
				)
			)

		# Journal Entry postings
		jre = qb.DocType("Journal Entry")
		jre_acc = qb.DocType("Journal Entry Account")
		query = (
			qb.from_(jre)
			.join(jre_acc)
			.on(jre.name == jre_acc.parent)
			.select(
				jre.name.as_("journal"),
				jre.posting_date,
				functions.Sum(jre_acc.debit),
				functions.Sum(jre_acc.credit),
			)
			.where(
				(jre_acc.reference_name == self.parent)
				& (jre_acc.reference_detail_no == self.name)
				& (jre_acc.account == self.deferred_account)
				& (jre.docstatus == 1)
			)
			.groupby(jre.posting_date)
			.orderby(jre.posting_date)
		)
		for name, posting_date, debit, credit in query.run():
			self.jre_entries.append(
				frappe._dict(
					{
						"name": name,
						"posting_date": posting_date,
						"debit": debit,
						"credit": credit,
						"posted": True,
					}
				)
			)

		# calculate last GL or journal posting for item
		if self.gle_entries == [] and self.jre_entries == []:
			self.last_entry_date = self.service_start_date
		elif self.calculate_item_total() == 0:
			self.last_entry_date = self.service_start_date
		else:
<<<<<<< HEAD
			self.last_entry_date = sorted((self.gle_entries + self.jre_entries), key=lambda x: x.posting_date, reverse=True)[0].posting_date
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			self.last_entry_date = sorted(
				(self.gle_entries + self.jre_entries), key=lambda x: x.posting_date, reverse=True
			)[0].posting_date
>>>>>>> 217fe49 (fixed formatting issues)
			if type(self.last_entry_date) == str:
				self.last_entry_date = datetime.datetime.strptime(self.last_entry_date, "%Y-%m-%d")

	def get_amount(self, entry):
		"""
<<<<<<< HEAD
<<<<<<< HEAD
		For a given GL/Journal posting, get balace based on item type
		"""
		if self.type == "Deferred Sale Item":
<<<<<<< HEAD
			return entry.debit - entry.credit
		elif self.type == "Deferred Purchase Item":
			return -(entry.credit - entry.debit)
=======
		get debit/credit based on type
		entry - should be a gl entry or journal posting
=======
		For a given GL/Journal posting, get balace based on item type
>>>>>>> 15442b8 (added comments)
		"""
		if self.type == 'Deferred Sale Item':
			return entry.debit - entry.credit
		elif self.type == 'Deferred Purchase Item':
<<<<<<< HEAD
			return -entry.credit
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
=======
			return entry.debit - entry.credit
		elif self.type == "Deferred Purchase Item":
>>>>>>> 217fe49 (fixed formatting issues)
			return -(entry.credit - entry.debit)
>>>>>>> 6a414f2 (bug fix - cancelled postings will not considered)
		return 0

	def calculate_item_total(self):
		"""
<<<<<<< HEAD
<<<<<<< HEAD
		Helper method - calculate booked amount. Included simulated postings as well
=======
		includes future postings as well
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
		Helper method - calculate booked amount. Included simulated postings as well
>>>>>>> 15442b8 (added comments)
		"""
		total = 0
		for gle_posting in self.gle_entries:
			total += self.get_amount(gle_posting)
		for jre_posting in self.jre_entries:
			total += self.get_amount(jre_posting)
<<<<<<< HEAD
<<<<<<< HEAD

		return total

	def calculate_amount(self, start_date, end_date):
		"""
		start_date, end_date - datetime.datetime.date
		return - estimated amount to post for given period
		Calculated based on already booked amount and item service period
		"""
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 217fe49 (fixed formatting issues)
		total_months = (
			(self.service_end_date.year - self.service_start_date.year) * 12
			+ (self.service_end_date.month - self.service_start_date.month)
			+ 1
		)
<<<<<<< HEAD

		prorate = date_diff(self.service_end_date, self.service_start_date) / date_diff(
			get_last_day(self.service_end_date), get_first_day(self.service_start_date)
		)
=======
=======

>>>>>>> 6a414f2 (bug fix - cancelled postings will not considered)
		return total

	def calculate_amount(self, start_date, end_date):
=======
>>>>>>> 15442b8 (added comments)
		total_months = (self.service_end_date.year - self.service_start_date.year) * 12 + (self.service_end_date.month - self.service_start_date.month) + 1

		prorate = date_diff(self.service_end_date, self.service_start_date) / date_diff(get_last_day(self.service_end_date),get_first_day(self.service_start_date))
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======

		prorate = date_diff(self.service_end_date, self.service_start_date) / date_diff(
			get_last_day(self.service_end_date), get_first_day(self.service_start_date)
		)
>>>>>>> 217fe49 (fixed formatting issues)

		actual_months = rounded(total_months * prorate, 1)

		already_booked_amount = self.calculate_item_total()
		base_amount = self.base_net_amount / actual_months

		if base_amount + already_booked_amount > self.base_net_amount:
			base_amount = self.base_net_amount - already_booked_amount

		if not (get_first_day(start_date) == start_date and get_last_day(end_date) == end_date):
<<<<<<< HEAD
<<<<<<< HEAD
			partial_month = flt(date_diff(end_date, start_date)) / flt(
				date_diff(get_last_day(end_date), get_first_day(start_date))
			)
=======
			partial_month = flt(date_diff(end_date, start_date)) / flt(date_diff(get_last_day(end_date), get_first_day(start_date)))
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			partial_month = flt(date_diff(end_date, start_date)) / flt(
				date_diff(get_last_day(end_date), get_first_day(start_date))
			)
>>>>>>> 217fe49 (fixed formatting issues)
			base_amount *= rounded(partial_month, 1)

		return base_amount

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 15442b8 (added comments)
	def make_dummy_gle(self, name, date, amount):
		"""
		return - frappe._dict()
		"""
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 217fe49 (fixed formatting issues)
		entry = frappe._dict(
			{"name": name, "posting_date": date, "debit": 0, "credit": 0, "posted": False}
		)
		if self.type == "Deferred Sale Item":
<<<<<<< HEAD
			entry.debit = amount
		elif self.type == "Deferred Purchase Item":
=======
	def make_dummy_gle(self, name, date , amount):
=======
>>>>>>> 15442b8 (added comments)
		entry = frappe._dict({'name': name,'posting_date': date, 'debit': 0 , 'credit': 0, 'posted': False})
		if self.type == 'Deferred Sale Item':
			entry.debit = amount
		elif self.type == 'Deferred Purchase Item':
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			entry.debit = amount
		elif self.type == "Deferred Purchase Item":
>>>>>>> 217fe49 (fixed formatting issues)
			entry.credit = amount
		return entry

	def simulate_future_posting(self):
		"""
<<<<<<< HEAD
<<<<<<< HEAD
		simulate future posting by creating dummy gl entries. starts from the last posting date.
		"""
		if add_days(self.last_entry_date, 1) < self.period_list[-1].to_date:
			self.estimate_for_period_list = get_period_list(
				self.filters.from_fiscal_year,
				self.filters.to_fiscal_year,
				add_days(self.last_entry_date, 1),
				self.period_list[-1].to_date,
				"Date Range",
				"Monthly",
				company=self.filters.company,
			)
<<<<<<< HEAD
=======
		simulate future posting by creating dummy gl entries
=======
		simulate future posting by creating dummy gl entries. starts from the last posting date.
>>>>>>> 15442b8 (added comments)
		"""
		if add_days(self.last_entry_date,1) < self.period_list[-1].to_date:
			self.estimate_for_period_list = get_period_list(self.filters.from_fiscal_year, self.filters.to_fiscal_year,
															add_days(self.last_entry_date,1), self.period_list[-1].to_date, 'Date Range', 'Monthly',
															company=self.filters.company)
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
>>>>>>> 217fe49 (fixed formatting issues)
			for period in self.estimate_for_period_list:
				amount = self.calculate_amount(period.from_date, period.to_date)
				gle = self.make_dummy_gle(period.key, period.to_date, amount)
				self.gle_entries.append(gle)

	def calculate_item_revenue_expense_for_period(self):
		"""
<<<<<<< HEAD
<<<<<<< HEAD
		calculate item postings for each period and update period_total list
		"""
		for period in self.period_list:
			period_sum = 0
			actual = 0
			for posting in list(
				filter(lambda x: period.from_date <= x.posting_date <= period.to_date, self.gle_entries,)
			):
=======
		will be used to generate data for reporting
=======
		calculate item postings for each period and update period_total list
>>>>>>> 15442b8 (added comments)
		"""
		for period in self.period_list:
			period_sum = 0
			actual = 0
<<<<<<< HEAD
			for posting in list(filter(lambda x: period.from_date <= x.posting_date <= period.to_date, self.gle_entries)):
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			for posting in list(
				filter(lambda x: period.from_date <= x.posting_date <= period.to_date, self.gle_entries,)
			):
>>>>>>> 217fe49 (fixed formatting issues)
				period_sum += self.get_amount(posting)
				if posting.posted:
					actual += self.get_amount(posting)

<<<<<<< HEAD
<<<<<<< HEAD
			for posting in list(
				filter(lambda x: period.from_date <= x.posting_date <= period.to_date, self.jre_entries,)
			):
=======
			for posting in list(filter(lambda x: period.from_date <= x.posting_date <= period.to_date, self.jre_entries)):
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			for posting in list(
				filter(lambda x: period.from_date <= x.posting_date <= period.to_date, self.jre_entries,)
			):
>>>>>>> 217fe49 (fixed formatting issues)
				period_sum += self.get_amount(posting)
				if posting.posted:
					actual += self.get_amount(posting)

<<<<<<< HEAD
<<<<<<< HEAD
			self.period_total.append(
				frappe._dict({"key": period.key, "total": period_sum, "actual": actual})
			)
		return self.period_total


class Deferred_Invoice(object):
	def __init__(self, invoice, items, filters, period_list):
		"""
		Helper class for processing invoices with deferred revenue/expense items
		invoice - string : invoice name
		items - list : frappe._dict() with item details. Refer Deferred_Item for required fields
=======
			self.period_total.append(frappe._dict({'key': period.key, 'total': period_sum, 'actual': actual}))
=======
			self.period_total.append(
				frappe._dict({"key": period.key, "total": period_sum, "actual": actual})
			)
>>>>>>> 217fe49 (fixed formatting issues)
		return self.period_total


class Deferred_Invoice(object):
	def __init__(self, invoice, items, filters, period_list):
		"""
<<<<<<< HEAD
		takes in sales invoice or purchase invoice and copies the relavant information for deferred accounting
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
		Helper class for processing invoices with deferred revenue/expense items
		invoice - string : invoice name
		items - list : frappe._dict() with item details. Refer Deferred_Item for required fields
>>>>>>> 15442b8 (added comments)
		"""
		self.name = invoice
		self.posting_date = items[0].posting_date
		self.filters = filters
		self.period_list = period_list
		self.period_total = []

		if items[0].deferred_revenue_account:
<<<<<<< HEAD
<<<<<<< HEAD
			self.type = "Sales"
		elif items[0].deferred_expense_account:
			self.type = "Purchase"
=======
			self.type = 'Sales'
		elif items[0].deferred_expense_account:
			self.type = 'Purchase'
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			self.type = "Sales"
		elif items[0].deferred_expense_account:
			self.type = "Purchase"
>>>>>>> 217fe49 (fixed formatting issues)

		self.items = []
		for item in items:
			self.items.append(Deferred_Item(item, self))

	def get_postings(self):
<<<<<<< HEAD
<<<<<<< HEAD
		"""
		get GL/Journal postings for deferred items in  invoice
		"""
		[item.get_gl_and_journal_postings() for item in self.items]

	def calculate_invoice_revenue_expense_for_period(self):
		"""
		calculate deferred revenue/expense for all items in invoice
		"""
		# initialize period_total list with invoice level total
		for period in self.period_list:
			self.period_total.append(frappe._dict({"key": period.key, "total": 0, "actual": 0}))
<<<<<<< HEAD

		for item in self.items:
			item_total = item.calculate_item_revenue_expense_for_period()
			# update invoice total
=======
=======
		"""
		get GL/Journal postings for deferred items in  invoice
		"""
>>>>>>> 15442b8 (added comments)
		[item.get_gl_and_journal_postings() for item in self.items]

	def calculate_invoice_revenue_expense_for_period(self):
		"""
		calculate deferred revenue/expense for all items in invoice
		"""
		# initialize period_total list with invoice level total
		for period in self.period_list:
				self.period_total.append(frappe._dict({'key': period.key, 'total':0, 'actual': 0}))
=======
>>>>>>> 217fe49 (fixed formatting issues)

		for item in self.items:
			item_total = item.calculate_item_revenue_expense_for_period()
<<<<<<< HEAD
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			# update invoice total
>>>>>>> 15442b8 (added comments)
			for idx, period in enumerate(self.period_list, 0):
				self.period_total[idx].total += item_total[idx].total
				self.period_total[idx].actual += item_total[idx].actual
		return self.period_total

	def estimate_future(self):
<<<<<<< HEAD
<<<<<<< HEAD
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
<<<<<<< HEAD
		for x in self.period_total:
			inv_total[x.key] = x.total
			inv_total.indent = 0
		ret_data.append(inv_total)
		list(map(lambda item: ret_data.append(item.report_data()), self.items))
		return ret_data


=======
=======
		"""
		create dummy GL entries for upcoming months for all items in invoice
		"""
>>>>>>> 15442b8 (added comments)
		[item.simulate_future_posting() for item in self.items]

	def report_data(self):
		"""
		generate report data for invoice, includes invoice total
		"""
		ret_data = []
		inv_total = frappe._dict({'name':self.name})
=======
>>>>>>> 217fe49 (fixed formatting issues)
		for x in self.period_total:
			inv_total[x.key] = x.total
			inv_total.indent = 0
		ret_data.append(inv_total)
		list(map(lambda item: ret_data.append(item.report_data()), self.items))
		return ret_data

<<<<<<< HEAD
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======

>>>>>>> 217fe49 (fixed formatting issues)
class Deferred_Income_and_Expense_Report(object):
	def __init__(self, filters=None):
		"""
		Initialize deferred revenue/expense report with user provided filters or system defaults, if none is provided
		"""
<<<<<<< HEAD
<<<<<<< HEAD

		# If no filters are provided, get user defaults
		if not filters:
			fiscal_year = frappe.get_doc("Fiscal Year", frappe.defaults.get_user_default("fiscal_year"))
			self.filters = frappe._dict(
				{
					"company": frappe.defaults.get_user_default("Company"),
					"filter_based_on": "Fiscal Year",
					"period_start_date": fiscal_year.year_start_date,
					"period_end_date": fiscal_year.year_end_date,
					"from_fiscal_year": fiscal_year.year,
					"to_fiscal_year": fiscal_year.year,
					"periodicity": "Monthly",
					"with_upcoming_postings": True,
				}
			)
=======
=======

>>>>>>> 15442b8 (added comments)
		# If no filters are provided, get user defaults
		if not filters:
<<<<<<< HEAD
			fiscal_year = frappe.get_doc('Fiscal Year', frappe.defaults.get_user_default('fiscal_year'))
<<<<<<< HEAD
			self.filters = frappe._dict({ 'company': frappe.defaults.get_user_default("Company"), 'filter_based_on': 'Fiscal Year', 'period_start_date': fiscal_year.year_start_date, 'period_end_date': fiscal_year.year_end_date, 'from_fiscal_year': fiscal_year.year, 'to_fiscal_year': fiscal_year.year, 'periodicity': 'Monthly'})
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			self.filters = frappe._dict({ 'company': frappe.defaults.get_user_default("Company"), 'filter_based_on': 'Fiscal Year', 'period_start_date': fiscal_year.year_start_date, 'period_end_date': fiscal_year.year_end_date, 'from_fiscal_year': fiscal_year.year, 'to_fiscal_year': fiscal_year.year, 'periodicity': 'Monthly', 'with_upcoming_postings': True})
>>>>>>> 6a414f2 (bug fix - cancelled postings will not considered)
=======
			fiscal_year = frappe.get_doc("Fiscal Year", frappe.defaults.get_user_default("fiscal_year"))
			self.filters = frappe._dict(
				{
					"company": frappe.defaults.get_user_default("Company"),
					"filter_based_on": "Fiscal Year",
					"period_start_date": fiscal_year.year_start_date,
					"period_end_date": fiscal_year.year_end_date,
					"from_fiscal_year": fiscal_year.year,
					"to_fiscal_year": fiscal_year.year,
					"periodicity": "Monthly",
					"with_upcoming_postings": True,
				}
			)
>>>>>>> 217fe49 (fixed formatting issues)
			self.period_list = None
		else:
			self.filters = frappe._dict(filters)

		self.def_invoices = []

<<<<<<< HEAD
<<<<<<< HEAD
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

		self.total_income = [
			frappe._dict({"key": period.key, "total": 0, "actual": 0}) for period in self.period_list
		]
		self.total_expense = [
			frappe._dict({"key": period.key, "total": 0, "actual": 0}) for period in self.period_list
		]
=======

=======
>>>>>>> 217fe49 (fixed formatting issues)
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

		self.total_income = [
			frappe._dict({"key": period.key, "total": 0, "actual": 0}) for period in self.period_list
		]
		self.total_expense = [
			frappe._dict({"key": period.key, "total": 0, "actual": 0}) for period in self.period_list
		]

<<<<<<< HEAD
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')

=======
>>>>>>> 15442b8 (added comments)
	def get_invoices(self):
		"""
		Get all sales and purchase invoices which has deferred revenue/expense items
		"""
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
		sinv = qb.DocType("Sales Invoice")
		sinv_item = qb.DocType("Sales Invoice Item")
		# sales invoices with deferred items
		query = (
			qb.from_(sinv_item)
			.join(sinv)
			.on(sinv.name == sinv_item.parent)
			.select(
				sinv.name.as_("doc"),
				sinv.posting_date,
				sinv_item.name.as_("item"),
				sinv_item.parent,
				sinv_item.item_code,
				sinv_item.item_name,
				sinv_item.service_start_date,
				sinv_item.service_end_date,
				sinv_item.base_net_amount,
				sinv_item.deferred_revenue_account,
			)
			.where(
				(sinv.docstatus == 1)
				& (sinv_item.enable_deferred_revenue == 1)
				& (
					(
						(self.period_list[0].from_date >= sinv_item.service_start_date)
						& (sinv_item.service_end_date >= self.period_list[0].from_date)
					)
					| (
						(sinv_item.service_start_date >= self.period_list[0].from_date)
						& (sinv_item.service_start_date <= self.period_list[-1].to_date)
					)
				)
			)
			.orderby(sinv.posting_date, sinv.posting_time)
		)
		self.sales_invoices = query.run(as_dict=True)

		# for each uniq sales invoice create Deferred_Invoices(helper class)
		uniq_sales_invoice = set([x.doc for x in self.sales_invoices])
		for inv in uniq_sales_invoice:
			self.def_invoices.append(
				Deferred_Invoice(
					inv,
					list(filter(lambda x: inv == x.doc, self.sales_invoices)),
					self.filters,
					self.period_list,
				)
			)

		pinv = qb.DocType("Purchase Invoice")
		pinv_item = qb.DocType("Purchase Invoice Item")
		# purchase invoices with deferred items
		query = (
			qb.from_(pinv_item)
			.join(pinv)
			.on(pinv.name == pinv_item.parent)
			.select(
				pinv.name.as_("doc"),
				pinv.posting_date,
				pinv_item.name.as_("item"),
				pinv_item.parent,
				pinv_item.item_code,
				pinv_item.item_name,
				pinv_item.service_start_date,
				pinv_item.service_end_date,
				pinv_item.base_net_amount,
				pinv_item.deferred_expense_account,
			)
			.where(
				(pinv.docstatus == 1)
				& (pinv_item.enable_deferred_expense == 1)
				& (
					(
						(self.period_list[0].from_date >= pinv_item.service_start_date)
						& (pinv_item.service_end_date >= self.period_list[0].from_date)
					)
					| (
						(pinv_item.service_start_date >= self.period_list[0].from_date)
						& (pinv_item.service_start_date <= self.period_list[-1].to_date)
					)
				)
			)
			.orderby(pinv.posting_date, pinv.posting_time)
		)
		self.purchase_invoices = query.run(as_dict=True)

		# for each uniq pruchase invoice create Deferred_Invoices(helper class)
		uniq_purchase_invoice = set([x.doc for x in self.purchase_invoices])
		for inv in uniq_purchase_invoice:
			self.def_invoices.append(
				Deferred_Invoice(
					inv,
					list(filter(lambda x: inv == x.doc, self.purchase_invoices)),
					self.filters,
					self.period_list,
				)
			)

	def get_postings(self):
		"""
		For all Invoices get GL entries and Journal postings
=======

=======
>>>>>>> 15442b8 (added comments)
		sinv = qb.DocType('Sales Invoice')
		sinv_item = qb.DocType('Sales Invoice Item')
=======
		sinv = qb.DocType("Sales Invoice")
		sinv_item = qb.DocType("Sales Invoice Item")
>>>>>>> 217fe49 (fixed formatting issues)
		# sales invoices with deferred items
		query = (
			qb.from_(sinv_item)
			.join(sinv)
			.on(sinv.name == sinv_item.parent)
			.select(
				sinv.name.as_("doc"),
				sinv.posting_date,
				sinv_item.name.as_("item"),
				sinv_item.parent,
				sinv_item.item_code,
				sinv_item.item_name,
				sinv_item.service_start_date,
				sinv_item.service_end_date,
				sinv_item.base_net_amount,
				sinv_item.deferred_revenue_account,
			)
			.where(
				(sinv.docstatus == 1)
				& (sinv_item.enable_deferred_revenue == 1)
				& (
					(
						(self.period_list[0].from_date >= sinv_item.service_start_date)
						& (sinv_item.service_end_date >= self.period_list[0].from_date)
					)
					| (
						(sinv_item.service_start_date >= self.period_list[0].from_date)
						& (sinv_item.service_start_date <= self.period_list[-1].to_date)
					)
				)
			)
			.orderby(sinv.posting_date, sinv.posting_time)
		)
		self.sales_invoices = query.run(as_dict=True)

		# for each uniq sales invoice create Deferred_Invoices(helper class)
		uniq_sales_invoice = set([x.doc for x in self.sales_invoices])
		for inv in uniq_sales_invoice:
			self.def_invoices.append(
				Deferred_Invoice(
					inv,
					list(filter(lambda x: inv == x.doc, self.sales_invoices)),
					self.filters,
					self.period_list,
				)
			)

		pinv = qb.DocType("Purchase Invoice")
		pinv_item = qb.DocType("Purchase Invoice Item")
		# purchase invoices with deferred items
		query = (
			qb.from_(pinv_item)
			.join(pinv)
			.on(pinv.name == pinv_item.parent)
			.select(
				pinv.name.as_("doc"),
				pinv.posting_date,
				pinv_item.name.as_("item"),
				pinv_item.parent,
				pinv_item.item_code,
				pinv_item.item_name,
				pinv_item.service_start_date,
				pinv_item.service_end_date,
				pinv_item.base_net_amount,
				pinv_item.deferred_expense_account,
			)
			.where(
				(pinv.docstatus == 1)
				& (pinv_item.enable_deferred_expense == 1)
				& (
					(
						(self.period_list[0].from_date >= pinv_item.service_start_date)
						& (pinv_item.service_end_date >= self.period_list[0].from_date)
					)
					| (
						(pinv_item.service_start_date >= self.period_list[0].from_date)
						& (pinv_item.service_start_date <= self.period_list[-1].to_date)
					)
				)
			)
			.orderby(pinv.posting_date, pinv.posting_time)
		)
		self.purchase_invoices = query.run(as_dict=True)

		# for each uniq pruchase invoice create Deferred_Invoices(helper class)
		uniq_purchase_invoice = set([x.doc for x in self.purchase_invoices])
		for inv in uniq_purchase_invoice:
			self.def_invoices.append(
				Deferred_Invoice(
					inv,
					list(filter(lambda x: inv == x.doc, self.purchase_invoices)),
					self.filters,
					self.period_list,
				)
			)

	def get_postings(self):
		"""
<<<<<<< HEAD
		Get all GL entries and Journal postings
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
		For all Invoices get GL entries and Journal postings
>>>>>>> 15442b8 (added comments)
		"""
		for x in self.def_invoices:
			x.get_postings()

	def estimate_future(self):
<<<<<<< HEAD
<<<<<<< HEAD
		"""
		For all Invoices get estimate upcoming postings
		"""
=======
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
		"""
		For all Invoices get estimate upcoming postings
		"""
>>>>>>> 15442b8 (added comments)
		for x in self.def_invoices:
			x.estimate_future()

	def calculate_revenue_and_expense(self):
		"""
		calculate the deferred revenue/expense for all invoices
		"""
		for inv in self.def_invoices:
			inv_total = inv.calculate_invoice_revenue_expense_for_period()
<<<<<<< HEAD
<<<<<<< HEAD
			if inv.type == "Sales":
				for idx, period in enumerate(self.period_list, 0):
					self.total_income[idx].total += inv_total[idx].total
					self.total_income[idx].actual += inv_total[idx].actual
			elif inv.type == "Purchase":
=======
			if inv.type == 'Sales':
				for idx, period in enumerate(self.period_list, 0):
					self.total_income[idx].total += inv_total[idx].total
					self.total_income[idx].actual += inv_total[idx].actual
			elif inv.type == 'Purchase':
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
			if inv.type == "Sales":
				for idx, period in enumerate(self.period_list, 0):
					self.total_income[idx].total += inv_total[idx].total
					self.total_income[idx].actual += inv_total[idx].actual
			elif inv.type == "Purchase":
>>>>>>> 217fe49 (fixed formatting issues)
				for idx, period in enumerate(self.period_list, 0):
					self.total_expense[idx].total += inv_total[idx].total
					self.total_expense[idx].actual += inv_total[idx].actual

	def get_columns(self):
		columns = []
<<<<<<< HEAD
<<<<<<< HEAD
		columns.append({"label": "Name", "fieldname": "name", "fieldtype": "Data", "read_only": 1})
		for period in self.period_list:
			columns.append(
				{"label": period.label, "fieldname": period.key, "fieldtype": "Currency", "read_only": 1,}
			)
		return columns

	def generate_report_data(self):
		"""
		Generate report data for all invoices. Adds total rows for revenue and expense
		"""
		ret = []
		for inv in filter(lambda inv: inv.type == "Sales", self.def_invoices):
			ret += inv.report_data()

		# revneue total row
		total_row = frappe._dict({"name": "Total Deferred Income"})
		for idx, period in enumerate(self.period_list, 0):
=======
		columns.append({
			'label': 'Name',
			'fieldname': 'name',
			'fieldtype': 'Data',
			'read_only': 1
		})
=======
		columns.append({"label": "Name", "fieldname": "name", "fieldtype": "Data", "read_only": 1})
>>>>>>> 217fe49 (fixed formatting issues)
		for period in self.period_list:
			columns.append(
				{"label": period.label, "fieldname": period.key, "fieldtype": "Currency", "read_only": 1,}
			)
		return columns

	def generate_report_data(self):
		"""
		Generate report data for all invoices. Adds total rows for revenue and expense
		"""
		ret = []
		for inv in filter(lambda inv: inv.type == "Sales", self.def_invoices):
			ret += inv.report_data()

		# revneue total row
<<<<<<< HEAD
		total_row = frappe._dict({'name': 'Total Deferred Income'})
		for idx, period in enumerate(self.period_list,0):
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
		total_row = frappe._dict({"name": "Total Deferred Income"})
		for idx, period in enumerate(self.period_list, 0):
>>>>>>> 217fe49 (fixed formatting issues)
			total_row[period.key] = self.total_income[idx].total
		ret.append(total_row)

		# padding with empty row
		ret += [{}]

<<<<<<< HEAD
<<<<<<< HEAD
		for inv in filter(lambda inv: inv.type == "Purchase", self.def_invoices):
			ret += inv.report_data()

		# expense total row
		total_row = frappe._dict({"name": "Total Deferred Expense"})
		for idx, period in enumerate(self.period_list, 0):
=======
		for inv in filter(lambda inv: inv.type == 'Purchase', self.def_invoices):
			ret +=  inv.report_data()

		# expense total row
		total_row = frappe._dict({'name': 'Total Deferred Expense'})
		for idx, period in enumerate(self.period_list,0):
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
		for inv in filter(lambda inv: inv.type == "Purchase", self.def_invoices):
			ret += inv.report_data()

		# expense total row
		total_row = frappe._dict({"name": "Total Deferred Expense"})
		for idx, period in enumerate(self.period_list, 0):
>>>>>>> 217fe49 (fixed formatting issues)
			total_row[period.key] = self.total_expense[idx].total
		ret.append(total_row)

		return ret

	def prepare_chart(self):
		chart = {
			"data": {
<<<<<<< HEAD
<<<<<<< HEAD
				"labels": [period.label for period in self.period_list],
				"datasets": [
					{
						"name": "Income - Actual",
						"chartType": "bar",
						"values": [x.actual for x in self.total_income],
					},
					{
						"name": "Expense - Actual",
						"chartType": "bar",
						"values": [x.actual for x in self.total_expense],
					},
				],
			},
			"type": "axis-mixed",
			"height": 500,
			"axisOptions": {"xAxisMode": "Tick", "xIsSeries": True},
			"barOptions": {"stacked": False, "spaceRatio": 0.2},
		}

		if self.filters.with_upcoming_postings:
			chart["data"]["datasets"].extend(
				[
					{
						"name": "Income - Expected",
						"chartType": "line",
						"values": [x.total for x in self.total_income],
					},
					{
						"name": "Expense - Expected",
						"chartType": "line",
						"values": [x.total for x in self.total_expense],
					},
				]
			)
=======
				'labels': [period.label for period in self.period_list],
				'datasets': [
 					{
=======
				"labels": [period.label for period in self.period_list],
				"datasets": [
					{
>>>>>>> 217fe49 (fixed formatting issues)
						"name": "Income - Actual",
						"chartType": "bar",
						"values": [x.actual for x in self.total_income],
					},
					{
						"name": "Expense - Actual",
						"chartType": "bar",
						"values": [x.actual for x in self.total_expense],
					},
				],
			},
			"type": "axis-mixed",
			"height": 500,
			"axisOptions": {"xAxisMode": "Tick", "xIsSeries": True},
			"barOptions": {"stacked": False, "spaceRatio": 0.2},
		}
<<<<<<< HEAD
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======

		if self.filters.with_upcoming_postings:
<<<<<<< HEAD
			chart['data']['datasets'].extend([
				{
					"name": "Income - Expected",
					"chartType": "line",
					"values": [x.total for x in self.total_income]
				},
				{
					"name": "Expense - Expected",
					"chartType": "line",
					"values": [x.total for x in self.total_expense]
				}])
>>>>>>> 15442b8 (added comments)
=======
			chart["data"]["datasets"].extend(
				[
					{
						"name": "Income - Expected",
						"chartType": "line",
						"values": [x.total for x in self.total_income],
					},
					{
						"name": "Expense - Expected",
						"chartType": "line",
						"values": [x.total for x in self.total_expense],
					},
				]
			)
>>>>>>> 217fe49 (fixed formatting issues)
		return chart

	def run(self, *args, **kwargs):
		"""
		Run report and generate data
		"""
		self.def_invoices.clear()
		self.get_period_list()
		self.get_invoices()
		self.get_postings()

		if self.filters.with_upcoming_postings:
			self.estimate_future()
		self.calculate_revenue_and_expense()

<<<<<<< HEAD
<<<<<<< HEAD

def execute(filters=None):
=======
=======

>>>>>>> 217fe49 (fixed formatting issues)
def execute(filters=None):
<<<<<<< HEAD
	print(filters)
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
>>>>>>> 6a414f2 (bug fix - cancelled postings will not considered)
	report = Deferred_Income_and_Expense_Report(filters=filters)
	report.run()

	columns = report.get_columns()
	data = report.generate_report_data()
	message = []
<<<<<<< HEAD
<<<<<<< HEAD
	chart = report.prepare_chart()
=======
	chart  = report.prepare_chart()
>>>>>>> fc408d6 (new report 'Deferred Revenue and Expense')
=======
	chart = report.prepare_chart()
>>>>>>> 217fe49 (fixed formatting issues)

	return columns, data, message, chart
