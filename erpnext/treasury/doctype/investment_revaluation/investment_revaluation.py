# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from copy import copy

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
	EXIT_TYPES,
	get_units_held,
	lock_investment,
)

OPEN_STATUSES = ("Active", "Partially Redeemed")
REVALUATION_INSTRUMENTS = ("Units", "Bond")


class InvestmentRevaluation(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.treasury.doctype.investment_revaluation_detail.investment_revaluation_detail import (
			InvestmentRevaluationDetail,
		)

		amended_from: DF.Link | None
		company: DF.Link
		cost_center: DF.Link | None
		currency: DF.Link | None
		finance_book: DF.Link | None
		investments: DF.Table[InvestmentRevaluationDetail]
		naming_series: DF.Literal["INV-REVAL-.YYYY.-"]
		remarks: DF.SmallText | None
		revaluation_date: DF.Date
		total_gain_loss: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.set_missing_values()
		self.validate_company_in_accounting_dimension()
		self.validate_duplicate_investments()
		self.lock_investments()
		for row in self.investments:
			self.validate_row(row)
			self.set_row_values(row)

		self.set_total_gain_loss()

	def on_submit(self):
		self.make_gl_entries()
		self.update_investments()

	def before_cancel(self):
		super().before_cancel()
		self.validate_is_latest_revaluation()
		self.validate_no_later_exits()

	def on_cancel(self):
		super().on_cancel()
		self.ignore_linked_doctypes = ("GL Entry",)
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
		self.update_investments()

	def get_investment(self, investment):
		if not hasattr(self, "_investments"):
			self._investments = {}

		if investment not in self._investments:
			self._investments[investment] = frappe.get_doc("Investment", investment)

		return self._investments[investment]

	def lock_investments(self):
		"""On submit, lock the investments so two revaluations submitted together cannot both
		post the change from the same previous value. Sorted, so they always lock in the same order."""
		if self.docstatus == 1:
			for investment in sorted({row.investment for row in self.investments}):
				lock_investment(investment)

	def get_previous_row(self, investment):
		"""Row of the investment's latest other submitted revaluation, fetched once."""
		if not hasattr(self, "_previous_rows"):
			self._previous_rows = {}

		if investment not in self._previous_rows:
			self._previous_rows[investment] = get_latest_revaluation_row(
				investment, self.name, for_update=self.docstatus == 1
			)

		return self._previous_rows[investment]

	def set_missing_values(self):
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

	def validate_duplicate_investments(self):
		seen = set()
		for row in self.investments:
			if row.investment in seen:
				frappe.throw(
					_("Row #{0}: Investment {1} is added more than once").format(
						row.idx, frappe.bold(row.investment)
					)
				)
			seen.add(row.investment)

	def validate_row(self, row):
		self.validate_row_investment(row)
		self.validate_after_previous_revaluation(row)
		self.set_row_conversion_rate(row)
		self.validate_row_inputs(row)

	def validate_row_investment(self, row):
		investment = self.get_investment(row.investment)
		if investment.docstatus != 1 or investment.company != self.company:
			frappe.throw(
				_(
					"Row #{0}: Investment {1} must be an approved (submitted) investment of Company {2}"
				).format(row.idx, frappe.bold(row.investment), frappe.bold(self.company))
			)

		if getdate(self.revaluation_date) < getdate(investment.purchase_date):
			frappe.throw(
				_("Row #{0}: Revaluation Date cannot be before the Purchase Date of Investment {1}").format(
					row.idx, frappe.bold(row.investment)
				)
			)

		if investment.instrument_class not in REVALUATION_INSTRUMENTS:
			frappe.throw(
				_("Row #{0}: {1} instruments have no market value to revalue").format(
					row.idx, frappe.bold(investment.instrument_class)
				)
			)

	def validate_after_previous_revaluation(self, row):
		"""Each revaluation posts only the change since the previous one, so they must stay in date order."""
		previous_row = self.get_previous_row(row.investment)
		if previous_row and getdate(self.revaluation_date) <= getdate(previous_row.revaluation_date):
			frappe.throw(
				_("Row #{0}: Investment {1} is already valued on {2} in {3}").format(
					row.idx,
					frappe.bold(row.investment),
					frappe.bold(frappe.format_value(previous_row.revaluation_date, "Date")),
					frappe.bold(previous_row.parent),
				)
			)

	def set_row_conversion_rate(self, row):
		"""Prices are in the investment currency; an investment in company currency needs no conversion."""
		if self.get_investment(row.investment).currency == erpnext.get_company_currency(self.company):
			row.conversion_rate = 1

	def validate_row_inputs(self, row):
		for fieldname in ("nav_per_unit", "market_price"):
			if flt(row.get(fieldname)) < 0:
				frappe.throw(
					_("Row #{0}: {1} cannot be negative").format(row.idx, _(row.meta.get_label(fieldname)))
				)

		if flt(row.conversion_rate) <= 0:
			frappe.throw(_("Row #{0}: Exchange Rate must be greater than zero").format(row.idx))

	def set_row_values(self, row):
		investment = self.get_investment(row.investment)
		row.posts_to_ledger = int(investment.posts_fair_value())
		self.set_book_values(row, investment)
		self.set_fair_value(row, investment)
		row.adjustment_amount = flt(
			row.unrealised_gain_loss - row.previous_gain_loss, row.precision("adjustment_amount")
		)

	def set_book_values(self, row, investment):
		"""Book value, previous amount and units held on the revaluation date."""
		row.book_value = investment.get_ledger_balance(investment.investment_account, self.revaluation_date)
		if investment.posts_fair_value():
			# what is on the books, after exits took their share of earlier revaluations
			row.previous_gain_loss = investment.get_ledger_balance(
				investment.fair_value_adjustment_account, self.revaluation_date
			)
		else:
			previous_row = self.get_previous_row(row.investment)
			row.previous_gain_loss = flt(previous_row.unrealised_gain_loss) if previous_row else 0

		row.units_held = flt(
			get_units_held(investment.name, self.revaluation_date), row.precision("units_held")
		)

	def set_fair_value(self, row, investment):
		price = row.nav_per_unit if investment.instrument_class == "Units" else row.market_price

		if row.units_held and flt(price) <= 0:
			frappe.throw(
				_("Row #{0}: Please enter the {1} of Investment {2}").format(
					row.idx,
					_("NAV per Unit") if investment.instrument_class == "Units" else _("Market Price"),
					frappe.bold(row.investment),
				)
			)

		market_value = flt(row.units_held) * flt(price) * flt(row.conversion_rate)
		row.market_value = flt(market_value, row.precision("market_value"))
		row.unrealised_gain_loss = flt(
			row.market_value - flt(row.book_value), row.precision("unrealised_gain_loss")
		)

	def set_total_gain_loss(self):
		total = sum(flt(row.adjustment_amount) for row in self.investments)
		self.total_gain_loss = flt(total, self.precision("total_gain_loss"))

	def validate_is_latest_revaluation(self):
		for row in self.investments:
			later_row = get_latest_revaluation_row(row.investment, self.name)
			if later_row and getdate(later_row.revaluation_date) > getdate(self.revaluation_date):
				frappe.throw(
					_("Please cancel the later Investment Revaluation {0} of Investment {1} first").format(
						frappe.bold(later_row.parent), frappe.bold(row.investment)
					)
				)

	def validate_no_later_exits(self):
		"""Exits after this revaluation took their share of its fair value gain off the books."""
		transaction = frappe.qb.DocType("Investment Transaction")
		for row in self.investments:
			if not cint(row.posts_to_ledger):
				continue

			later_exit = (
				frappe.qb.from_(transaction)
				.select(transaction.name)
				.where(transaction.investment == row.investment)
				.where(transaction.docstatus == 1)
				.where(transaction.transaction_type.isin(EXIT_TYPES))
				.where(
					(transaction.posting_date > self.revaluation_date)
					| (
						(transaction.posting_date == self.revaluation_date)
						& (transaction.creation > self.creation)
					)
				)
				.limit(1)
			).run()
			if later_exit:
				frappe.throw(
					_("Please cancel the exits of Investment {0} made after {1} first").format(
						frappe.bold(row.investment),
						frappe.bold(frappe.format_value(self.revaluation_date, "Date")),
					)
				)

	def update_investments(self):
		for row in self.investments:
			self.get_investment(row.investment).update_revaluation()

	def make_gl_entries(self):
		make_gl_entries(self.get_gl_entries())

	def get_gl_entries(self):
		gl_entries = []
		for row in self.investments:
			if not (cint(row.posts_to_ledger) and flt(row.adjustment_amount)):
				continue

			for account, debit, credit in self.get_row_entries(row):
				gl_entries.append(self.get_gl_entry(row, account, debit, credit))

		return gl_entries

	def get_row_entries(self, row):
		"""Fair value adjustment against profit and loss (FVTPL) or the equity reserve (FVOCI)."""
		investment = self.get_investment(row.investment)
		increase, decrease = max(flt(row.adjustment_amount), 0), max(-flt(row.adjustment_amount), 0)
		debit_account = investment.get_account("fair_value_adjustment_account")
		credit_account = investment.get_fair_value_gain_account()

		return [(debit_account, increase, decrease), (credit_account, decrease, increase)]

	def get_gl_entry(self, row, account, debit, credit):
		precision = self.precision("total_gain_loss")
		# each row is in its investment's currency and rate, so its accounts may be in that currency too
		row_doc = copy(self)
		row_doc.currency = self.get_investment(row.investment).currency
		row_doc.conversion_rate = row.conversion_rate

		return row_doc.get_gl_dict(
			{
				"account": account,
				"debit": flt(debit, precision),
				"credit": flt(credit, precision),
				"against": row.investment,
				"cost_center": self.cost_center,
				"finance_book": self.finance_book,
				"posting_date": self.revaluation_date,
				"voucher_detail_no": row.name,
			},
			item=row,
		)

	@frappe.whitelist()
	def set_investments(self):
		"""Fill the table with investments to value, including exited ones still carrying an amount."""
		self.set("investments", [])
		for investment in get_investments_to_value(self.company):
			if self.has_amount_to_carry(investment):
				row = self.append("investments", {"investment": investment.name})
				self.set_row_preview(row)

	def has_amount_to_carry(self, investment):
		if investment.status in OPEN_STATUSES:
			return True

		return bool(self.get_investment(investment.name).get_unrealised_gain_loss())

	def set_row_preview(self, row):
		"""Ledger figures shown before the user enters prices; recalculated in full on save."""
		investment = self.get_investment(row.investment)
		row.update(
			{
				"instrument_class": investment.instrument_class,
				"investment_currency": investment.currency,
				"measurement_category": investment.measurement_category,
			}
		)
		self.set_book_values(row, investment)
		self.set_row_conversion_rate(row)


def get_investments_to_value(company):
	return frappe.get_list(
		"Investment",
		filters={"company": company, "docstatus": 1, "instrument_class": ("in", REVALUATION_INSTRUMENTS)},
		fields=["name", "status"],
		order_by="name asc",
	)


def get_latest_revaluation_row(investment, exclude_revaluation=None, for_update=False):
	"""Row of the investment's latest submitted revaluation, optionally ignoring one revaluation."""
	revaluation = frappe.qb.DocType("Investment Revaluation")
	row = frappe.qb.DocType("Investment Revaluation Detail")
	query = (
		frappe.qb.from_(row)
		.join(revaluation)
		.on(row.parent == revaluation.name)
		.select(
			row.parent,
			revaluation.revaluation_date,
			row.unrealised_gain_loss,
		)
		.where(row.parenttype == "Investment Revaluation")
		.where(row.investment == investment)
		.where(revaluation.docstatus == 1)
		.orderby(revaluation.revaluation_date, order=frappe.qb.desc)
		.orderby(revaluation.creation, order=frappe.qb.desc)
		.limit(1)
	)
	if exclude_revaluation:
		query = query.where(revaluation.name != exclude_revaluation)

	if for_update:
		query = query.for_update()

	result = query.run(as_dict=True)
	return result[0] if result else None
