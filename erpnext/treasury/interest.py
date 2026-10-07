# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Interest and bond amortisation maths; periods include `start` but not `end`, so each day earns once."""

from functools import cached_property
from itertools import pairwise

from frappe.utils import add_days, add_months, date_diff, flt, getdate

INTEREST_CLASSES = ("Deposit", "Bond")
FREQUENCY_MONTHS = {"Monthly": 1, "Quarterly": 3, "Semi-Annual": 6, "Annual": 12}
DEFAULT_PERIOD_MONTHS = 12


class InterestCalculator:
	def __init__(self, investment):
		self.investment = investment
		self.is_bond = investment.instrument_class == "Bond"
		# a cumulative deposit adds each period's interest to its balance, so later periods earn on it
		self.compounds = not self.is_bond and investment.interest_payout_type == "Cumulative"
		self.maturity_date = getdate(investment.maturity_date)
		self.rate = flt(investment.coupon_rate if self.is_bond else investment.rate_of_interest) / 100
		self.unit_value = flt(investment.face_value) if self.is_bond else 1
		self.period_months = FREQUENCY_MONTHS.get(self.get_frequency(), DEFAULT_PERIOD_MONTHS)
		self.lots = get_lot_timelines(investment.name, self.is_bond)

	def get_frequency(self):
		if self.is_bond:
			return self.investment.coupon_frequency

		if self.investment.interest_payout_type == "Non-Cumulative":
			return self.investment.payout_frequency

		return self.investment.compounding_frequency

	def get_schedule_periods(self):
		"""One period per payout / compounding / coupon period, from the first purchase until maturity or full exit."""
		periods = []
		start, end = self.get_start_date(), self.get_end_date()
		while start and start < end:
			period_end = min(self.get_period_end(start), end)
			periods.append((start, period_end))
			start = period_end

		return periods

	def get_period_end(self, date):
		if self.get_frequency() == "At Maturity":
			return self.maturity_date

		return self.get_reference_period(date)[1]

	def get_start_date(self):
		return min((lot.purchase_date for lot in self.lots), default=None)

	def get_end_date(self):
		"""Maturity, or the day the last lot was fully exited if that is earlier."""
		if any(lot.get_quantity(self.maturity_date) for lot in self.lots):
			return self.maturity_date

		exit_dates = [posting_date for lot in self.lots for posting_date, _quantity in lot.exits]
		return min(max(exit_dates, default=self.maturity_date), self.maturity_date)

	def get_interest(self, start, end, compounded_interest=0):
		"""Interest for the period, also on `compounded_interest` that a cumulative deposit added to it."""
		interest = 0
		for piece_start, piece_end in self.split_at_balance_changes(start, end):
			principal = sum(lot.get_quantity(piece_start) for lot in self.lots) * self.unit_value
			balance = principal + compounded_interest if principal else 0
			interest += balance * self.rate * self.get_year_fraction(piece_start, piece_end)

		return interest

	def get_amortisation(self, start, end):
		"""Bond premium (negative) or discount (positive) earned over the period, effective interest method."""
		if not self.is_bond:
			return 0

		amortisation = 0
		for piece_start, piece_end in self.split_at_balance_changes(start, end):
			for lot in self.lots:
				if not lot.get_quantity(piece_start):
					continue

				value_change = self.get_carrying_value(lot, piece_end) - self.get_carrying_value(
					lot, piece_start
				)
				amortisation += lot.get_quantity(piece_start) * value_change

		return amortisation

	def get_carrying_cost(self, units_already_sold, units_to_sell, posting_date):
		"""Amortised cost of bond units being sold, taken from the oldest lots (FIFO)."""
		lots = take_fifo(self.lots, lambda lot: lot.quantity, units_already_sold, units_to_sell)
		return sum(taken * self.get_carrying_value(lot, getdate(posting_date)) for lot, taken in lots)

	def split_at_balance_changes(self, start, end):
		start, end = getdate(start), getdate(end)
		change_dates = {date for lot in self.lots for date in lot.get_change_dates() if start < date < end}
		boundaries = [start, *sorted(change_dates), end]

		return list(pairwise(boundaries))

	def get_year_fraction(self, start, end):
		convention = self.investment.day_count_convention
		if convention == "Actual/360":
			return date_diff(end, start) / 360

		if convention == "30/360":
			return get_days_30_360(start, end) / 360

		if convention == "Actual/Actual (ICMA)":
			return self.get_icma_fraction(start, end)

		return date_diff(end, start) / 365

	def get_icma_fraction(self, start, end):
		"""Days in each reference period, divided by (days in that period * periods per year)."""
		fraction, periods_per_year = 0, 12 / self.period_months
		while start < end:
			period_start, period_end = self.get_reference_period(start)
			piece_end = min(period_end, end)
			fraction += date_diff(piece_end, start) / (date_diff(period_end, period_start) * periods_per_year)
			start = piece_end

		return fraction

	def get_reference_period(self, date):
		"""Interest period containing `date` (before maturity), counted back from the maturity date."""
		count = 1
		while getdate(add_months(self.maturity_date, -count * self.period_months)) > date:
			count += 1

		return (
			getdate(add_months(self.maturity_date, -count * self.period_months)),
			getdate(add_months(self.maturity_date, -(count - 1) * self.period_months)),
		)

	def get_carrying_value(self, lot, date):
		"""Amortised (clean) cost of one bond unit of `lot` on `date`."""
		if date >= self.maturity_date:
			return self.unit_value

		if lot.effective_rate is None:
			lot.effective_rate = self.get_effective_rate(lot)

		return self.get_present_value(lot.effective_rate, date) - self.get_accrued_coupon(date)

	def get_effective_rate(self, lot):
		"""Annual rate at which the lot's future cash flows discount back to its purchase price (bisection)."""
		target = lot.cost / lot.quantity + self.get_accrued_coupon(lot.purchase_date)
		low, high = -0.99, 10.0
		for _iteration in range(60):
			rate = (low + high) / 2
			if self.get_present_value(rate, lot.purchase_date) > target:
				low = rate
			else:
				high = rate

		return (low + high) / 2

	def get_present_value(self, effective_rate, date):
		value = 0
		for payment_date, amount in self.coupon_payments:
			if payment_date > date:
				value += amount * (1 + effective_rate) ** (-date_diff(payment_date, date) / 365)

		return value

	@cached_property
	def coupon_payments(self):
		"""Coupon (plus face value at maturity) paid per bond unit, as (date, amount)."""
		payments = [(end, self.get_coupon(start, end)) for start, end in self.coupon_periods]
		payments[-1] = (self.maturity_date, payments[-1][1] + self.unit_value)
		return payments

	@cached_property
	def coupon_periods(self):
		first_date = min(self.get_start_date(), getdate(self.investment.purchase_date))
		if self.investment.coupon_frequency == "At Maturity":
			return [(first_date, self.maturity_date)]

		periods = [self.get_reference_period(add_days(self.maturity_date, -1))]
		while periods[0][0] > first_date:
			periods.insert(0, self.get_reference_period(add_days(periods[0][0], -1)))

		return periods

	def get_coupon(self, start, end):
		return self.unit_value * self.rate * self.get_year_fraction(start, end)

	def get_accrued_coupon(self, date):
		"""Coupon earned per bond unit since the last coupon date, not yet paid."""
		for start, end in self.coupon_periods:
			if start <= date < end:
				return self.get_coupon(start, date)

		return 0


class LotTimeline:
	"""Quantity (bond units, or deposit principal) held in one lot over time."""

	def __init__(self, lot, quantity):
		self.purchase_date = getdate(lot.purchase_date)
		self.quantity = quantity
		self.cost = flt(lot.amount)
		self.exits = []
		self.effective_rate = None

	def get_quantity(self, date):
		if date < self.purchase_date:
			return 0

		return self.quantity - sum(quantity for posting_date, quantity in self.exits if posting_date <= date)

	def get_change_dates(self):
		return [self.purchase_date, *(posting_date for posting_date, _quantity in self.exits)]

	def consume(self, posting_date, quantity):
		taken = min(self.get_quantity(posting_date), quantity)
		if taken > 0:
			self.exits.append((posting_date, taken))

		return max(taken, 0)


def get_lot_timelines(investment, is_bond):
	"""Purchases of the investment as lots, with each exit taken from the oldest lot first (FIFO)."""
	from erpnext.treasury.doctype.investment_transaction.investment_transaction import (
		get_exit_transactions,
		get_purchases,
	)

	quantity_field, exit_field = ("units", "units") if is_bond else ("amount", "gross_amount")
	lots = [LotTimeline(lot, flt(lot.get(quantity_field))) for lot in get_purchases(investment)]

	for exit_transaction in get_exit_transactions(investment):
		remaining = flt(exit_transaction.get(exit_field))
		for lot in lots:
			remaining -= lot.consume(getdate(exit_transaction.posting_date), remaining)

	return lots


def take_fifo(lots, get_quantity, already_taken, to_take):
	"""(lot, quantity) pairs taken from the oldest lots first, after skipping what was taken earlier."""
	for lot in lots:
		quantity = get_quantity(lot)
		skipped = min(quantity, already_taken)
		already_taken -= skipped
		taken = min(quantity - skipped, to_take)
		to_take -= taken
		if taken > 0:
			yield lot, taken


def get_days_30_360(start, end):
	"""Day count under the 30/360 (bond basis) convention."""
	start_day = min(start.day, 30)
	end_day = 30 if end.day == 31 and start_day == 30 else end.day

	return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (end_day - start_day)
