# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

import erpnext
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.setup.utils import get_exchange_rate
from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
	get_gl_entry,
	set_conversion_rate,
	validate_interest_not_received,
)
from erpnext.treasury.interest import INTEREST_CLASSES, InterestCalculator
from erpnext.treasury.interest_schedule import (
	get_estimated_interest,
	get_rounded_amortisation,
	get_schedule,
	update_interest_schedule,
)


class InvestmentInterestAccrual(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amortisation_amount: DF.Currency
		company: DF.Link
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		currency: DF.Link
		estimated_interest: DF.Currency
		from_date: DF.Date
		instrument_class: DF.Data | None
		interest_amount: DF.Currency
		investment: DF.Link
		naming_series: DF.Literal["INV-ACCR-.YYYY.-"]
		posting_date: DF.Date
		remarks: DF.SmallText | None
		to_date: DF.Date
		variance: DF.Currency
	# end: auto-generated types

	"""Interest earned on a Deposit or Bond over a date range, as reported by the bank / issuer."""

	def validate(self):
		self.validate_investment()
		set_conversion_rate(self)
		self.set_missing_values()
		self.validate_dates()
		self.validate_accrual_period()
		self.set_estimated_interest()
		self.set_amortisation()
		self.validate_amounts()

	def on_submit(self):
		make_gl_entries(self.get_gl_entries())
		self.update_investment()

	def before_cancel(self):
		super().before_cancel()
		self.validate_latest_accrual()
		validate_interest_not_received(
			self,
			_(
				"Interest accrued by this entry has already been received. Please cancel the Interest Receipt transactions of Investment {0} first."
			),
		)

	def on_cancel(self):
		super().on_cancel()
		self.ignore_linked_doctypes = ("GL Entry",)
		make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
		self.update_investment()

	def get_investment(self):
		if not getattr(self, "_investment", None):
			self._investment = frappe.get_doc("Investment", self.investment)

		return self._investment

	def get_schedule(self):
		if getattr(self, "_schedule", None) is None:
			self._schedule = get_schedule(self.investment)

		return self._schedule

	def validate_investment(self):
		investment = self.get_investment()
		if investment.docstatus != 1:
			frappe.throw(
				_("Investment {0} must be approved (submitted) before accruing interest").format(
					frappe.bold(self.investment)
				)
			)

		if investment.instrument_class not in INTEREST_CLASSES:
			frappe.throw(_("Interest can only be accrued for Deposit and Bond investments"))

		if not self.get_schedule():
			frappe.throw(
				_("Please record a Purchase or Opening for Investment {0} first").format(
					frappe.bold(self.investment)
				)
			)

	def set_missing_values(self):
		next_accrual = get_next_accrual(self.investment, self.get_schedule())
		if next_accrual and not self.from_date:
			self.from_date = next_accrual.from_date

		if next_accrual and not self.to_date:
			self.to_date = next_accrual.to_date

		if not self.cost_center:
			self.cost_center = self.get_investment().cost_center or frappe.get_cached_value(
				"Company", self.company, "cost_center"
			)

	def validate_dates(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date cannot be before From Date"))

		# interest of a period is only earned by its last day, so it cannot be booked earlier
		if getdate(self.posting_date) < getdate(self.to_date):
			frappe.throw(_("Posting Date cannot be before To Date"))

	def validate_accrual_period(self):
		"""Accruals follow each other without gaps or overlaps, from the first purchase until maturity
		or full exit, so every day's interest is booked exactly once."""
		schedule_end = getdate(self.get_schedule()[-1].period_to)
		self.validate_from_date(schedule_end)

		if getdate(self.to_date) > schedule_end:
			frappe.throw(
				_(
					"To Date cannot be after {0}, the last day interest is earned (maturity or full exit)"
				).format(frappe.bold(frappe.format_value(schedule_end, "Date"))),
				title=_("Invalid Accrual Period"),
			)

	def validate_from_date(self, schedule_end):
		next_date = get_next_accrual_date(self.investment, self.get_schedule())
		if next_date > schedule_end:
			frappe.throw(
				_("Interest of Investment {0} is already accrued up to its last day, {1}").format(
					frappe.bold(self.investment), frappe.bold(frappe.format_value(schedule_end, "Date"))
				),
				title=_("Invalid Accrual Period"),
			)

		if getdate(self.from_date) != next_date:
			frappe.throw(
				_("From Date must be {0}: interest of Investment {1} is accrued up to the day before").format(
					frappe.bold(frappe.format_value(next_date, "Date")), frappe.bold(self.investment)
				),
				title=_("Invalid Accrual Period"),
			)

	def set_estimated_interest(self):
		self.estimated_interest = get_estimated_interest(self.investment, self.from_date, self.to_date)
		self.variance = flt(flt(self.interest_amount) - self.estimated_interest, self.precision("variance"))

	def set_amortisation(self):
		"""Bond amortisation is an accounting figure, not a bank one, so it is always calculated."""
		if self.instrument_class != "Bond":
			self.amortisation_amount = 0
			return

		calculator = InterestCalculator(self.get_investment())
		self.amortisation_amount = get_rounded_amortisation(
			calculator, getdate(self.from_date), add_days(self.to_date, 1)
		)

	def validate_amounts(self):
		if flt(self.interest_amount) < 0:
			frappe.throw(_("Interest Amount cannot be negative"))

		# a zero-coupon bond accrues no interest, only amortisation
		if not flt(self.interest_amount) and not flt(self.amortisation_amount):
			frappe.throw(_("Interest Amount must be greater than zero"))

	def validate_latest_accrual(self):
		if frappe.db.exists(
			self.doctype,
			{"investment": self.investment, "docstatus": 1, "from_date": (">", self.to_date)},
		):
			frappe.throw(
				_("Please cancel the later Interest Accruals of Investment {0} first").format(
					frappe.bold(self.investment)
				)
			)

	def update_investment(self):
		update_interest_schedule(self.investment)
		self.get_investment().update_position()

	def get_gl_entries(self):
		"""Interest accrued, plus bond discount earned (positive) or premium written off (negative)."""
		amortisation = flt(self.amortisation_amount)
		income = flt(self.interest_amount) + amortisation
		entries = [
			("accrued_interest_account", self.interest_amount, 0),
			("investment_account", max(amortisation, 0), max(-amortisation, 0)),
			("interest_income_account", max(-income, 0), max(income, 0)),
		]

		return [
			get_gl_entry(self, self.get_investment().get_account(fieldname), debit, credit)
			for fieldname, debit, credit in entries
			if debit or credit
		]


def get_next_accrual(investment, schedule):
	"""Dates and estimated interest of the next accrual: the rest of the schedule period it starts in."""
	from_date = get_next_accrual_date(investment, schedule)
	period = (
		next((row for row in schedule if getdate(row.period_to) >= from_date), None) if from_date else None
	)
	if not period:
		return None

	return frappe._dict(
		from_date=from_date,
		to_date=getdate(period.period_to),
		posting_date=getdate(period.period_to),
		interest_amount=get_estimated_interest(investment, from_date, period.period_to),
	)


def get_next_accrual_date(investment, schedule):
	"""The day after interest is accrued up to, or the first day of the schedule."""
	accrued_upto = frappe.db.get_value("Investment", investment, "accrued_upto")
	if accrued_upto:
		return getdate(add_days(accrued_upto, 1))

	return getdate(schedule[0].period_from) if schedule else None


@frappe.whitelist()
def get_accrual_defaults(investment: str) -> dict | None:
	"""From / To Date, Posting Date and the estimate as Interest Amount, to prefill a new accrual."""
	frappe.get_doc("Investment", investment).check_permission("read")

	return get_next_accrual(investment, get_schedule(investment))


def make_draft_accruals():
	"""Daily job: once a schedule period has ended, make a draft accrual for it prefilled with the
	estimate, so the user only corrects the amount to the bank's figure and submits."""
	for investment in get_investments_due_for_accrual():
		make_draft_accrual(investment)


def get_investments_due_for_accrual():
	"""Investments with an ended schedule period not accrued yet, and no draft accrual waiting."""
	investment = frappe.qb.DocType("Investment")
	schedule = frappe.qb.DocType("Investment Interest Schedule")
	accrual = frappe.qb.DocType("Investment Interest Accrual")
	draft_accruals = frappe.qb.from_(accrual).select(accrual.investment).where(accrual.docstatus == 0)

	return (
		frappe.qb.from_(schedule)
		.join(investment)
		.on(schedule.parent == investment.name)
		.select(investment.name)
		.distinct()
		.where(schedule.parenttype == "Investment")
		.where(investment.docstatus == 1)
		.where(schedule.period_to < nowdate())
		.where(investment.accrued_upto.isnull() | (investment.accrued_upto < schedule.period_to))
		.where(investment.name.notin(draft_accruals))
	).run(pluck=True)


def make_draft_accrual(investment):
	"""Make one investment's draft in its own database transaction, so one failure does not stop the others."""
	try:
		values = get_next_accrual(investment, get_schedule(investment))
		if values:
			accrual = frappe.get_doc({"doctype": "Investment Interest Accrual", "investment": investment})
			accrual.update(values)
			accrual.conversion_rate = get_draft_conversion_rate(investment, values.to_date)
			accrual.remarks = _("Prefilled with the estimated interest. Please enter the bank's figure.")
			accrual.insert()

		frappe.db.commit()  # nosemgrep: scheduled job, commit each investment separately
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=_("Draft interest accrual failed for {0}").format(investment))


def get_draft_conversion_rate(investment, to_date):
	"""Exchange Rate on the last day of the period, from Currency Exchange, for the user to check."""
	currency, company = frappe.db.get_value("Investment", investment, ["currency", "company"])
	company_currency = erpnext.get_company_currency(company)
	if currency == company_currency:
		return 1

	return get_exchange_rate(currency, company_currency, to_date)
