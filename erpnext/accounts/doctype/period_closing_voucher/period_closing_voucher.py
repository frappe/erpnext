# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_account_currency, get_fiscal_year, validate_fiscal_year
from erpnext.controllers.accounts_controller import AccountsController


class PeriodClosingVoucher(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		closing_account_head: DF.Link
		company: DF.Link
		error_message: DF.Text | None
		fiscal_year: DF.Link
		gle_processing_status: DF.Literal["In Progress", "Completed", "Failed"]
		posting_date: DF.Date
		remarks: DF.SmallText
		transaction_date: DF.Date | None
		year_start_date: DF.Date | None
	# end: auto-generated types

	def validate(self):
		self.validate_account_head()
		self.validate_posting_date()

	def on_submit(self):
		self.db_set("gle_processing_status", "In Progress")
		get_opening_entries = False

		if not frappe.db.exists(
			"Period Closing Voucher", {"company": self.company, "docstatus": 1, "name": ("!=", self.name)}
		):
			get_opening_entries = True

		self.make_gl_entries(get_opening_entries=get_opening_entries)

	def on_cancel(self):
		self.validate_future_closing_vouchers()
		self.db_set("gle_processing_status", "In Progress")
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		gle_count = frappe.db.count(
			"GL Entry",
			{"voucher_type": "Period Closing Voucher", "voucher_no": self.name, "is_cancelled": 0},
		)
		if gle_count > 5000:
			frappe.enqueue(
				make_reverse_gl_entries,
				voucher_type="Period Closing Voucher",
				voucher_no=self.name,
				queue="long",
				enqueue_after_commit=True,
			)
			frappe.msgprint(
				_("The GL Entries will be cancelled in the background, it can take a few minutes."),
				alert=True,
			)
		else:
			make_reverse_gl_entries(voucher_type="Period Closing Voucher", voucher_no=self.name)

		self.delete_closing_entries()

	def validate_future_closing_vouchers(self):
		if frappe.db.exists(
			"Period Closing Voucher",
			{"posting_date": (">", self.posting_date), "docstatus": 1, "company": self.company},
		):
			frappe.throw(
				_(
					"You can not cancel this Period Closing Voucher, please cancel the future Period Closing Vouchers first"
				)
			)

	def delete_closing_entries(self):
		closing_balance = frappe.qb.DocType("Account Closing Balance")
		frappe.qb.from_(closing_balance).delete().where(
			closing_balance.period_closing_voucher == self.name
		).run()

	def validate_account_head(self):
		closing_account_type = frappe.get_cached_value("Account", self.closing_account_head, "root_type")

		if closing_account_type not in ["Liability", "Equity"]:
			frappe.throw(
				_("Closing Account {0} must be of type Liability / Equity").format(self.closing_account_head)
			)

		account_currency = get_account_currency(self.closing_account_head)
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if account_currency != company_currency:
			frappe.throw(_("Currency of the Closing Account must be {0}").format(company_currency))

	def validate_posting_date(self):
		validate_fiscal_year(
			self.posting_date, self.fiscal_year, self.company, label=_("Posting Date"), doc=self
		)

		self.year_start_date = get_fiscal_year(self.posting_date, self.fiscal_year, company=self.company)[1]

		self.check_if_previous_year_closed()

		pcv = frappe.qb.DocType("Period Closing Voucher")
		existing_entry = (
			frappe.qb.from_(pcv)
			.select(pcv.name)
			.where(
				(pcv.posting_date >= self.posting_date)
				& (pcv.fiscal_year == self.fiscal_year)
				& (pcv.docstatus == 1)
				& (pcv.company == self.company)
			)
			.run()
		)

		if existing_entry and existing_entry[0][0]:
			frappe.throw(
				_("Another Period Closing Entry {0} has been made after {1}").format(
					existing_entry[0][0], self.posting_date
				)
			)

	def check_if_previous_year_closed(self):
		last_year_closing = add_days(self.year_start_date, -1)
		previous_fiscal_year = get_fiscal_year(last_year_closing, company=self.company, boolean=True)
		if not previous_fiscal_year:
			return

		previous_fiscal_year_start_date = previous_fiscal_year[0][1]
		if not frappe.db.exists(
			"GL Entry",
			{
				"posting_date": ("between", [previous_fiscal_year_start_date, last_year_closing]),
				"company": self.company,
				"is_cancelled": 0,
			},
		):
			return

		if not frappe.db.exists(
			"Period Closing Voucher",
			{
				"posting_date": ("between", [previous_fiscal_year_start_date, last_year_closing]),
				"docstatus": 1,
				"company": self.company,
			},
		):
			frappe.throw(_("Previous Year is not closed, please close it first"))

	def make_gl_entries(self, get_opening_entries=False):
		gl_entries = self.get_gl_entries()
		closing_entries = self.get_grouped_gl_entries(get_opening_entries=get_opening_entries)
		if len(gl_entries + closing_entries) > 3000:
			frappe.enqueue(
				process_gl_entries,
				gl_entries=gl_entries,
				voucher_name=self.name,
				timeout=3000,
			)

			frappe.enqueue(
				process_closing_entries,
				gl_entries=gl_entries,
				closing_entries=closing_entries,
				voucher_name=self.name,
				company=self.company,
				closing_date=self.posting_date,
				timeout=3000,
			)

			frappe.msgprint(
				_("The GL Entries will be processed in the background, it can take a few minutes."),
				alert=True,
			)
		else:
			process_gl_entries(gl_entries, self.name)
			process_closing_entries(gl_entries, closing_entries, self.name, self.company, self.posting_date)

	def get_grouped_gl_entries(self, get_opening_entries=False):
		closing_entries = []
		for acc in self.get_balances_based_on_dimensions(
			group_by_account=True, for_aggregation=True, get_opening_entries=get_opening_entries
		):
			closing_entries.append(self.get_closing_entries(acc))

		return closing_entries

	def get_gl_entries(self):
		gl_entries = []

		# pl account
		for acc in self.get_balances_based_on_dimensions(
			group_by_account=True, report_type="Profit and Loss"
		):
			if flt(acc.bal_in_company_currency):
				gl_entries.append(self.get_gle_for_pl_account(acc))

		# closing liability account
		for acc in self.get_balances_based_on_dimensions(
			group_by_account=False, report_type="Profit and Loss"
		):
			if flt(acc.bal_in_company_currency):
				gl_entries.append(self.get_gle_for_closing_account(acc))

		return gl_entries

	def get_gle_for_pl_account(self, acc):
		gl_entry = self.get_gl_dict(
			{
				"company": self.company,
				"closing_date": self.posting_date,
				"account": acc.account,
				"cost_center": acc.cost_center,
				"finance_book": acc.finance_book,
				"account_currency": acc.account_currency,
				"debit_in_account_currency": abs(flt(acc.bal_in_account_currency))
				if flt(acc.bal_in_account_currency) < 0
				else 0,
				"debit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) < 0 else 0,
				"credit_in_account_currency": abs(flt(acc.bal_in_account_currency))
				if flt(acc.bal_in_account_currency) > 0
				else 0,
				"credit": abs(flt(acc.bal_in_company_currency))
				if flt(acc.bal_in_company_currency) > 0
				else 0,
				"is_period_closing_voucher_entry": 1,
			},
			item=acc,
		)
		self.update_default_dimensions(gl_entry, acc)
		return gl_entry

	def get_gle_for_closing_account(self, acc):
		gl_entry = self.get_gl_dict(
			{
				"company": self.company,
				"closing_date": self.posting_date,
				"account": self.closing_account_head,
				"cost_center": acc.cost_center,
				"finance_book": acc.finance_book,
				"account_currency": acc.account_currency,
				"debit_in_account_currency": abs(flt(acc.bal_in_account_currency))
				if flt(acc.bal_in_account_currency) > 0
				else 0,
				"debit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) > 0 else 0,
				"credit_in_account_currency": abs(flt(acc.bal_in_account_currency))
				if flt(acc.bal_in_account_currency) < 0
				else 0,
				"credit": abs(flt(acc.bal_in_company_currency))
				if flt(acc.bal_in_company_currency) < 0
				else 0,
				"is_period_closing_voucher_entry": 1,
			},
			item=acc,
		)
		self.update_default_dimensions(gl_entry, acc)
		return gl_entry

	def get_closing_entries(self, acc):
		closing_entry = self.get_gl_dict(
			{
				"company": self.company,
				"closing_date": self.posting_date,
				"period_closing_voucher": self.name,
				"account": acc.account,
				"cost_center": acc.cost_center,
				"finance_book": acc.finance_book,
				"account_currency": acc.account_currency,
				"debit_in_account_currency": flt(acc.debit_in_account_currency),
				"debit": flt(acc.debit),
				"credit_in_account_currency": flt(acc.credit_in_account_currency),
				"credit": flt(acc.credit),
			},
			item=acc,
		)

		for dimension in self.accounting_dimensions:
			closing_entry.update({dimension: acc.get(dimension)})

		return closing_entry

	def update_default_dimensions(self, gl_entry, acc):
		if not self.accounting_dimensions:
			self.accounting_dimensions = get_accounting_dimensions()

		for dimension in self.accounting_dimensions:
			gl_entry.update({dimension: acc.get(dimension)})

	def get_balances_based_on_dimensions(
		self, group_by_account=False, report_type=None, for_aggregation=False, get_opening_entries=False
	):
		"""Get balance for dimension-wise pl accounts"""

		qb_dimension_fields = ["cost_center", "finance_book", "project"]

		self.accounting_dimensions = get_accounting_dimensions()
		for dimension in self.accounting_dimensions:
			qb_dimension_fields.append(dimension)

		if group_by_account:
			qb_dimension_fields.append("account")

		account_filters = {
			"company": self.company,
			"is_group": 0,
		}

		if report_type:
			account_filters.update({"report_type": report_type})

		accounts = frappe.get_all("Account", filters=account_filters, pluck="name")

		gl_entry = frappe.qb.DocType("GL Entry")
		query = frappe.qb.from_(gl_entry).select(gl_entry.account, gl_entry.account_currency)

		if not for_aggregation:
			query = query.select(
				(Sum(gl_entry.debit_in_account_currency) - Sum(gl_entry.credit_in_account_currency)).as_(
					"bal_in_account_currency"
				),
				(Sum(gl_entry.debit) - Sum(gl_entry.credit)).as_("bal_in_company_currency"),
			)
		else:
			query = query.select(
				(Sum(gl_entry.debit_in_account_currency)).as_("debit_in_account_currency"),
				(Sum(gl_entry.credit_in_account_currency)).as_("credit_in_account_currency"),
				(Sum(gl_entry.debit)).as_("debit"),
				(Sum(gl_entry.credit)).as_("credit"),
			)

		for dimension in qb_dimension_fields:
			query = query.select(gl_entry[dimension])

		query = query.where(
			(gl_entry.company == self.company)
			& (gl_entry.is_cancelled == 0)
			& (gl_entry.account.isin(accounts))
		)

		if get_opening_entries:
			query = query.where(
				gl_entry.posting_date.between(self.get("year_start_date"), self.posting_date)
				| gl_entry.is_opening
				== "Yes"
			)
		else:
			query = query.where(
				gl_entry.posting_date.between(self.get("year_start_date"), self.posting_date)
				& gl_entry.is_opening
				== "No"
			)

		if for_aggregation:
			query = query.where(gl_entry.voucher_type != "Period Closing Voucher")

		for dimension in qb_dimension_fields:
			query = query.groupby(gl_entry[dimension])

		return query.run(as_dict=1)


def process_gl_entries(gl_entries, voucher_name):
	from erpnext.accounts.general_ledger import make_gl_entries

	try:
		if gl_entries:
			make_gl_entries(gl_entries, merge_entries=False)
		frappe.db.set_value("Period Closing Voucher", voucher_name, "gle_processing_status", "Completed")
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(e)
		frappe.db.set_value("Period Closing Voucher", voucher_name, "gle_processing_status", "Failed")


def process_closing_entries(gl_entries, closing_entries, voucher_name, company, closing_date):
	from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
		make_closing_entries,
	)

	try:
		if gl_entries + closing_entries:
			make_closing_entries(gl_entries + closing_entries, voucher_name, company, closing_date)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(e)


def make_reverse_gl_entries(voucher_type, voucher_no):
	from erpnext.accounts.general_ledger import make_reverse_gl_entries

	try:
		make_reverse_gl_entries(voucher_type=voucher_type, voucher_no=voucher_no)
		frappe.db.set_value("Period Closing Voucher", voucher_no, "gle_processing_status", "Completed")
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(e)
		frappe.db.set_value("Period Closing Voucher", voucher_no, "gle_processing_status", "Failed")
