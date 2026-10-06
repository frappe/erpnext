# Copyright (c) 2026, Aagnya Mistry and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import freeze_time
from frappe.utils import flt, getdate

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
from erpnext.treasury.interest import get_days_30_360

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
		self.assertEqual((first_quarter.status, first_quarter.interest_accrual), ("Accrued", accrual.name))

	def test_accrual_across_periods_is_split_by_days(self):
		investment = make_fd(FD_TERMS)
		# 120 days: 90 in the first quarter, 30 in the second
		make_interest_accrual(investment.name, "2026-01-01", "2026-04-30", 2400).submit()

		first_quarter, second_quarter = get_investment(investment.name).interest_schedule[:2]
		self.assertEqual((first_quarter.actual_interest, first_quarter.status), (1800, "Accrued"))
		self.assertEqual((second_quarter.actual_interest, second_quarter.status), (600, "Partially Accrued"))
		self.assertEqual(second_quarter.variance, 0)

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

		amortisation = 0
		while defaults := get_accrual_defaults(investment.name):
			accrual = make_interest_accrual(
				investment.name, defaults.from_date, defaults.to_date, defaults.interest_amount
			).submit()
			amortisation += accrual.amortisation_amount

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


def make_deposit(investment, transaction_type, posting_date, gross_amount, submit=True):
	transaction = make_transaction(
		investment, transaction_type, posting_date=posting_date, gross_amount=gross_amount
	)
	return transaction.submit() if submit else transaction


def get_investment(name):
	return frappe.get_doc("Investment", name)
