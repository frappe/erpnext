# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (get_accounting_dimensions,
	get_dimensions)

class PeriodClosingVoucher(AccountsController):
	def validate(self):
		self.validate_account_head()
		self.validate_posting_date()

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.ignore_linked_doctypes = ('GL Entry', 'Stock Ledger Entry')
		from erpnext.accounts.general_ledger import make_reverse_gl_entries
		make_reverse_gl_entries(voucher_type="Period Closing Voucher", voucher_no=self.name)

	def validate_account_head(self):
		closing_account_type = frappe.db.get_value("Account", self.closing_account_head, "root_type")

		if closing_account_type not in ["Liability", "Equity"]:
			frappe.throw(_("Closing Account {0} must be of type Liability / Equity")
				.format(self.closing_account_head))

		account_currency = get_account_currency(self.closing_account_head)
		company_currency = frappe.get_cached_value('Company',  self.company,  "default_currency")
		if account_currency != company_currency:
			frappe.throw(_("Currency of the Closing Account must be {0}").format(company_currency))

	def validate_posting_date(self):
		from erpnext.accounts.utils import get_fiscal_year, validate_fiscal_year

		validate_fiscal_year(self.posting_date, self.fiscal_year, self.company, label=_("Posting Date"), doc=self)

		self.year_start_date = get_fiscal_year(self.posting_date, self.fiscal_year, company=self.company)[1]

		pce = frappe.db.sql("""select name from `tabPeriod Closing Voucher`
			where posting_date > %s and fiscal_year = %s and docstatus = 1""",
			(self.posting_date, self.fiscal_year))
		if pce and pce[0][0]:
			frappe.throw(_("Another Period Closing Entry {0} has been made after {1}")
				.format(pce[0][0], self.posting_date))

	def make_gl_entries(self):
		gl_entries = []
		net_pl_balance = 0 

		pl_accounts = self.get_pl_balances()

		for acc in pl_accounts:
			if flt(acc.bal_in_company_currency):
				gl_entries.append(self.get_gl_dict({
					"account": acc.account,
					"cost_center": acc.cost_center,
					"account_currency": acc.account_currency,
					"debit_in_account_currency": abs(flt(acc.bal_in_account_currency)) if flt(acc.bal_in_account_currency) < 0 else 0,
					"debit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) < 0 else 0,
					"credit_in_account_currency": abs(flt(acc.bal_in_account_currency)) if flt(acc.bal_in_account_currency) > 0 else 0,
					"credit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) > 0 else 0
				}, item=acc))

				net_pl_balance += flt(acc.bal_in_company_currency)

		if net_pl_balance:
			if self.cost_center_wise_pnl:
				costcenter_wise_gl_entries = self.get_costcenter_wise_pnl_gl_entries(pl_accounts)
				gl_entries += costcenter_wise_gl_entries
			else:
				gl_entry = self.get_pnl_gl_entry(net_pl_balance)
				gl_entries.append(gl_entry)

		from erpnext.accounts.general_ledger import make_gl_entries
		make_gl_entries(gl_entries)
	
	def get_pnl_gl_entry(self, net_pl_balance):
		cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		gl_entry = self.get_gl_dict({
			"account": self.closing_account_head,
			"debit_in_account_currency": abs(net_pl_balance) if net_pl_balance > 0 else 0,
			"debit": abs(net_pl_balance) if net_pl_balance > 0 else 0,
			"credit_in_account_currency": abs(net_pl_balance) if net_pl_balance < 0 else 0,
			"credit": abs(net_pl_balance) if net_pl_balance < 0 else 0,
			"cost_center": cost_center
		})

		self.update_default_dimensions(gl_entry)

		return gl_entry

	def get_costcenter_wise_pnl_gl_entries(self, pl_accounts):
		company_cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		gl_entries = []

		for acc in pl_accounts:
			if flt(acc.bal_in_company_currency):
				gl_entry = self.get_gl_dict({
					"account": self.closing_account_head,
					"cost_center": acc.cost_center or company_cost_center,
					"account_currency": acc.account_currency,
					"debit_in_account_currency": abs(flt(acc.bal_in_account_currency)) if flt(acc.bal_in_account_currency) > 0 else 0,
					"debit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) > 0 else 0,
					"credit_in_account_currency": abs(flt(acc.bal_in_account_currency)) if flt(acc.bal_in_account_currency) < 0 else 0,
					"credit": abs(flt(acc.bal_in_company_currency)) if flt(acc.bal_in_company_currency) < 0 else 0
				}, item=acc)

				self.update_default_dimensions(gl_entry)

				gl_entries.append(gl_entry)

		return gl_entries

	def update_default_dimensions(self, gl_entry):
		if not self.accounting_dimensions:
			self.accounting_dimensions = get_accounting_dimensions()

		_, default_dimensions = get_dimensions()
		for dimension in self.accounting_dimensions:
			gl_entry.update({
				dimension: default_dimensions.get(self.company, {}).get(dimension)
			})

	def get_pl_balances(self):
		"""Get balance for dimension-wise pl accounts"""

		dimension_fields = ['t1.cost_center']

		self.accounting_dimensions = get_accounting_dimensions()
		for dimension in self.accounting_dimensions:
			dimension_fields.append('t1.{0}'.format(dimension))

		return frappe.db.sql("""
			select
				t1.account, t2.account_currency, {dimension_fields},
				sum(t1.debit_in_account_currency) - sum(t1.credit_in_account_currency) as bal_in_account_currency,
				sum(t1.debit) - sum(t1.credit) as bal_in_company_currency
			from `tabGL Entry` t1, `tabAccount` t2
			where t1.account = t2.name and t2.report_type = 'Profit and Loss'
			and t2.docstatus < 2 and t2.company = %s
			and t1.posting_date between %s and %s
			group by t1.account, {dimension_fields}
		""".format(dimension_fields = ', '.join(dimension_fields)), (self.company, self.get("year_start_date"), self.posting_date), as_dict=1)
