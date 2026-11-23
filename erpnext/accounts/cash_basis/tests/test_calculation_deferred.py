# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Phase 7: deferred revenue and deferred expense on the cash basis. CB-21 is a converted case.

The schedule runs from 1 March to 31 May 2026 (92 days). "Book Deferred Entries Based On"
is "Days": March has 31/92 and April 30/92 of the amount.
"""

import frappe

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import EUR_CUSTOMER, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.vouchers import (
	BANK,
	line,
	make_purchase_invoice,
	make_return,
	make_sales_invoice,
	pay,
	save,
)
from erpnext.tests.utils import change_settings

SALES = acc("Sales")
SERVICE = acc("Service")
DEBTORS = acc("Debtors")
CREDITORS = acc("Creditors")
TAX = acc("ST 6%")
DEFERRED = acc("Deferred Revenue")
PREPAID = acc("Prepaid Expenses")
RENT = acc("Office Rent")
DEBTORS_EUR = acc("Debtors EUR")
SECOND = acc("Second")
SCHEDULE = {"service_start_date": "2026-03-01", "service_end_date": "2026-05-31"}


def deferred_line(amount, account=None, **extra):
	return line(
		amount,
		account=account,
		enable_deferred_revenue=1,
		deferred_revenue_account=DEFERRED,
		**SCHEDULE,
		**extra,
	)


def book_schedule(schedule_type, end_date):
	frappe.get_doc(
		{
			"doctype": "Process Deferred Accounting",
			"type": schedule_type,
			"start_date": "2026-03-01",
			"end_date": end_date,
			"posting_date": end_date,
			"company": US_COMPANY,
		}
	).insert().submit()


class TestCashBasisDeferred(CashBasisTestCase):
	def make_cb21(self):
		"""100 of deferred revenue with 10 of tax; 55 paid on 10 April; schedule booked to 30 April."""
		invoice = make_sales_invoice("2026-03-01", [deferred_line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-04-10", 55)
		book_schedule("Income", "2026-04-30")
		return invoice

	def assert_cb21(self):
		self.assertEqual(self.exception_reasons(), {})
		# Accrual: the schedule. March 31/92 x 100 = 33.70, April 30/92 x 100 = 32.61.
		# Cash: nothing in March; in April half of the invoice is paid, 50 of income.
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -33.70, DEFERRED: -66.30, DEBTORS: 110},
			cash={SALES: 0, DEFERRED: 0, DEBTORS: 10, TAX: -10},
		)
		self.assert_balances(
			"2026-04-30",
			from_date="2026-04-01",
			accrual={SALES: -32.61},
			cash={SALES: -50},
		)
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: -66.31, DEFERRED: -33.69, DEBTORS: 55},
			cash={SALES: -50, DEFERRED: 0, DEBTORS: 5, TAX: -10},
		)
		self.assert_invariants("2026-03-31")
		self.assert_invariants("2026-04-30", from_date="2026-04-01")

	def test_cb21_deferred_revenue_converts(self):
		self.make_cb21()
		self.assert_cb21()

	@change_settings(
		"Accounts Settings", {"book_deferred_entries_via_journal_entry": 1, "submit_journal_entries": 1}
	)
	def test_cb21_schedule_booked_by_journal_entries(self):
		self.make_cb21()
		self.assertEqual(
			frappe.db.count("Journal Entry", {"voucher_type": "Deferred Revenue", "docstatus": 1}), 2
		)
		self.assert_cb21()

	def test_unpaid_invoice_with_a_complete_schedule(self):
		make_sales_invoice("2026-03-01", [deferred_line(100)])
		book_schedule("Income", "2026-05-31")
		self.assert_balances(
			"2026-05-31",
			accrual={SALES: -100, DEFERRED: 0, DEBTORS: 100},
			cash={SALES: 0, DEFERRED: 0, DEBTORS: 0},
		)
		self.assert_invariants("2026-05-31")

	def test_paid_invoice_with_a_complete_schedule_matches_accrual(self):
		invoice = make_sales_invoice("2026-03-01", [deferred_line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-03-20")
		book_schedule("Income", "2026-05-31")
		# The income moves to the payment date. The cumulative balances are the same (I4).
		self.assert_balances("2026-03-31", accrual={SALES: -33.70}, cash={SALES: -100, DEFERRED: 0})
		self.assert_balances(
			"2026-05-31", accrual={SALES: -100, DEFERRED: 0}, cash={SALES: -100, DEFERRED: 0, DEBTORS: 0}
		)
		self.assert_invariants("2026-05-31", fully_paid=True)

	def test_two_items_on_one_deferred_account(self):
		invoice = make_sales_invoice("2026-03-01", [deferred_line(60, SALES), deferred_line(40, SERVICE)])
		pay(invoice, "2026-04-10", 50)
		# The deferred row is split by the item amounts: half of each account is recognised.
		self.assert_balances(
			"2026-04-30", accrual={SALES: 0, SERVICE: 0}, cash={SALES: -30, SERVICE: -20, DEFERRED: 0}
		)
		self.assert_invariants("2026-04-30")

	def test_deferred_expense_converts(self):
		invoice = make_purchase_invoice(
			"2026-03-01",
			[line(90, enable_deferred_expense=1, deferred_expense_account=PREPAID, **SCHEDULE)],
		)
		pay(invoice, "2026-04-10", 30)
		book_schedule("Expense", "2026-04-30")
		self.assertEqual(self.exception_reasons(), {})
		# Accrual: 31/92 x 90 = 30.33 and 30/92 x 90 = 29.35. Cash: the 30 paid.
		self.assert_balances(
			"2026-04-30",
			accrual={RENT: 59.68, PREPAID: 30.32, CREDITORS: -60},
			cash={RENT: 30, PREPAID: 0, CREDITORS: 0},
		)
		self.assert_invariants("2026-04-30")

	def test_cancelled_schedule_entry_is_not_removed(self):
		self.make_cb21()
		process = frappe.get_last_doc("Process Deferred Accounting")
		process.cancel()
		# The schedule is gone, so nothing is removed; the cash result is the same.
		self.assert_balances("2026-04-30", accrual={SALES: 0, DEFERRED: -100}, cash={SALES: -50, DEFERRED: 0})
		self.assert_invariants("2026-04-30")

	def test_return_on_the_deferred_account(self):
		invoice = make_sales_invoice("2026-03-01", [deferred_line(100)])
		credit_note = make_return(invoice, "2026-03-10", 40)
		accounts = frappe.get_all(
			"GL Entry", filters={"voucher_no": credit_note.name, "debit": (">", 0)}, pluck="account"
		)
		# The schedule has not started, so the return reverses the deferred account.
		self.assertEqual(accounts, [DEFERRED])
		self.assertEqual(self.exception_reasons(), {})
		pay(invoice, "2026-04-10", 30)
		# 30 of the 100 is paid in cash: 30 of income. The credit note is not settled.
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: 0, DEFERRED: -60, DEBTORS: 30},
			cash={SALES: -30, DEFERRED: 0},
		)
		self.assert_invariants("2026-04-30")

	def test_exception_invoice_keeps_its_schedule(self):
		invoice = self.make_cb21()
		# The user changes the cost center of the item after submit. Until a repost of the ledger,
		# the GL row of the deferred account does not match the item: an exception.
		frappe.db.set_value("Sales Invoice Item", invoice.items[0].name, "cost_center", SECOND)
		self.assertEqual(self.exception_reasons(), {invoice.name: "deferred revenue or expense"})
		# The invoice and its schedule stay as posted.
		balances = {SALES: -66.31, DEFERRED: -33.69, DEBTORS: 55}
		self.assert_balances("2026-04-30", accrual=balances, cash=balances)
		self.assert_invariants("2026-04-30")

	def test_project_of_the_invoice_header(self):
		project = frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test Cash Basis Deferred", "company": US_COMPANY}
		).insert()
		invoice = make_sales_invoice("2026-03-01", [deferred_line(100)], project=project.name)
		self.assertEqual(
			frappe.db.get_value("GL Entry", {"voucher_no": invoice.name, "account": DEFERRED}, "project"),
			project.name,
		)
		pay(invoice, "2026-04-10", 50)
		self.assertEqual(self.exception_reasons(), {})
		self.assert_balances("2026-04-30", cash={SALES: -50, DEFERRED: 0, DEBTORS: 0})
		self.assert_invariants("2026-04-30")

	def test_foreign_currency_deferred_invoice(self):
		invoice = make_sales_invoice(
			"2026-03-01",
			[deferred_line(100)],
			customer=EUR_CUSTOMER,
			currency="EUR",
			conversion_rate=1.10,
			debit_to=DEBTORS_EUR,
			party_account_currency="EUR",
			ignore_pricing_rule=1,
		)
		payment = frappe.new_doc("Payment Entry")
		payment.update(
			{
				"company": US_COMPANY,
				"payment_type": "Receive",
				"party_type": "Customer",
				"party": EUR_CUSTOMER,
				"posting_date": "2026-04-10",
				"paid_from": DEBTORS_EUR,
				"paid_from_account_currency": "EUR",
				"paid_to": BANK,
				"paid_to_account_currency": "USD",
				"paid_amount": 50,
				"source_exchange_rate": 1.10,
				"received_amount": 55,
				"target_exchange_rate": 1,
				"reference_no": "FX-DEF",
				"reference_date": "2026-04-10",
			}
		)
		payment.append(
			"references",
			{"reference_doctype": "Sales Invoice", "reference_name": invoice.name, "allocated_amount": 50},
		)
		save(payment, submit=True)
		book_schedule("Income", "2026-04-30")
		self.assertEqual(self.exception_reasons(), {})
		# 110 USD of deferred revenue. Accrual: 31/92 and 30/92 of 110. Cash: half paid, 55.
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: -72.94, DEFERRED: -37.06},
			cash={SALES: -55, DEFERRED: 0, DEBTORS_EUR: 0},
		)
		self.assert_invariants("2026-04-30")

	@change_settings(
		"Accounts Settings",
		{
			"book_deferred_entries_via_journal_entry": 1,
			"submit_journal_entries": 1,
			"enable_immutable_ledger": 1,
		},
	)
	def test_cancelled_schedule_journal_with_the_immutable_ledger(self):
		self.make_cb21()
		journal = frappe.get_last_doc(
			"Journal Entry", filters={"voucher_type": "Deferred Revenue", "docstatus": 1}
		)
		journal.cancel()
		# The cancel adds reversal rows. The removal of both nets to zero; cash does not change.
		self.assert_balances("2026-04-30", cash={SALES: -50, DEFERRED: 0, DEBTORS: 5})
		self.assert_invariants("2026-04-30")

	def test_items_with_their_own_dimensions(self):
		invoice = make_sales_invoice(
			"2026-03-01", [deferred_line(60, SALES), deferred_line(40, SERVICE, cost_center=SECOND)]
		)
		pay(invoice, "2026-04-10", 50)
		recognised = {
			(row["account"], row["cost_center"]): row["credit"] - row["debit"]
			for row in self.adjustments("2026-04-30")
			if row["remarks"] == "Cash basis: recognition" and row["account"] in (SALES, SERVICE)
		}
		# Each deferred row matches only its own item, so each income account keeps its cost center.
		self.assertEqual(recognised, {(SALES, acc("Main")): 30, (SERVICE, SECOND): 20})
		self.assert_invariants("2026-04-30")

	def test_return_against_the_invoice_on_the_deferred_account(self):
		invoice = make_sales_invoice("2026-03-01", [deferred_line(100)])
		credit_note = make_return(invoice, "2026-03-10", 40, submit=False)
		credit_note.update_outstanding_for_self = 0
		credit_note.save()
		credit_note.submit()
		accounts = frappe.get_all(
			"GL Entry", filters={"voucher_no": credit_note.name, "debit": (">", 0)}, pluck="account"
		)
		self.assertEqual(accounts, [DEFERRED])
		self.assertEqual(self.exception_reasons(), {})
		# The credit note settles 40 of the invoice, non-cash. Its deferred row is removed too.
		self.assert_balances("2026-03-31", cash={SALES: 0, DEFERRED: 0, DEBTORS: 0})
		self.assert_invariants("2026-03-31")
		pay(invoice, "2026-04-10", 60)
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: 0, DEFERRED: -60, DEBTORS: 0},
			cash={SALES: -60, DEFERRED: 0, DEBTORS: 0},
		)
		# No schedule is booked, so I4 does not apply (section 11).
		self.assert_invariants("2026-04-30")

	def test_return_with_another_tax_ratio_than_the_invoice(self):
		# The invoice: a deferred item and an ordinary item, with tax on the net total.
		invoice = make_sales_invoice(
			"2026-03-01", [deferred_line(100), line(100, account=SERVICE)], taxes=[(TAX, 10)]
		)
		# The return of 40 of the deferred item has no tax, so its ratio is not the ratio of V.
		credit_note = make_return(invoice, "2026-03-10", 40, submit=False)
		credit_note.update_outstanding_for_self = 0
		credit_note.taxes = []
		credit_note.save()
		credit_note.submit()
		self.assertEqual(credit_note.base_grand_total, -40)
		# The tax of V is 10 on 200 of lines, so c_V = 200/210; the return has c_X = 1.
		# The deferred row of the return is removed in full. The tax part of V stays: 10.
		self.assert_balances(
			"2026-03-31",
			accrual={SERVICE: -100, DEFERRED: -60, TAX: -10, DEBTORS: 170},
			cash={SERVICE: 0, DEFERRED: 0, TAX: -10, DEBTORS: 10},
		)
		self.assert_invariants("2026-03-31")

	def make_mixed_return(self, with_tax):
		"""V: deferred 100, service 100, tax 10. The return: 40 of the deferred item, 20 of service."""
		invoice = make_sales_invoice(
			"2026-03-01", [deferred_line(100), line(100, account=SERVICE)], taxes=[(TAX, 10)]
		)
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		credit_note = make_return_doc("Sales Invoice", invoice.name)
		credit_note.update({"posting_date": "2026-03-10", "set_posting_time": 1, "due_date": "2026-03-10"})
		credit_note.update_outstanding_for_self = 0
		for row, rate in zip(credit_note.items, (40, 20), strict=True):
			row.qty, row.rate = -1, rate
		if with_tax:
			credit_note.taxes[0].tax_amount = -3
		else:
			credit_note.taxes = []
		return save(credit_note, submit=True)

	def test_mixed_return_with_the_tax_ratio_of_the_invoice(self):
		credit_note = self.make_mixed_return(with_tax=True)
		self.assertEqual(credit_note.base_grand_total, -63)
		# c_X = 60/63 = c_V = 200/210, so the factor is 1: each row of the return is removed.
		self.assert_balances(
			"2026-03-31",
			accrual={SERVICE: -80, DEFERRED: -60, TAX: -7, DEBTORS: 147},
			cash={SERVICE: 0, DEFERRED: 0, TAX: -7, DEBTORS: 7},
		)
		self.assert_invariants("2026-03-31")

	def test_mixed_return_with_no_tax(self):
		credit_note = self.make_mixed_return(with_tax=False)
		self.assertEqual(credit_note.base_grand_total, -60)
		# c_X = 1 and c_V = 200/210: the service row is removed at 0.952, so 0.95 stays, as for
		# any credit note with another tax ratio. The deferred row is removed in full.
		self.assert_balances(
			"2026-03-31",
			accrual={SERVICE: -80, DEFERRED: -60, TAX: -10, DEBTORS: 150},
			cash={SERVICE: 0.95, DEFERRED: 0, TAX: -10, DEBTORS: 9.05},
		)
		self.assert_invariants("2026-03-31")


class TestCashBasisDeferredDiscount(CashBasisTestCase):
	"""Open point 12: the amount of a deferred item is the amount of its GL row."""

	def make_invoice(self, discount_account=None, **fields):
		return make_sales_invoice(
			"2026-03-01",
			[deferred_line(60), deferred_line(40, account=SERVICE)],
			discount_amount=10,
			additional_discount_account=discount_account or acc("Write Off"),
			**fields,
		)

	def item_amounts(self, invoice):
		from erpnext.accounts.cash_basis.queries import get_deferred_items

		return sorted(
			item.amount for item in get_deferred_items("Sales Invoice", [invoice.name])[invoice.name]
		)

	def deferred_total(self, invoice):
		filters = {"voucher_no": invoice.name, "account": DEFERRED, "is_cancelled": 0}
		return sum(frappe.get_all("GL Entry", filters, pluck="credit"))

	def test_posted_with_discount_accounting(self):
		# The 10% discount posts to its own account, so the deferred rows are 60 and 40. The
		# setting is off when the report runs: the GL of the invoice decides, not the setting.
		with change_settings("Selling Settings", {"enable_discount_accounting": 1}):
			invoice = self.make_invoice()
		self.assertEqual(self.deferred_total(invoice), 100)
		self.assertEqual(self.item_amounts(invoice), [40, 60])
		pay(invoice, "2026-04-10", 90)
		self.assert_invariants("2026-04-30")

	def test_posted_without_discount_accounting(self):
		# The discount reduces the item rows to 54 and 36, also with a discount account on the invoice.
		invoice = self.make_invoice()
		self.assertEqual(self.deferred_total(invoice), 90)
		with change_settings("Selling Settings", {"enable_discount_accounting": 1}):
			self.assertEqual(self.item_amounts(invoice), [36, 54])

	def test_cash_discount_without_discount_accounting(self):
		# "Is Cash or Non Trade Discount" posts the discount row with the setting off. The discount
		# is on the grand total, so the net amounts and the deferred rows stay at 60 and 40.
		invoice = self.make_invoice(is_cash_or_non_trade_discount=1, apply_discount_on="Grand Total")
		self.assertEqual(self.deferred_total(invoice), 100)
		self.assertEqual(self.item_amounts(invoice), [40, 60])

	def test_discount_account_is_the_income_account(self):
		# The schedule posts rows on Sales under the voucher number of the invoice. With the
		# discount on Sales too, those rows must not make the invoice look "before discount".
		invoice = self.make_invoice(discount_account=SALES)
		book_schedule("Income", "2026-03-31")
		self.assertEqual(self.item_amounts(invoice), [36, 54])
		self.assert_invariants("2026-03-31")

	def test_item_discounts_with_discount_accounting(self):
		# Round 3 of the review. The item discount row posts to the deferred account too: Sales
		# has 50 after a discount of 50, Service has 100. The deferred row is 200: 100 and 100.
		with change_settings("Selling Settings", {"enable_discount_accounting": 1}):
			invoice = make_sales_invoice(
				"2026-03-01",
				[
					deferred_line(50, price_list_rate=100, discount_account=acc("Write Off")),
					deferred_line(100, account=SERVICE),
				],
				ignore_pricing_rule=1,
			)
		self.assertEqual(invoice.items[0].discount_amount, 50)
		self.assertEqual(self.deferred_total(invoice), 200)
		self.assertEqual(self.item_amounts(invoice), [100, 100])
		pay(invoice, "2026-04-10", 150)
		self.assert_invariants("2026-04-30")
