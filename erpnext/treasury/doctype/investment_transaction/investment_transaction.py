# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, getdate

import erpnext
from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
	get_temporary_opening_account,
)
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.treasury.doctype.investment.investment import validate_company_links
from erpnext.treasury.interest import INTEREST_CLASSES, InterestCalculator, take_fifo
from erpnext.treasury.interest_schedule import get_schedule, update_interest_schedule

PURCHASE_TYPES = ("Opening", "Purchase")
EXIT_TYPES = ("Sale", "Redemption", "Withdrawal", "Maturity")
INCOME_TYPES = ("Interest Receipt", "Dividend")
NON_CASH_TYPES = ("Opening",)
UNIT_CLASSES = ("Units", "Bond")
AMOUNT_FIELDS = (
	"units",
	"rate",
	"gross_amount",
	"charges",
	"tax_withheld",
	"interest_amount",
	"accrued_interest_in_purchase",
	"accrued_interest_in_sale",
	"penalty_applied",
)

# transaction types that only make sense for some instruments; types not listed are allowed for all
ALLOWED_INSTRUMENTS = {
	"Sale": UNIT_CLASSES,
	"Redemption": UNIT_CLASSES,
	"Withdrawal": ("Deposit",),
	"Maturity": ("Deposit", "Bond"),
	"Interest Receipt": ("Deposit", "Bond"),
	"Dividend": ("Units",),
}


class InvestmentTransaction(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accrued_interest_in_purchase: DF.Currency
		accrued_interest_in_sale: DF.Currency
		amended_from: DF.Link | None
		cash_account: DF.Link | None
		charges: DF.Currency
		company: DF.Link
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		cost_of_units_sold: DF.Currency
		currency: DF.Link
		gross_amount: DF.Currency
		instrument_class: DF.Data | None
		interest_amount: DF.Currency
		investment: DF.Link
		naming_series: DF.Literal["INV-TXN-.YYYY.-"]
		net_amount: DF.Currency
		penalty_applied: DF.Currency
		posting_date: DF.Date
		rate: DF.Currency
		realised_gain_loss: DF.Currency
		reference_date: DF.Date | None
		reference_no: DF.Data | None
		remarks: DF.SmallText | None
		tax_withheld: DF.Currency
		transaction_type: DF.Literal[
			"",
			"Opening",
			"Purchase",
			"Sale",
			"Redemption",
			"Withdrawal",
			"Maturity",
			"Interest Receipt",
			"Dividend",
			"Charges",
		]
		units: DF.Float
	# end: auto-generated types

	def validate(self):
		self.lock_investment()
		self.validate_investment()
		set_conversion_rate(self)
		self.validate_transaction_type()
		self.validate_has_investment()
		self.validate_dates()
		self.set_missing_values()
		self.validate_amounts()
		self.set_net_amount()
		self.validate_cash_account()
		self.validate_approved_amount()
		self.validate_available_balance()
		self.validate_after_accrued_interest()
		self.validate_interest_accrued()
		self.validate_accrued_interest_in_sale()

	def before_submit(self):
		self.validate_no_later_exits()
		self.validate_no_later_revaluation()
		self.validate_interest_accrued_before_exit()
		self.set_cost_and_realised_gain_loss()

	def on_submit(self):
		self.make_gl_entries()
		self.update_investment()
		self.update_interest_schedule()

	def before_cancel(self):
		super().before_cancel()
		self.validate_purchase_not_consumed()
		self.validate_no_later_exits()
		self.validate_no_later_revaluation()
		self.validate_after_accrued_interest()
		self.validate_accrued_interest_not_received()
		self.validate_proceeds_not_renewed()

	def on_cancel(self):
		super().on_cancel()
		self.ignore_linked_doctypes = ("GL Entry",)
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
		self.update_investment()
		self.update_interest_schedule()

	def get_investment(self):
		if not getattr(self, "_investment", None):
			self._investment = frappe.get_doc("Investment", self.investment)

		return self._investment

	def lock_investment(self):
		"""On submit, lock the investment so vouchers submitted together check against each other.

		A draft save posts nothing, so it does not lock.
		"""
		if self.docstatus == 1:
			lock_investment(self.investment)

	def validate_investment(self):
		if self.get_investment().docstatus != 1:
			frappe.throw(
				_("Investment {0} must be approved (submitted) before posting transactions").format(
					frappe.bold(self.investment)
				)
			)

	def validate_transaction_type(self):
		allowed = ALLOWED_INSTRUMENTS.get(self.transaction_type)
		if allowed and self.instrument_class not in allowed:
			frappe.throw(
				_("Transaction Type {0} is not allowed for {1} instruments").format(
					frappe.bold(self.transaction_type), frappe.bold(self.instrument_class)
				)
			)

	def validate_has_investment(self):
		"""Income can only be earned once money is actually invested in the investment."""
		if self.transaction_type not in INCOME_TYPES:
			return

		if not frappe.db.exists(
			"Investment Transaction",
			{
				"investment": self.investment,
				"transaction_type": ("in", PURCHASE_TYPES),
				"docstatus": 1,
			},
		):
			frappe.throw(
				_("Please record a Purchase or Opening for Investment {0} first").format(
					frappe.bold(self.investment)
				)
			)

	def validate_dates(self):
		if getdate(self.posting_date) < getdate(self.get_investment().purchase_date):
			frappe.throw(_("Posting Date cannot be before the investment's Purchase Date"))

	def set_missing_values(self):
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

		if self.is_unit_movement():
			self.gross_amount = flt(flt(self.units) * flt(self.rate), self.precision("gross_amount"))

		self.clear_hidden_amounts()

	def clear_hidden_amounts(self):
		"""The form hides these for other types but keeps their value, which would still be posted."""
		if self.transaction_type not in (*EXIT_TYPES, *INCOME_TYPES):
			self.tax_withheld = 0

		if self.transaction_type != "Purchase":
			self.accrued_interest_in_purchase = 0

		if not (self.instrument_class == "Bond" and self.transaction_type in ("Sale", "Redemption")):
			self.accrued_interest_in_sale = 0

		if self.transaction_type != "Interest Receipt":
			self.interest_amount = 0

		if not (self.instrument_class == "Deposit" and self.transaction_type == "Withdrawal"):
			self.penalty_applied = 0

	def is_unit_movement(self):
		return self.instrument_class in UNIT_CLASSES and self.transaction_type in (
			*PURCHASE_TYPES,
			*EXIT_TYPES,
		)

	def validate_amounts(self):
		for fieldname in AMOUNT_FIELDS:
			if flt(self.get(fieldname)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(fieldname))))

		if self.is_unit_movement() and (flt(self.units) <= 0 or flt(self.rate) <= 0):
			frappe.throw(_("Units and Rate must be greater than zero"))

		if flt(self.accrued_interest_in_purchase) > flt(self.gross_amount):
			frappe.throw(_("Accrued Interest in Purchase cannot be more than Gross Amount"))

		if flt(self.accrued_interest_in_sale) > flt(self.gross_amount):
			frappe.throw(_("Accrued Interest in Sale cannot be more than Gross Amount"))

	def set_net_amount(self):
		self.net_amount = flt(self.get_net_amount(), self.precision("net_amount"))

		if self.net_amount <= 0:
			frappe.throw(_("Net Amount must be greater than zero"))

	def get_net_amount(self):
		"""Cash that actually moves in (or out of) the bank; for non-cash types, the amount booked."""
		if self.transaction_type == "Purchase":
			return flt(self.gross_amount) + flt(self.charges)

		if self.transaction_type == "Opening":
			return flt(self.gross_amount)

		if self.transaction_type == "Charges":
			return flt(self.charges)

		deductions = flt(self.charges) + flt(self.tax_withheld) + flt(self.penalty_applied)
		return self.get_inflow_amount() - deductions

	def get_inflow_amount(self):
		if self.transaction_type == "Interest Receipt":
			return flt(self.interest_amount)

		return flt(self.gross_amount)

	def validate_cash_account(self):
		if self.transaction_type in NON_CASH_TYPES:
			self.cash_account = None
			return

		if not self.cash_account:
			frappe.throw(_("Cash / Bank Account is required"))

		validate_company_links(self, ("cash_account",))

	def validate_approved_amount(self):
		if self.transaction_type not in PURCHASE_TYPES:
			return

		approved_amount = flt(self.get_investment().approved_amount)
		# interest bought with a purchase is not part of the investment's cost, so it does not count
		other_purchases = sum(p.amount for p in get_purchases(self.investment) if p.name != self.name)
		total_purchased = flt(other_purchases + get_investment_amount(self), self.precision("gross_amount"))

		if total_purchased > approved_amount:
			frappe.throw(
				_("Total purchases {0} would exceed the Approved Amount {1} of Investment {2}").format(
					frappe.bold(total_purchased),
					frappe.bold(approved_amount),
					frappe.bold(self.investment),
				)
			)

	def get_submitted_total(self, fieldname, transaction_types, upto=None):
		"""Sum of a field over the other submitted transactions of this investment, optionally up to a date."""
		return get_submitted_sum(self.doctype, fieldname, self.investment, upto, self.name, transaction_types)

	def validate_available_balance(self):
		if self.transaction_type not in EXIT_TYPES:
			return

		if self.instrument_class in UNIT_CLASSES:
			self.validate_balance("units", _("Units"), flt(self.units))
		else:
			self.validate_balance("amount", _("Principal"), flt(self.gross_amount))

	def validate_balance(self, purchase_field, label, required):
		# on submit the investment is locked, and rows are read with locks too, so the second of two
		# exits submitted together sees the first one once it commits
		lock = self.docstatus == 1
		# only what was bought by the posting date can leave, so an exit never takes a later purchase's cost
		purchased = sum(
			flt(p.get(purchase_field))
			for p in get_purchases(self.investment, for_update=lock)
			if getdate(p.posting_date) <= getdate(self.posting_date)
		)
		exit_field = "units" if purchase_field == "units" else "gross_amount"
		# rows are locked and summed here, as PostgreSQL cannot lock rows inside SUM()
		exits = frappe.db.get_values(
			self.doctype,
			{
				"investment": self.investment,
				"docstatus": 1,
				"transaction_type": ("in", EXIT_TYPES),
				"name": ("!=", self.name or ""),
			},
			exit_field,
			for_update=lock,
		)
		available = purchased - sum(flt(value) for (value,) in exits)

		if required > flt(available, self.precision(exit_field)):
			frappe.throw(
				_("{0} available in Investment {1} is {2}, cannot exit {3}").format(
					label, frappe.bold(self.investment), frappe.bold(available), frappe.bold(required)
				)
			)

	def is_principal_movement(self):
		return self.instrument_class in INTEREST_CLASSES and self.transaction_type in (
			*PURCHASE_TYPES,
			*EXIT_TYPES,
		)

	def validate_after_accrued_interest(self):
		"""Posted interest assumed the old principal, so principal cannot change on or before it."""
		if not self.is_principal_movement():
			return

		accrued_upto = self.get_investment().accrued_upto
		if accrued_upto and getdate(self.posting_date) <= getdate(accrued_upto):
			frappe.throw(
				_(
					"Interest is already accrued up to {0}. Cancel the Investment Interest Accruals from {1} onwards first."
				).format(
					frappe.bold(frappe.format_value(accrued_upto, "Date")),
					frappe.bold(frappe.format_value(self.posting_date, "Date")),
				)
			)

	def validate_interest_accrued(self):
		"""Interest can only be received once it has been accrued, so Accrued Interest never goes negative."""
		if self.transaction_type != "Interest Receipt":
			return

		available = get_unreceived_interest(
			self.investment, self.posting_date, self.name, for_update=self.docstatus == 1
		)
		if flt(self.interest_amount) > flt(available, self.precision("interest_amount")):
			frappe.throw(
				_(
					"Interest Amount {0} is more than the {3} accrued up to {2} and not yet received for Investment {1}. Please make an Investment Interest Accrual up to {2} first."
				).format(
					frappe.bold(frappe.format_value(self.interest_amount, currency=self.currency)),
					frappe.bold(self.investment),
					frappe.bold(frappe.format_value(self.posting_date, "Date")),
					frappe.bold(frappe.format_value(max(available, 0), currency=self.currency)),
				),
				title=_("Interest Not Accrued"),
			)

	def validate_proceeds_not_renewed(self):
		"""Renewals reinvest money this investment paid out, so a payment they use cannot be taken back."""
		if self.transaction_type in EXIT_TYPES:
			fieldname, transaction_types = "principal_renewed", EXIT_TYPES
		elif self.transaction_type == "Interest Receipt":
			fieldname, transaction_types = "interest_renewed", ("Interest Receipt",)
		else:
			return

		renewals = frappe.get_all(
			"Investment Renewal",
			filters={"original_investment": self.investment, "docstatus": 1, fieldname: (">", 0)},
			fields=["name", "renewal_date", fieldname],
			order_by="renewal_date asc, creation asc",
		)
		renewed = 0
		for renewal in renewals:
			# a renewal can only use money paid out by its date, as checked when it was submitted
			renewed += flt(renewal.get(fieldname))
			paid_out = get_submitted_sum(
				self.doctype,
				"net_amount",
				self.investment,
				renewal.renewal_date,
				self.name,
				transaction_types,
			)
			if renewed > flt(paid_out, self.precision("net_amount")):
				frappe.throw(
					_(
						"Investment Renewal {0} reinvests money paid out by this transaction. Please cancel the renewal (and its new investment) first."
					).format(frappe.get_desk_link("Investment Renewal", renewal.name))
				)

	def validate_accrued_interest_in_sale(self):
		"""The buyer pays interest the books already accrued, so a sale cannot collect more than that."""
		if not flt(self.accrued_interest_in_sale):
			return

		available = get_unreceived_interest(
			self.investment, self.posting_date, self.name, for_update=self.docstatus == 1
		)
		if flt(self.accrued_interest_in_sale) > flt(available, self.precision("accrued_interest_in_sale")):
			frappe.throw(
				_(
					"Accrued Interest in Sale {0} is more than the {1} accrued and not yet received for Investment {2}. Please make an Investment Interest Accrual first."
				).format(
					frappe.bold(frappe.format_value(self.accrued_interest_in_sale, currency=self.currency)),
					frappe.bold(frappe.format_value(max(available, 0), currency=self.currency)),
					frappe.bold(self.investment),
				),
				title=_("Interest Not Accrued"),
			)

	def validate_accrued_interest_not_received(self):
		"""Interest bought with a purchase that a receipt has already collected cannot be taken back."""
		if flt(self.accrued_interest_in_purchase):
			validate_interest_not_received(
				self,
				_(
					"Interest bought with this purchase has already been received. Please cancel the Interest Receipt transactions of Investment {0} first."
				),
			)

	def validate_interest_accrued_before_exit(self):
		"""Interest must be accrued up to the day before an exit, so it exits at its accrued book value."""
		if not (self.is_principal_movement() and self.transaction_type in EXIT_TYPES):
			return

		schedule = get_schedule(self.investment)
		if not schedule:
			return

		# interest stops at maturity, so a late payment needs accruals only up to the schedule's last day
		accrue_upto = min(getdate(add_days(self.posting_date, -1)), getdate(schedule[-1].period_to))
		if accrue_upto < getdate(schedule[0].period_from):
			return

		accrued_upto = self.get_investment().accrued_upto
		if not accrued_upto or getdate(accrued_upto) < getdate(accrue_upto):
			frappe.throw(
				_("Please make an Investment Interest Accrual for Investment {0} up to {1} first").format(
					frappe.bold(self.investment), frappe.bold(frappe.format_value(accrue_upto, "Date"))
				),
				title=_("Interest Not Accrued"),
			)

	def update_interest_schedule(self):
		# interest paid out of a cumulative deposit no longer compounds
		if self.is_principal_movement() or self.transaction_type == "Interest Receipt":
			update_interest_schedule(self.investment)

	def set_cost_and_realised_gain_loss(self):
		if self.transaction_type not in EXIT_TYPES:
			return

		units_already_sold = self.get_submitted_total("units", EXIT_TYPES)
		if self.instrument_class == "Bond":
			calculator = InterestCalculator(self.get_investment())
			cost = calculator.get_carrying_cost(units_already_sold, flt(self.units), self.posting_date)
		elif self.instrument_class in UNIT_CLASSES:
			cost = get_fifo_cost(get_purchases(self.investment), units_already_sold, flt(self.units))
		else:
			cost = flt(self.gross_amount)

		if self.instrument_class in UNIT_CLASSES and self.sells_last_units(units_already_sold):
			# the last units take all the cost left, so rounding on earlier exits leaves no balance behind
			cost = self.get_investment().get_book_value_in_investment_currency(exclude=self.name)

		self.cost_of_units_sold = flt(cost, self.precision("cost_of_units_sold"))
		# accrued interest the buyer paid with the price is interest, not gain
		self.realised_gain_loss = flt(
			flt(self.gross_amount) - flt(self.accrued_interest_in_sale) - self.cost_of_units_sold,
			self.precision("realised_gain_loss"),
		)

	def sells_last_units(self, units_already_sold):
		units_bought = self.get_submitted_total("units", PURCHASE_TYPES)
		return flt(units_bought - units_already_sold - flt(self.units), self.precision("units")) <= 0

	def validate_purchase_not_consumed(self):
		if self.transaction_type not in PURCHASE_TYPES:
			return

		purchase_field, exit_field = (
			("units", "units") if self.instrument_class in UNIT_CLASSES else ("amount", "gross_amount")
		)
		other_purchases = [p for p in get_purchases(self.investment) if p.name != self.name]
		remaining = sum(flt(p.get(purchase_field)) for p in other_purchases)

		if flt(remaining - self.get_submitted_total(exit_field, EXIT_TYPES), self.precision(exit_field)) < 0:
			frappe.throw(_("Cannot cancel this purchase because it has already been sold or withdrawn"))

	def validate_no_later_exits(self):
		"""Exits are costed from the oldest units left after the exits before them,
		so a purchase or exit cannot change once later exits exist."""
		if not self.is_unit_movement():
			return

		if self.has_later_exits():
			frappe.throw(
				_(
					"Investment {0} has exits on or after {1} that were costed without this change. Please cancel them first."
				).format(
					frappe.bold(self.investment), frappe.bold(frappe.format_value(self.posting_date, "Date"))
				)
			)

	def validate_no_later_revaluation(self):
		"""A revaluation posts the change from the fair value left after earlier exits,
		so an exit cannot be added or cancelled before it."""
		if self.transaction_type not in EXIT_TYPES or not self.get_investment().posts_fair_value():
			return

		revaluation = frappe.qb.DocType("Investment Revaluation")
		row = frappe.qb.DocType("Investment Revaluation Detail")
		later = (
			frappe.qb.from_(row)
			.join(revaluation)
			.on(row.parent == revaluation.name)
			.select(revaluation.name)
			.where(row.investment == self.investment)
			.where(revaluation.docstatus == 1)
			.where(
				(revaluation.revaluation_date > self.posting_date)
				| (
					(revaluation.revaluation_date == self.posting_date)
					& (revaluation.creation > self.creation)
				)
			)
			.limit(1)
		).run()
		if later:
			frappe.throw(
				_(
					"Investment Revaluation {0} of Investment {1} was made after {2}. Please cancel it first."
				).format(
					frappe.get_desk_link("Investment Revaluation", later[0][0]),
					frappe.bold(self.investment),
					frappe.bold(frappe.format_value(self.posting_date, "Date")),
				)
			)

	def has_later_exits(self):
		transaction = frappe.qb.DocType(self.doctype)
		if self.transaction_type in PURCHASE_TYPES:
			# an exit on the purchase date may have taken this purchase's cost
			later = transaction.posting_date >= self.posting_date
		else:
			# exits are costed in (posting date, creation) order, as in get_exit_transactions
			later = (transaction.posting_date > self.posting_date) | (
				(transaction.posting_date == self.posting_date) & (transaction.creation > self.creation)
			)

		return bool(
			frappe.qb.from_(transaction)
			.select(transaction.name)
			.where(transaction.investment == self.investment)
			.where(transaction.docstatus == 1)
			.where(transaction.transaction_type.isin(EXIT_TYPES))
			.where(transaction.name != self.name)
			.where(later)
			.limit(1)
			.run()
		)

	def update_investment(self):
		self.get_investment().update_position()

	def make_gl_entries(self):
		make_gl_entries(self.get_gl_entries())

	def get_gl_entries(self):
		builders = {
			"Opening": self.get_opening_gl_entries,
			"Purchase": self.get_purchase_gl_entries,
			"Interest Receipt": self.get_income_receipt_gl_entries,
			"Dividend": self.get_income_receipt_gl_entries,
			"Charges": self.get_charges_gl_entries,
		}
		builder = builders.get(self.transaction_type, self.get_exit_gl_entries)
		settlements = self.get_settlements()

		gl_entries = []
		for account, debit, credit in builder():
			if not (debit or credit):
				continue

			if credit and account in settlements:
				gl_entries.append(
					get_gl_entry(self, account, debit, credit, base_credit=settlements[account])
				)
			else:
				gl_entries.append(get_gl_entry(self, account, debit, credit))

		gl_entries += self.get_fair_value_release_entries()
		if settlements:
			gl_entries += self.get_exchange_gain_loss_entries(gl_entries)

		return gl_entries

	def get_fair_value_release_entries(self):
		"""An exit takes its share of the fair value gain off the books, so the gain is counted once, as
		realised. For FVOCI this moves it from the equity reserve into profit and loss."""
		investment = self.get_investment()
		if self.transaction_type not in EXIT_TYPES or not investment.posts_fair_value():
			return []

		fair_value_account = investment.fair_value_adjustment_account
		balance = investment.get_ledger_balance(fair_value_account, self.posting_date)
		# this exit is already submitted, so the units held include it
		units_left = get_units_held(self.investment, self.posting_date)
		units_before = units_left + flt(self.units)
		share = 1 if units_left <= 0 or not units_before else flt(self.units) / units_before
		release = flt(balance * share, self.precision("net_amount"))
		if not release:
			return []

		# amounts are in company currency; the investment currency amount converts back to exactly them
		amount = release / flt(self.conversion_rate)
		gain, loss = max(release, 0), max(-release, 0)
		return [
			get_gl_entry(self, fair_value_account, max(-amount, 0), max(amount, 0), loss, gain),
			get_gl_entry(
				self, investment.get_fair_value_gain_account(), max(amount, 0), max(-amount, 0), gain, loss
			),
		]

	def get_opening_gl_entries(self):
		opening_account = get_temporary_opening_account(self.company)
		return [
			(self.get_investment_account("investment_account"), self.gross_amount, 0),
			(opening_account, 0, self.gross_amount),
		]

	def get_purchase_gl_entries(self):
		entries = [
			(self.get_investment_account("investment_account"), get_investment_amount(self), 0),
			(self.cash_account, 0, self.net_amount),
		]

		if flt(self.accrued_interest_in_purchase):
			entries.append(
				(
					self.get_investment_account("accrued_interest_account"),
					self.accrued_interest_in_purchase,
					0,
				)
			)

		return entries + self.get_charges_and_tax_entries()

	def get_income_receipt_gl_entries(self):
		if self.transaction_type == "Dividend":
			income_account = self.get_investment_account("dividend_income_account")
		else:
			income_account = self.get_investment_account("accrued_interest_account")

		return [
			(self.cash_account, self.net_amount, 0),
			(income_account, 0, self.get_inflow_amount()),
			*self.get_charges_and_tax_entries(),
		]

	def get_charges_gl_entries(self):
		return [
			(self.get_investment_account("charges_account"), self.charges, 0),
			(self.cash_account, 0, self.charges),
		]

	def get_exit_gl_entries(self):
		entries = [
			(self.cash_account, self.net_amount, 0),
			(self.get_investment_account("investment_account"), 0, self.cost_of_units_sold),
			*self.get_charges_and_tax_entries(),
		]

		if flt(self.accrued_interest_in_sale):
			entries.append(
				(self.get_investment_account("accrued_interest_account"), 0, self.accrued_interest_in_sale)
			)

		if flt(self.realised_gain_loss):
			gain_loss_account = self.get_investment_account("realised_gain_loss_account")
			entries.append(
				(gain_loss_account, max(-self.realised_gain_loss, 0), max(self.realised_gain_loss, 0))
			)

		return entries

	def get_charges_and_tax_entries(self):
		entries = []
		charges = flt(self.charges) + flt(self.penalty_applied)

		if charges:
			entries.append((self.get_investment_account("charges_account"), charges, 0))

		if flt(self.tax_withheld):
			entries.append(
				(self.get_investment_account("tax_withheld_receivable_account"), self.tax_withheld, 0)
			)

		return entries

	def get_investment_account(self, fieldname):
		return self.get_investment().get_account(fieldname)

	def get_settlements(self):
		"""Company currency value each settled account leaves at, at its booked rates, so a rate change
		shows as exchange gain."""
		if self.currency == erpnext.get_company_currency(self.company):
			return {}

		investment = self.get_investment()
		settled = []
		if self.transaction_type in EXIT_TYPES:
			held = investment.get_book_value_in_investment_currency(self.posting_date, self.name)
			settled.append((investment.get_account("investment_account"), flt(self.cost_of_units_sold), held))

		interest = flt(self.interest_amount) + flt(self.accrued_interest_in_sale)
		if interest:
			# collections dated later are left out, as the ledger balance below is also up to this date
			held = get_accrued_interest(self.investment, self.posting_date) - get_interest_received(
				self.investment, self.name, self.posting_date
			)
			settled.append((investment.get_account("accrued_interest_account"), interest, held))

		settlements = {}
		for account, amount, held in settled:
			held = flt(held, self.precision("net_amount"))
			if held <= 0:
				continue

			# everything still held leaves at its full book value, so the account ends at exactly zero
			base_held = investment.get_ledger_balance(account, self.posting_date)
			settlements[account] = base_held if amount >= held else base_held * amount / held

		return settlements

	def get_exchange_gain_loss_entries(self, gl_entries):
		"""Cash moves at today's rate, the settled amount at its booked rate; the gap is exchange gain/loss."""
		difference = flt(
			sum(flt(gl_entry.debit) - flt(gl_entry.credit) for gl_entry in gl_entries),
			self.precision("net_amount"),
		)
		if not difference:
			return []

		account = frappe.get_cached_value("Company", self.company, "exchange_gain_loss_account")
		if not account:
			frappe.throw(
				_("Please set the Exchange Gain / Loss Account in Company {0}").format(
					frappe.bold(self.company)
				)
			)

		return [
			self.get_gl_dict(
				{
					"account": account,
					"debit": max(-difference, 0),
					"credit": max(difference, 0),
					"against": self.investment,
					"cost_center": self.cost_center,
				},
				item=self,
			)
		]


def get_gl_entry(doc, account, debit, credit, base_debit=None, base_credit=None):
	"""GL Entry converted at the Exchange Rate; `base_debit` / `base_credit` override the company
	currency amounts."""
	precision = doc.precision("interest_amount")
	args = {
		"account": account,
		"debit": flt(flt(debit) * flt(doc.conversion_rate), precision),
		"credit": flt(flt(credit) * flt(doc.conversion_rate), precision),
		"against": doc.investment,
		"cost_center": doc.cost_center,
		"is_opening": "Yes" if doc.get("transaction_type") == "Opening" else "No",
	}

	is_foreign_account = get_account_currency(account) != erpnext.get_company_currency(doc.company)
	for side, base_amount, amount in (("debit", base_debit, debit), ("credit", base_credit, credit)):
		if base_amount is not None:
			args[side] = flt(base_amount, precision)
			if is_foreign_account:
				args[f"{side}_in_account_currency"] = flt(amount, precision)

	return doc.get_gl_dict(args, item=doc)


def set_conversion_rate(doc):
	"""A foreign-currency investment needs an Exchange Rate, as its amounts are posted times that rate."""
	company_currency = erpnext.get_company_currency(doc.company)
	if doc.currency == company_currency:
		doc.conversion_rate = 1
		return

	if flt(doc.conversion_rate) <= 0:
		frappe.throw(
			_("Please enter the Exchange Rate from {0} to {1}").format(
				frappe.bold(doc.currency), frappe.bold(company_currency)
			),
			title=_("Exchange Rate Missing"),
		)


def get_accrued_interest(investment, upto=None, exclude=None, for_update=False):
	"""Interest accrued by Investment Interest Accruals, plus interest bought with bond purchases."""
	accrued = get_submitted_sum(
		"Investment Interest Accrual", "interest_amount", investment, upto, exclude, for_update=for_update
	)
	bought = get_submitted_sum(
		"Investment Transaction",
		"accrued_interest_in_purchase",
		investment,
		upto,
		exclude,
		PURCHASE_TYPES,
		for_update=for_update,
	)

	return accrued + bought


def get_unreceived_interest(investment, upto=None, exclude_receipt=None, for_update=False):
	"""Interest accrued up to a date and not yet received."""
	return get_accrued_interest(investment, upto, for_update=for_update) - get_interest_received(
		investment, exclude_receipt, for_update=for_update
	)


def validate_interest_not_received(doc, message):
	"""Block cancelling `doc` once a receipt collected its interest; `message` is whole for translators."""
	received = get_interest_received(doc.investment)
	accrued = get_accrued_interest(doc.investment, exclude=doc.name)
	if received > flt(accrued, doc.precision("interest_amount")):
		frappe.throw(message.format(frappe.bold(doc.investment)))


def get_interest_received(investment, exclude=None, upto=None, for_update=False):
	"""Accrued interest collected: by interest receipts, and from buyers with bond sales."""
	received = get_submitted_sum(
		"Investment Transaction",
		"interest_amount",
		investment,
		upto,
		exclude,
		transaction_types=("Interest Receipt",),
		for_update=for_update,
	)
	sold = get_submitted_sum(
		"Investment Transaction",
		"accrued_interest_in_sale",
		investment,
		upto,
		exclude,
		transaction_types=EXIT_TYPES,
		for_update=for_update,
	)
	return received + sold


def get_submitted_sum(
	doctype,
	fieldname,
	investment,
	upto=None,
	exclude=None,
	transaction_types=None,
	link_field="investment",
	for_update=False,
):
	"""Sum of a field over the submitted documents of an investment, optionally up to a posting date.

	With `for_update`, the rows are locked, so the sum includes rows another submit committed meanwhile.
	"""
	table = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(table)
		.where(table[link_field] == investment)
		.where(table.docstatus == 1)
		.where(table.name != (exclude or ""))
	)
	if transaction_types:
		query = query.where(table.transaction_type.isin(transaction_types))

	if upto:
		query = query.where(table.posting_date <= upto)

	if for_update:
		# PostgreSQL cannot lock rows inside SUM(), so the rows are locked and summed here
		return sum(flt(value) for (value,) in query.select(table[fieldname]).for_update().run())

	return flt(query.select(Sum(table[fieldname])).run()[0][0])


def lock_investment(investment):
	"""Lock the investment until commit, so vouchers submitted together check against each other.

	Once locked, reads still see the database as this transaction first saw it. Every posting
	updates the investment, so if it changed meanwhile, ask for a retry rather than use old balances.
	"""
	first_seen = frappe.db.get_value("Investment", investment, "modified")
	if frappe.db.get_value("Investment", investment, "modified", for_update=True) != first_seen:
		frappe.throw(
			_("Investment {0} was just updated by another entry. Please try again.").format(
				frappe.bold(investment)
			),
			exc=frappe.TimestampMismatchError,
			title=_("Please Retry"),
		)


def get_units_held(investment, upto=None):
	"""Units bought minus units exited, optionally up to a date."""
	bought = get_submitted_sum(
		"Investment Transaction", "units", investment, upto, transaction_types=PURCHASE_TYPES
	)
	exited = get_submitted_sum(
		"Investment Transaction", "units", investment, upto, transaction_types=EXIT_TYPES
	)

	return bought - exited


def get_exit_transactions(investment):
	"""Submitted exits of an investment, oldest first."""
	return frappe.get_all(
		"Investment Transaction",
		filters={"investment": investment, "docstatus": 1, "transaction_type": ("in", EXIT_TYPES)},
		fields=["transaction_type", "posting_date", "units", "gross_amount"],
		order_by="posting_date asc, creation asc",
	)


def get_purchases(investment, for_update=False):
	"""Submitted purchases of an investment in FIFO order (oldest first), with units and investment cost."""
	purchases = frappe.db.get_values(
		"Investment Transaction",
		{
			"investment": investment,
			"transaction_type": ("in", PURCHASE_TYPES),
			"docstatus": 1,
		},
		[
			"name",
			"transaction_type",
			"instrument_class",
			"posting_date",
			"units",
			"gross_amount",
			"accrued_interest_in_purchase",
		],
		as_dict=True,
		order_by="posting_date asc, creation asc",
		for_update=for_update,
	)

	for purchase in purchases:
		purchase.purchase_date = purchase.posting_date
		purchase.units = flt(purchase.units) if purchase.instrument_class in UNIT_CLASSES else 0
		purchase.amount = get_investment_amount(purchase)

	return purchases


def get_investment_amount(purchase):
	"""Part of a purchase that is the cost of the investment itself (excludes bought-in interest)."""
	if purchase.transaction_type == "Opening":
		return flt(purchase.gross_amount)

	return flt(purchase.gross_amount) - flt(purchase.accrued_interest_in_purchase)


def get_fifo_cost(purchases, units_already_sold, units_to_sell):
	"""Cost of `units_to_sell`, taken from the oldest purchases after skipping units sold earlier."""
	lots = take_fifo(purchases, lambda purchase: flt(purchase.units), units_already_sold, units_to_sell)
	return sum(taken * flt(purchase.amount) / flt(purchase.units) for purchase, taken in lots)
