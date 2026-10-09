# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.treasury.doctype.investment_transaction.investment_transaction import get_units_held

OPEN_STATUSES = ("Active", "Partially Redeemed")
REVALUATION_INSTRUMENTS = ("Units", "Bond")
# measurement categories whose fair value changes are posted to the ledger
GL_CATEGORIES = ("FVOCI", "FVTPL")


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
		self.validate_duplicate_investments()
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

	def get_previous_row(self, investment):
		"""Row of the investment's latest other submitted revaluation, fetched once."""
		if not hasattr(self, "_previous_rows"):
			self._previous_rows = {}

		if investment not in self._previous_rows:
			self._previous_rows[investment] = get_latest_revaluation_row(investment, self.name)

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
		row.posts_to_ledger = int(investment.measurement_category in GL_CATEGORIES)
		self.set_book_values(row, investment)
		self.set_fair_value(row, investment)
		row.adjustment_amount = flt(
			row.unrealised_gain_loss - row.previous_gain_loss, row.precision("adjustment_amount")
		)

	def set_book_values(self, row, investment):
		"""Book value, previous amount and units held on the revaluation date."""
		previous_row = self.get_previous_row(row.investment)
		row.book_value = investment.get_ledger_balance(investment.investment_account, self.revaluation_date)
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
		"""Fair value adjustment against unrealised gain / loss."""
		investment = self.get_investment(row.investment)
		increase, decrease = max(flt(row.adjustment_amount), 0), max(-flt(row.adjustment_amount), 0)
		debit_account = investment.get_account("fair_value_adjustment_account")
		credit_account = investment.get_account("unrealised_gain_loss_account")

		return [(debit_account, increase, decrease), (credit_account, decrease, increase)]

	def get_gl_entry(self, row, account, debit, credit):
		precision = self.precision("total_gain_loss")
		return self.get_gl_dict(
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

		previous_row = self.get_previous_row(investment.name)
		return bool(previous_row and flt(previous_row.unrealised_gain_loss))

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


def get_latest_revaluation_row(investment, exclude_revaluation=None):
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

	result = query.run(as_dict=True)
	return result[0] if result else None
