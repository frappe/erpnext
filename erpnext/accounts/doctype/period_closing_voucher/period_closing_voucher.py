# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.accounts_controller import AccountsController


class PeriodClosingVoucher(AccountsController):
	def validate(self):
		self.validate_account_head()
		self.validate_posting_date()

	def on_submit(self):
		self.db_set("gle_processing_status", "In Progress")
		self.make_gl_entries()

	def on_cancel(self):
		self.db_set("gle_processing_status", "In Progress")
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
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
			)
			frappe.msgprint(
				_("The GL Entries will be cancelled in the background, it can take a few minutes."), alert=True
			)
		else:
			make_reverse_gl_entries(voucher_type="Period Closing Voucher", voucher_no=self.name)

	def validate_account_head(self):
		closing_account_type = frappe.db.get_value("Account", self.closing_account_head, "root_type")

		if closing_account_type not in ["Liability", "Equity"]:
			frappe.throw(
				_("Closing Account {0} must be of type Liability / Equity").format(self.closing_account_head)
			)

		account_currency = get_account_currency(self.closing_account_head)
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")
		if account_currency != company_currency:
			frappe.throw(_("Currency of the Closing Account must be {0}").format(company_currency))

	def validate_posting_date(self):
		from erpnext.accounts.utils import get_fiscal_year, validate_fiscal_year

		validate_fiscal_year(
			self.posting_date, self.fiscal_year, self.company, label=_("Posting Date"), doc=self
		)

		self.year_start_date = get_fiscal_year(
			self.posting_date, self.fiscal_year, company=self.company
		)[1]

		pce = frappe.db.sql(
			"""select name from `tabPeriod Closing Voucher`
			where posting_date > %s and fiscal_year = %s and docstatus = 1 and company = %s""",
			(self.posting_date, self.fiscal_year, self.company),
		)
		if pce and pce[0][0]:
			frappe.throw(
				_("Another Period Closing Entry {0} has been made after {1}").format(
					pce[0][0], self.posting_date
				)
			)

	def make_gl_entries(self):
		gl_entries = self.get_gl_entries()
		if gl_entries:
			if len(gl_entries) > 5000:
				frappe.enqueue(process_gl_entries, gl_entries=gl_entries, queue="long")
				frappe.msgprint(
					_("The GL Entries will be processed in the background, it can take a few minutes."),
					alert=True,
				)
			else:
				process_gl_entries(gl_entries)

	def get_gl_entries(self):
		gl_entries = []

		# pl account
		for acc in self.get_pl_balances_based_on_dimensions(group_by_account=True):
			if flt(acc.bal_in_company_currency):
				gl_entries.append(self.get_gle_for_pl_account(acc))

		# closing liability account
		for acc in self.get_pl_balances_based_on_dimensions(group_by_account=False):
			if flt(acc.bal_in_company_currency):
				gl_entries.append(self.get_gle_for_closing_account(acc))

		return gl_entries

	def get_gle_for_pl_account(self, acc):
		gl_entry = self.get_gl_dict(
			{
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
				"credit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) > 0 else 0,
			},
			item=acc,
		)
		self.update_default_dimensions(gl_entry, acc)
		return gl_entry

	def get_gle_for_closing_account(self, acc):
		gl_entry = self.get_gl_dict(
			{
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
				"credit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) < 0 else 0,
			},
			item=acc,
		)
		self.update_default_dimensions(gl_entry, acc)
		return gl_entry

	def update_default_dimensions(self, gl_entry, acc):
		if not self.accounting_dimensions:
			self.accounting_dimensions = get_accounting_dimensions()

		for dimension in self.accounting_dimensions:
			gl_entry.update({dimension: acc.get(dimension)})

	def get_pl_balances_based_on_dimensions(self, group_by_account=False):
		"""Get balance for dimension-wise pl accounts"""

		dimension_fields = ["t1.cost_center", "t1.finance_book"]

		self.accounting_dimensions = get_accounting_dimensions()
		for dimension in self.accounting_dimensions:
			dimension_fields.append("t1.{0}".format(dimension))

		if group_by_account:
			dimension_fields.append("t1.account")

		return frappe.db.sql(
			"""
			select
				t2.account_currency,
				{dimension_fields},
				sum(t1.debit_in_account_currency) - sum(t1.credit_in_account_currency) as bal_in_account_currency,
				sum(t1.debit) - sum(t1.credit) as bal_in_company_currency
			from `tabGL Entry` t1, `tabAccount` t2
			where
				t1.is_cancelled = 0
				and t1.account = t2.name
				and t2.report_type = 'Profit and Loss'
				and t2.docstatus < 2
				and t2.company = %s
				and t1.posting_date between %s and %s
			group by {dimension_fields}
		""".format(
				dimension_fields=", ".join(dimension_fields)
			),
			(self.company, self.get("year_start_date"), self.posting_date),
			as_dict=1,
		)


def process_gl_entries(gl_entries):
	from erpnext.accounts.general_ledger import make_gl_entries

	try:
		make_gl_entries(gl_entries, merge_entries=False)
		frappe.db.set_value(
			"Period Closing Voucher", gl_entries[0].get("voucher_no"), "gle_processing_status", "Completed"
		)
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(e)
		frappe.db.set_value(
			"Period Closing Voucher", gl_entries[0].get("voucher_no"), "gle_processing_status", "Failed"
		)


def make_reverse_gl_entries(voucher_type, voucher_no):
	from erpnext.accounts.general_ledger import make_reverse_gl_entries

	try:
		make_reverse_gl_entries(voucher_type=voucher_type, voucher_no=voucher_no)
		frappe.db.set_value("Period Closing Voucher", voucher_no, "gle_processing_status", "Completed")
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(e)
		frappe.db.set_value("Period Closing Voucher", voucher_no, "gle_processing_status", "Failed")
