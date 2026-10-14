# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import freeze_time
from frappe.utils import add_days, add_months, flt, getdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.doctype.investment.test_investment import (
	create_financial_institution,
	create_investment_type,
)
from erpnext.treasury.doctype.investment_interest_accrual.investment_interest_accrual import (
	get_accrual_defaults,
	make_draft_accruals,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	get_gl_entries,
	make_interest_accrual,
	make_submitted_investment,
	make_transaction,
)
from erpnext.treasury.interest import InterestCalculator, get_days_30_360

FD_TERMS = {
	"purchase_date": "2026-01-01",
	"maturity_date": "2027-01-01",
	"rate_of_interest": 7.3,
	"interest_payout_type": "Non-Cumulative",
	"payout_frequency": "Quarterly",
}
CUMULATIVE_FD_TERMS = {
	**FD_TERMS,
	"interest_payout_type": "Cumulative",
	"compounding_frequency": "Quarterly",
}
BOND_TERMS = {
	"investment_type": "_Test Corporate Bond",
	"purchase_date": "2026-01-01",
	"maturity_date": "2028-01-01",
	"face_value": 1000,
	"coupon_rate": 8,
	"coupon_frequency": "Semi-Annual",
}


class TestInvestmentInterestAccrual(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_investment_type("_Test Corporate Bond", "Bond")
		create_financial_institution("_Test Bank")

	def test_purchase_creates_estimated_schedule(self):
		investment = make_fd(FD_TERMS)

		schedule = investment.interest_schedule
		self.assertEqual(len(schedule), 4)
		self.assertEqual(getdate(schedule[0].period_to), getdate("2026-03-31"))
		self.assertEqual(getdate(schedule[-1].period_to), getdate("2026-12-31"))
		# first quarter: 100000 * 7.3% * 90 / 365, simple interest because it is paid out
		self.assertEqual(schedule[0].estimated_interest, 1800)
		self.assertEqual(sum(row.estimated_interest for row in schedule), 7300)
		self.assertEqual({row.status for row in schedule}, {"Pending"})

	def test_schedule_has_one_row_per_period_of_the_tenure(self):
		two_years_quarterly = make_fd({**FD_TERMS, "maturity_date": "2028-01-01"})
		three_years_half_yearly = make_fd(
			{**FD_TERMS, "maturity_date": "2029-01-01", "payout_frequency": "Semi-Annual"}
		)

		self.assertEqual(len(two_years_quarterly.interest_schedule), 8)
		self.assertEqual(len(three_years_half_yearly.interest_schedule), 6)

	def test_rebuilt_schedule_replaces_old_rows(self):
		investment = make_fd(FD_TERMS)
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1790).submit()

		schedule = get_investment(investment.name).interest_schedule
		self.assertEqual(len(schedule), 4)
		self.assertEqual(frappe.db.count("Investment Interest Schedule", {"parent": investment.name}), 4)

	def test_cumulative_deposit_compounds(self):
		investment = make_fd(CUMULATIVE_FD_TERMS)

		# second quarter earns on the principal plus the first quarter's interest: 101800 * 7.3% * 91 / 365
		self.assertEqual(investment.interest_schedule[0].estimated_interest, 1800)
		self.assertEqual(investment.interest_schedule[1].estimated_interest, 1852.76)

	def test_compounding_follows_actual_interest(self):
		investment = make_fd(CUMULATIVE_FD_TERMS)
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1790).submit()

		schedule = get_investment(investment.name).interest_schedule
		self.assertEqual((schedule[0].actual_interest, schedule[0].variance), (1790, -10))
		# 101790 * 7.3% * 91 / 365
		self.assertEqual(schedule[1].estimated_interest, 1852.58)

	def test_interest_paid_out_stops_compounding(self):
		investment = make_fd(CUMULATIVE_FD_TERMS)
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1800).submit()
		make_transaction(
			investment.name, "Interest Receipt", posting_date="2026-04-01", interest_amount=1800
		).submit()

		# the first quarter's interest was paid out, so the second earns on 100000 only: 100000 * 7.3% * 91 / 365
		self.assertEqual(get_investment(investment.name).interest_schedule[1].estimated_interest, 1820)

	def test_reference_period_matches_stepping_back_from_maturity(self):
		for maturity_date, frequency in (
			("2031-01-31", "Monthly"),
			("2030-08-31", "Quarterly"),
			("2032-02-29", "Semi-Annual"),
		):
			investment = frappe._dict(
				name="_Test No Lots",
				instrument_class="Bond",
				coupon_frequency=frequency,
				maturity_date=maturity_date,
			)
			calculator = InterestCalculator(investment)
			date = getdate(add_months(maturity_date, -60))
			while date < getdate(maturity_date):
				count = 1
				while getdate(add_months(maturity_date, -count * calculator.period_months)) > date:
					count += 1

				expected = (
					getdate(add_months(maturity_date, -count * calculator.period_months)),
					getdate(add_months(maturity_date, -(count - 1) * calculator.period_months)),
				)
				self.assertEqual(calculator.get_reference_period(date), expected, date)
				date = getdate(add_days(date, 1))

	def test_submit_locks_the_investment(self):
		investment = make_fd(FD_TERMS)
		accrual = make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1800).insert()

		with patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value:
			accrual.submit()

		self.assertIn(
			(("Investment", investment.name, "modified"), {"for_update": True}),
			[(call.args, call.kwargs) for call in get_value.call_args_list],
		)

	def test_accrual_posts_bank_figure_and_fills_schedule(self):
		investment = make_fd(FD_TERMS)
		accrual = make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1795).submit()

		self.assertEqual((accrual.estimated_interest, accrual.variance), (1800, -5))
		self.assertEqual(
			get_gl_entries(accrual.name, accrual.doctype),
			{"Earnest Money - _TC": (1795, 0), "Interest on Fixed Deposits - _TC": (0, 1795)},
		)

		investment = get_investment(investment.name)
		self.assertEqual(getdate(investment.accrued_upto), getdate("2026-03-31"))
		self.assertEqual(investment.accrued_interest, 1795)
		first_quarter = investment.interest_schedule[0]
		self.assertEqual((first_quarter.status, first_quarter.interest_accruals), ("Accrued", accrual.name))

	def test_accrual_across_periods_is_split_by_days(self):
		investment = make_fd(FD_TERMS)
		# 120 days: 90 in the first quarter, 30 in the second
		make_interest_accrual(investment.name, "2026-01-01", "2026-04-30", 2400).submit()

		first_quarter, second_quarter = get_investment(investment.name).interest_schedule[:2]
		self.assertEqual((first_quarter.actual_interest, first_quarter.status), (1800, "Accrued"))
		self.assertEqual((second_quarter.actual_interest, second_quarter.status), (600, "Partially Accrued"))
		self.assertEqual(second_quarter.variance, 0)

	def test_period_lists_every_accrual_covering_it(self):
		investment = make_fd(FD_TERMS)
		first = make_interest_accrual(investment.name, "2026-01-01", "2026-02-28", 1180).submit()
		second = make_interest_accrual(investment.name, "2026-03-01", "2026-03-31", 620).submit()

		first_quarter = get_investment(investment.name).interest_schedule[0]
		self.assertEqual(first_quarter.actual_interest, 1800)
		self.assertEqual(first_quarter.interest_accruals, f"{first.name}, {second.name}")

	def test_accruals_cannot_leave_gaps_or_overlap(self):
		investment = make_fd(FD_TERMS)
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1800).submit()

		for from_date in ("2026-03-20", "2026-04-05"):
			accrual = make_interest_accrual(investment.name, from_date, "2026-06-30", 1000)
			self.assertRaises(frappe.ValidationError, accrual.insert)

	def test_accrual_cannot_go_past_maturity(self):
		investment = make_fd(FD_TERMS)

		accrual = make_interest_accrual(investment.name, "2026-01-01", "2027-01-05", 7300)
		self.assertRaises(frappe.ValidationError, accrual.insert)

	def test_posting_date_cannot_be_before_to_date(self):
		investment = make_fd(FD_TERMS)

		accrual = make_interest_accrual(
			investment.name, "2026-01-01", "2026-03-31", 1800, posting_date="2026-03-15"
		)
		self.assertRaises(frappe.ValidationError, accrual.insert)

	def test_interest_needs_a_deposit_first(self):
		investment = make_submitted_investment(**FD_TERMS)

		accrual = make_interest_accrual(investment.name, "2026-01-01", "2026-01-31", 100)
		self.assertRaises(frappe.ValidationError, accrual.insert)

	def test_defaults_are_next_period_with_estimate(self):
		investment = make_fd(FD_TERMS)

		defaults = get_accrual_defaults(investment.name)
		self.assertEqual(
			(defaults.from_date, defaults.to_date), (getdate("2026-01-01"), getdate("2026-03-31"))
		)
		self.assertEqual(defaults.interest_amount, 1800)

		make_interest_accrual(investment.name, "2026-01-01", "2026-02-15", 900).submit()
		defaults = get_accrual_defaults(investment.name)
		self.assertEqual(
			(defaults.from_date, defaults.to_date), (getdate("2026-02-16"), getdate("2026-03-31"))
		)

	def test_only_latest_accrual_can_be_cancelled(self):
		investment = make_fd(FD_TERMS)
		first = make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1800).submit()
		second = make_interest_accrual(investment.name, "2026-04-01", "2026-06-30", 1820).submit()

		self.assertRaises(frappe.ValidationError, first.cancel)

		second.cancel()
		investment = get_investment(investment.name)
		self.assertEqual(getdate(investment.accrued_upto), getdate("2026-03-31"))
		self.assertEqual([row.status for row in investment.interest_schedule[:2]], ["Accrued", "Pending"])

	def test_exit_needs_interest_accrued_first(self):
		investment = make_fd(FD_TERMS)

		withdrawal = make_deposit(investment.name, "Withdrawal", "2026-02-01", 40000, submit=False)
		self.assertRaises(frappe.ValidationError, withdrawal.submit)

		make_interest_accrual(investment.name, "2026-01-01", "2026-01-31", 620).submit()
		make_deposit(investment.name, "Withdrawal", "2026-02-01", 40000)

		first_quarter = get_investment(investment.name).interest_schedule[0]
		# January on 100000 (620) + 1 Feb to 31 Mar on the remaining 60000 (708)
		self.assertEqual(first_quarter.estimated_interest, 1328)
		self.assertEqual((first_quarter.actual_interest, first_quarter.status), (620, "Partially Accrued"))
		# the next accrual's estimate is on the 60000 left, not a share of the quarter's 1328
		self.assertEqual(get_accrual_defaults(investment.name).interest_amount, 708)

	def test_accrual_used_by_an_exit_cannot_be_cancelled(self):
		investment = make_fd(FD_TERMS)
		accrual = make_interest_accrual(investment.name, "2026-01-01", "2026-01-31", 620).submit()
		make_deposit(investment.name, "Withdrawal", "2026-02-01", 40000)

		self.assertRaises(frappe.ValidationError, accrual.cancel)

	def test_maturity_paid_late_needs_interest_only_up_to_maturity(self):
		investment = make_fd(FD_TERMS)
		accrue_all_interest(investment.name)

		# matures on 1 Jan, paid on 5 Jan: interest stopped on 31 Dec
		maturity = make_deposit(investment.name, "Maturity", "2027-01-05", 100000)
		self.assertEqual(maturity.docstatus, 1)

	def test_principal_cannot_change_inside_accrued_period(self):
		investment = make_fd(FD_TERMS)
		make_interest_accrual(investment.name, "2026-01-01", "2026-03-31", 1800).submit()

		purchase = make_deposit(investment.name, "Purchase", "2026-03-15", 10000, submit=False)
		self.assertRaises(frappe.ValidationError, purchase.insert)

	def test_daily_job_makes_one_draft_with_estimate(self):
		investment = make_fd(FD_TERMS)

		# the job commits after each investment, which would keep this test's records
		with freeze_time("2026-07-15"), patch.object(frappe.db, "commit"):
			make_draft_accruals()
			make_draft_accruals()

		drafts = frappe.get_all(
			"Investment Interest Accrual",
			filters={"investment": investment.name, "docstatus": 0},
			fields=["from_date", "to_date", "interest_amount"],
		)
		self.assertEqual(len(drafts), 1)
		self.assertEqual(getdate(drafts[0].to_date), getdate("2026-03-31"))
		self.assertEqual(drafts[0].interest_amount, 1800)

	def test_bond_discount_is_amortised_to_face_value(self):
		investment = make_submitted_investment(**BOND_TERMS)
		make_transaction(investment.name, "Purchase", posting_date="2026-01-01", units=10, rate=950).submit()

		amortisation = sum(accrual.amortisation_amount for accrual in accrue_all_interest(investment.name))
		self.assertEqual(flt(amortisation, 2), 500)

		maturity = make_transaction(
			investment.name, "Maturity", posting_date="2028-01-01", units=10, rate=1000
		).submit()
		self.assertEqual(maturity.cost_of_units_sold, 10000)
		self.assertEqual(maturity.realised_gain_loss, 0)
		self.assertEqual(get_investment(investment.name).total_cost, 0)

	def test_30_360_day_count(self):
		# every month counts as 30 days, and the 31st is treated as the 30th
		self.assertEqual(get_days_30_360(getdate("2026-02-01"), getdate("2026-03-01")), 30)
		self.assertEqual(get_days_30_360(getdate("2026-01-31"), getdate("2026-03-31")), 60)
		self.assertEqual(get_days_30_360(getdate("2026-01-01"), getdate("2027-01-01")), 360)


def make_fd(terms, amount=100000):
	investment = make_submitted_investment(**terms)
	make_deposit(investment.name, "Purchase", terms["purchase_date"], amount)

	return get_investment(investment.name)


def accrue_all_interest(investment):
	"""Submit an accrual of the estimated interest for every period up to maturity."""
	accruals = []
	while defaults := get_accrual_defaults(investment):
		accruals.append(
			make_interest_accrual(
				investment, defaults.from_date, defaults.to_date, defaults.interest_amount
			).submit()
		)

	return accruals


def make_deposit(investment, transaction_type, posting_date, gross_amount, submit=True):
	transaction = make_transaction(
		investment, transaction_type, posting_date=posting_date, gross_amount=gross_amount
	)
	return transaction.submit() if submit else transaction


def get_investment(name):
	return frappe.get_doc("Investment", name)
