# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Scenarios CB-07 and CB-08: an advance receipt in an earlier period, reconciled later."""

import frappe
from frappe.tests.classes.context_managers import freeze_time

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.vouchers import (
	line,
	make_advance,
	make_journal_entry,
	make_return,
	make_sales_invoice,
	reconcile,
)

SALES = acc("Sales")
DEBTORS = acc("Debtors")
ADVANCES = acc("Customer Advances Received")
UNAPPLIED = acc("Test Unapplied Receipts")
BANK = acc("Test Bank")

FEBRUARY = ("2026-02-01", "2026-02-28")
MARCH = ("2026-03-01", "2026-03-31")
RECONCILIATION_DATE = "2026-03-20"


def reclassify_to_doubtful_debts(invoice):
	"""Move the open amount of an invoice to a doubtful debts receivable. No cash moves."""
	doubtful = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": "Doubtful Debtors",
			"parent_account": acc("Accounts Receivable"),
			"company": US_COMPANY,
			"account_type": "Receivable",
		}
	).insert()
	make_journal_entry(
		"2026-03-15",
		[
			{"account": doubtful.name, "debit": 100, "party_type": "Customer", "party": CUSTOMER},
			{
				"account": DEBTORS,
				"credit": 100,
				"party_type": "Customer",
				"party": CUSTOMER,
				"reference_type": "Sales Invoice",
				"reference_name": invoice.name,
			},
		],
	)


class AdvanceScenario:
	def make_advance_and_invoice(self, party_account=None):
		make_advance("Customer", CUSTOMER, "2026-02-10", 100, party_account=party_account)
		make_sales_invoice("2026-03-05", [line(100)])

	def reconcile_on(self, advance_account=None):
		with freeze_time(RECONCILIATION_DATE):
			reconcile("Customer", CUSTOMER, DEBTORS, advance_account)

	def period(self, period, accrual=None, cash=None):
		from_date, to_date = period
		self.assert_balances(to_date, from_date=from_date, accrual=accrual, cash=cash)


class TestAdvanceIncomeAndExpense(AdvanceScenario, CashBasisTestCase):
	def test_cb07_advance_before_and_after_reconciliation(self):
		self.make_advance_and_invoice()
		# Before the reconciliation: the receipt is unapplied income in February.
		self.period(FEBRUARY, accrual={SALES: 0, BANK: 100}, cash={UNAPPLIED: -100, SALES: 0})
		self.period(MARCH, accrual={SALES: -100}, cash={UNAPPLIED: 0, SALES: 0})

		self.reconcile_on()
		# After the reconciliation: February stays. In March the unapplied account decreases
		# and the income account increases by the same amount.
		self.period(FEBRUARY, accrual={SALES: 0, DEBTORS: -100}, cash={UNAPPLIED: -100, SALES: 0, DEBTORS: 0})
		self.period(MARCH, accrual={SALES: -100, DEBTORS: 100}, cash={UNAPPLIED: 100, SALES: -100})
		self.assert_balances("2026-03-31", cash={UNAPPLIED: 0, SALES: -100, DEBTORS: 0, BANK: 100})
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_cb07_journal_entry_receipt(self):
		make_journal_entry(
			"2026-02-10",
			[
				{"account": BANK, "debit": 100},
				{"account": DEBTORS, "credit": 100, "party_type": "Customer", "party": CUSTOMER},
			],
		)
		make_sales_invoice("2026-03-05", [line(100)])
		self.assert_balances("2026-02-28", cash={UNAPPLIED: -100, SALES: 0})
		self.reconcile_on()
		# The reconciliation leaves the receipt with no own row. February must not change.
		self.assert_balances("2026-02-28", cash={UNAPPLIED: -100, SALES: 0})
		self.period(MARCH, cash={UNAPPLIED: 100, SALES: -100})
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_cb07_receipt_on_clearing_account(self):
		clearing = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Card Clearing",
				"parent_account": acc("Current Assets"),
				"company": US_COMPANY,
			}
		).insert()
		make_journal_entry(
			"2026-02-10",
			[
				{"account": clearing.name, "debit": 100},
				{"account": DEBTORS, "credit": 100, "party_type": "Customer", "party": CUSTOMER},
			],
		)
		make_sales_invoice("2026-03-05", [line(100)])
		self.reconcile_on()
		# The receipt has no Bank or Cash row. It decreases the receivable, so it is a payment.
		self.assert_balances("2026-02-28", cash={UNAPPLIED: -100, SALES: 0})
		self.period(MARCH, cash={UNAPPLIED: 100, SALES: -100})

	def test_reclassification_to_doubtful_debts_is_not_cash(self):
		invoice = make_sales_invoice("2026-03-05", [line(100)])
		reclassify_to_doubtful_debts(invoice)
		self.assert_balances("2026-03-31", accrual={SALES: -100}, cash={SALES: 0, UNAPPLIED: 0})

	def test_one_journal_for_credit_note_and_payment(self):
		advance = make_advance("Customer", CUSTOMER, "2026-02-10", 40)
		invoice = make_sales_invoice("2026-03-05", [line(100)])
		credit_note = make_return(invoice, "2026-03-06", 60)
		make_journal_entry(
			"2026-03-15",
			[
				{
					"account": DEBTORS,
					"credit": 100,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
				{
					"account": DEBTORS,
					"debit": 60,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": credit_note.name,
				},
				{
					"account": DEBTORS,
					"debit": 40,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Payment Entry",
					"reference_name": advance.name,
				},
			],
		)
		# The advance of 40 is cash for the invoice. The credit note of 60 is non-cash, with no tax:
		# income 100 - 60 = 40, all of it from the advance. The unapplied account ends at zero.
		self.period(FEBRUARY, cash={UNAPPLIED: -40, SALES: 0})
		self.assert_balances("2026-03-31", accrual={SALES: -40}, cash={SALES: -40, UNAPPLIED: 0})

	def test_journal_draws_on_credit_moved_by_an_earlier_journal(self):
		second = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Second Debtors",
				"parent_account": acc("Accounts Receivable"),
				"company": US_COMPANY,
				"account_type": "Receivable",
			}
		).insert()
		make_advance("Customer", CUSTOMER, "2026-02-10", 100)
		party = {"party_type": "Customer", "party": CUSTOMER}
		make_journal_entry(
			"2026-02-20",
			[{"account": DEBTORS, "debit": 100, **party}, {"account": second.name, "credit": 100, **party}],
		)
		invoice = make_sales_invoice("2026-03-05", [line(100)])
		make_journal_entry(
			"2026-03-15",
			[
				{"account": second.name, "debit": 100, **party},
				{
					"account": DEBTORS,
					"credit": 100,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
					**party,
				},
			],
		)
		# The cash of the advance moves to the second account, then onto the invoice.
		self.period(FEBRUARY, cash={UNAPPLIED: -100, SALES: 0})
		self.assert_balances("2026-03-31", cash={UNAPPLIED: 0, SALES: -100})

	def make_link_journal(self, posting_date, reference_type, reference_name, invoice):
		return make_journal_entry(
			posting_date,
			[
				{
					"account": DEBTORS,
					"debit": 100,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": reference_type,
					"reference_name": reference_name,
				},
				{
					"account": DEBTORS,
					"credit": 100,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
			],
		)

	def test_link_journal_uses_advance_payment_entry(self):
		advance = make_advance("Customer", CUSTOMER, "2026-02-10", 100)
		invoice = make_sales_invoice("2026-03-05", [line(100)])
		self.make_link_journal("2026-03-15", "Payment Entry", advance.name, invoice)
		self.period(FEBRUARY, cash={UNAPPLIED: -100, SALES: 0})
		self.assert_balances("2026-03-31", cash={UNAPPLIED: 0, SALES: -100})
		self.assert_invariants("2026-03-31", fully_paid=True)


class TestAdvanceBalanceSheetTreatment(AdvanceScenario, CashBasisTestCase):
	treatment = "Balance Sheet"

	def test_cb07_advance_stays_on_party_account(self):
		self.make_advance_and_invoice()
		self.reconcile_on()
		self.period(FEBRUARY, accrual={DEBTORS: -100}, cash={SALES: 0, DEBTORS: -100})
		self.period(MARCH, accrual={SALES: -100}, cash={SALES: -100})
		self.assertFalse([r for r in self.adjustments("2026-03-31") if r["account"] == UNAPPLIED])
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_reclassification_to_doubtful_debts_is_not_cash(self):
		invoice = make_sales_invoice("2026-03-05", [line(100)])
		reclassify_to_doubtful_debts(invoice)
		self.assert_balances("2026-03-31", accrual={SALES: -100}, cash={SALES: 0})


class TestAdvanceSeparateAccount(AdvanceScenario, CashBasisTestCase):
	def use_separate_account(self, effect):
		company = frappe.get_doc("Company", US_COMPANY)
		company.book_advance_payments_in_separate_party_account = 1
		company.default_advance_received_account = ADVANCES
		company.reconciliation_takes_effect_on = effect
		company.save()

	def check_effect(self, effect, february_advance_balance):
		self.use_separate_account(effect)
		self.make_advance_and_invoice(party_account=ADVANCES)
		self.reconcile_on(advance_account=ADVANCES)
		self.period(
			FEBRUARY,
			accrual={SALES: 0, ADVANCES: february_advance_balance},
			cash={UNAPPLIED: -100, SALES: 0},
		)
		self.period(MARCH, accrual={SALES: -100}, cash={UNAPPLIED: 100, SALES: -100})
		self.assert_balances(
			"2026-03-31", accrual={ADVANCES: 0, DEBTORS: 0}, cash={UNAPPLIED: 0, SALES: -100, BANK: 100}
		)
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_cb08_advance_payment_date(self):
		# The advance is used on its own date.
		self.check_effect("Advance Payment Date", february_advance_balance=0)

	def test_cb08_oldest_of_invoice_or_advance(self):
		self.check_effect("Oldest Of Invoice Or Advance", february_advance_balance=-100)

	def test_cb08_reconciliation_date(self):
		self.check_effect("Reconciliation Date", february_advance_balance=-100)
		# A report to a date before the reconciliation sees the receipt as unapplied, as the ledger does.
		self.assert_balances(
			"2026-03-15", accrual={ADVANCES: -100, DEBTORS: 100}, cash={UNAPPLIED: -100, SALES: 0}
		)

	def test_cb08_advance_payment_date_before_invoice_date(self):
		self.use_separate_account("Advance Payment Date")
		self.make_advance_and_invoice(party_account=ADVANCES)
		self.reconcile_on(advance_account=ADVANCES)
		# The allocation rows carry the advance date, before the invoice exists. February still
		# shows the receipt as unapplied, and no income.
		self.assert_balances("2026-02-28", cash={UNAPPLIED: -100, SALES: 0})

	def test_cb08_one_advance_for_two_invoices(self):
		self.use_separate_account("Reconciliation Date")
		make_advance("Customer", CUSTOMER, "2026-02-10", 100, party_account=ADVANCES)
		make_sales_invoice("2026-03-05", [line(60)])
		make_sales_invoice("2026-03-06", [line(40)])
		self.reconcile_on(advance_account=ADVANCES)
		# Each allocation uses its own part of the advance. The unapplied account ends at zero.
		self.period(FEBRUARY, cash={UNAPPLIED: -100, SALES: 0})
		self.period(MARCH, accrual={SALES: -100}, cash={UNAPPLIED: 100, SALES: -100})
		self.assert_balances("2026-03-31", cash={UNAPPLIED: 0, SALES: -100})
		self.assert_invariants("2026-03-31", fully_paid=True)

	def test_party_rows_journal_moves_advance_to_invoice(self):
		self.use_separate_account("Advance Payment Date")
		make_advance("Customer", CUSTOMER, "2026-02-10", 100, party_account=ADVANCES)
		invoice = make_sales_invoice("2026-03-05", [line(100)])
		make_journal_entry(
			"2026-03-15",
			[
				{"account": ADVANCES, "debit": 100, "party_type": "Customer", "party": CUSTOMER},
				{
					"account": DEBTORS,
					"credit": 100,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
			],
		)
		# The Journal Entry applies the advance in cash terms: no credit obligation is on it.
		self.period(FEBRUARY, cash={UNAPPLIED: -100})
		self.period(MARCH, accrual={SALES: -100}, cash={UNAPPLIED: 100, SALES: -100})
		self.assertEqual(self.exception_reasons(), {})
		self.assert_invariants("2026-03-31", fully_paid=True)
