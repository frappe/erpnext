# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Scenarios CB-09 to CB-12, CB-15, CB-20, CB-23, CB-24: settlements of each class."""

import frappe
from frappe.tests.classes.context_managers import freeze_time

from erpnext.accounts.cash_basis.settlements import get_settlement_events
from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, CUSTOMER_2, US_COMPANY, acc
from erpnext.accounts.cash_basis.tests.vouchers import (
	BANK,
	MAIN_CC,
	line,
	make_advance,
	make_journal_entry,
	make_return,
	make_sales_invoice,
	pay,
	reconcile,
	save,
)
from erpnext.accounts.doctype.journal_entry.mapper import get_payment_entry_against_invoice
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.tests.utils import change_settings

SALES = acc("Sales")
SERVICE = acc("Service")
DEBTORS = acc("Debtors")
TAX = acc("ST 6%")
WRITE_OFF = acc("Write Off")
CASH_ACCOUNT = acc("Cash")
UNAPPLIED = acc("Test Unapplied Receipts")


class TestCashBasisSettlements(CashBasisTestCase):
	def test_cb09_credit_note_against_part_paid_invoice(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		pay(invoice, "2026-03-10", 55)
		make_return(invoice, "2026-04-01", 40)
		# c = 100 / 110. The payment of 55 recognises 50. The open credit note converts only when settled.
		self.assert_balances("2026-04-30", accrual={SALES: -60, TAX: -10}, cash={SALES: -50, TAX: -10})

		with freeze_time("2026-04-15"):
			reconcile("Customer", CUSTOMER, DEBTORS)
		# The credit note settles 40 of the invoice, non-cash. Its own line of 40 keeps
		# 40 * (1 - (100/110) / 1) = 3.64: the part of the credit that was tax on the invoice.
		self.assert_balances("2026-04-30", cash={SALES: -46.36, TAX: -10})

		pay(invoice, "2026-05-01", 15)
		# The invoice is settled: 70 in cash and 40 by the credit note. 63.64 - 3.64 = 60.
		self.assert_balances(
			"2026-05-31", accrual={SALES: -60, TAX: -10}, cash={SALES: -60, TAX: -10, DEBTORS: 0}
		)

	def test_credit_note_journal_with_deferred_credit_note_is_non_cash(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		credit_note = make_return(invoice, "2026-04-01", 40, submit=False)
		credit_note.items[0].update(
			{
				"enable_deferred_revenue": 1,
				"deferred_revenue_account": acc("Deferred Revenue"),
				"service_start_date": "2026-04-01",
				"service_end_date": "2026-06-30",
			}
		)
		credit_note.save()
		credit_note.submit()
		with freeze_time("2026-04-15"):
			reconcile("Customer", CUSTOMER, DEBTORS)
		# Phase 7: the deferred credit note converts. Its item posts to Sales (an ordinary line).
		self.assertEqual(self.exception_reasons(), {})
		# No cash moves: the Payment Reconciliation Journal Entry stays non-cash for both vouchers.
		events = get_settlement_events(US_COMPANY, "2026-04-30")
		self.assertEqual([e["settlement_class"] for e in events], ["Non-cash", "Non-cash"])
		self.assert_balances(
			"2026-04-30",
			# The invoice of the return has no deferred item, so the return posts to Sales.
			accrual={SALES: -60, acc("Deferred Revenue"): 0},
			cash={SALES: 0, acc("Deferred Revenue"): 0, DEBTORS: 0},
		)
		self.assert_invariants("2026-04-30")

	def test_cb10_return_and_refund_after_full_payment(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		pay(invoice, "2026-03-10")
		credit_note = make_return(invoice, "2026-04-01", 100)
		refund = get_payment_entry("Sales Invoice", credit_note.name, bank_account=BANK)
		refund.update(
			{"posting_date": "2026-04-05", "reference_no": "REFUND", "reference_date": "2026-04-05"}
		)
		save(refund, submit=True)
		self.assert_balances("2026-03-31", from_date="2026-03-01", accrual={SALES: -100}, cash={SALES: -100})
		# The refund reduces the income on the refund date.
		self.assert_balances("2026-04-30", from_date="2026-04-01", accrual={SALES: 100}, cash={SALES: 100})
		self.assert_invariants("2026-04-30", fully_paid=True)

	def test_cb11_write_off_by_journal_entry(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		make_journal_entry(
			"2026-06-01",
			[
				{"account": WRITE_OFF, "debit": 110},
				{
					"account": DEBTORS,
					"credit": 110,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
			],
			voucher_type="Write Off Entry",
		)
		# Section 6.5 example: income 0, bad debt expense 10 (the tax not collected), receivable 0.
		self.assert_balances(
			"2026-06-30",
			accrual={SALES: -100, WRITE_OFF: 110, DEBTORS: 0},
			cash={SALES: 0, WRITE_OFF: 10, DEBTORS: 0, TAX: -10},
		)

	def make_pos_invoice_with_change_and_write_off(self):
		invoice = make_sales_invoice(
			"2026-03-01",
			[line(100)],
			taxes=[(TAX, 10)],
			is_pos=1,
			submit=False,
			payments=[{"mode_of_payment": "Cash", "account": CASH_ACCOUNT, "amount": 115}],
			write_off_amount=5,
			write_off_account=WRITE_OFF,
			write_off_cost_center=MAIN_CC,
			account_for_change_amount=CASH_ACCOUNT,
		)
		# The cashier gives 10 in change and writes off 5: 115 - 10 + 5 = 110.
		invoice.flags.keep_change_amount = True
		invoice.change_amount = invoice.base_change_amount = 10
		invoice.save()
		self.assertEqual((invoice.change_amount, invoice.outstanding_amount), (10, 0))
		invoice.submit()
		# c = 100 / 110. Cash 105 recognises 95.45. The write-off of 5 removes 4.55 of its expense.
		self.assert_balances(
			"2026-03-31",
			accrual={SALES: -100, WRITE_OFF: 5, TAX: -10, CASH_ACCOUNT: 105, DEBTORS: 0},
			cash={SALES: -95.45, WRITE_OFF: 0.45, TAX: -10, CASH_ACCOUNT: 105, DEBTORS: 0},
		)
		return invoice

	def test_cb12_pos_invoice_with_change_and_write_off(self):
		with change_settings("POS Settings", {"post_change_gl_entries": 0}):
			self.make_pos_invoice_with_change_and_write_off()

	def test_cb12_pos_invoice_with_ledger_entries_for_change(self):
		with change_settings("POS Settings", {"post_change_gl_entries": 1}):
			invoice = self.make_pos_invoice_with_change_and_write_off()
		change_rows = frappe.get_all(
			"GL Entry", filters={"voucher_no": invoice.name, "account": DEBTORS, "debit": 10}, pluck="name"
		)
		self.assertTrue(change_rows, "the change has its own party row")
		self.assertEqual(self.exception_reasons(), {})

	def test_manual_credit_note_journal_entry_is_non_cash(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		make_journal_entry(
			"2026-04-01",
			[
				{"account": SERVICE, "debit": 110},
				{
					"account": DEBTORS,
					"credit": 110,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
			],
			voucher_type="Credit Note",
		)
		# All other rows are P&L, so the settlement is non-cash (rule 3), whatever the type says.
		self.assert_balances("2026-04-30", accrual={SALES: -100, SERVICE: 110}, cash={SALES: 0, SERVICE: 10})

	def test_cb15_payment_with_bank_charge_and_discount(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		payment = get_payment_entry("Sales Invoice", invoice.name, bank_account=BANK)
		payment.update({"posting_date": "2026-04-10", "reference_no": "P1", "reference_date": "2026-04-10"})
		payment.paid_amount = payment.received_amount = 95
		for account, amount in ((acc("Bank Charges"), 2), (acc("Sales Expenses"), 3)):
			payment.append("deductions", {"account": account, "cost_center": MAIN_CC, "amount": amount})
		save(payment, submit=True)
		# The deductions stay as posted. The invoice is settled in full by the payment.
		balances = {SALES: -100, acc("Bank Charges"): 2, acc("Sales Expenses"): 3, BANK: 95, DEBTORS: 0}
		self.assert_balances("2026-04-30", accrual=balances, cash=balances)
		self.assert_balances("2026-04-30", from_date="2026-04-01", accrual={SALES: 0}, cash={SALES: -100})

	def test_cb20_journal_entry_of_invoice_shape(self):
		journal = make_journal_entry(
			"2026-03-01",
			[
				{"account": DEBTORS, "debit": 100, "party_type": "Customer", "party": CUSTOMER},
				{"account": SERVICE, "credit": 100},
			],
		)
		make_advance(
			"Customer", CUSTOMER, "2026-04-10", 100, references=[("Journal Entry", journal.name, 100)]
		)
		self.assert_balances("2026-03-31", from_date="2026-03-01", accrual={SERVICE: -100}, cash={SERVICE: 0})
		self.assert_balances("2026-04-30", from_date="2026-04-01", accrual={SERVICE: 0}, cash={SERVICE: -100})

	def test_cb20_journal_entry_with_two_parties_is_exception(self):
		journal = make_journal_entry(
			"2026-03-01",
			[
				{"account": DEBTORS, "debit": 50, "party_type": "Customer", "party": CUSTOMER},
				{"account": DEBTORS, "debit": 50, "party_type": "Customer", "party": CUSTOMER_2},
				{"account": SERVICE, "credit": 100},
			],
		)
		self.assertEqual(self.exception_reasons(), {journal.name: "multiple parties"})
		self.assert_balances("2026-03-31", accrual={SERVICE: -100}, cash={SERVICE: -100})

	def test_cb23_invoice_discounting(self):
		accounts = {}
		for name, account_type, parent in (
			("AR Credit", "Receivable", "Accounts Receivable"),
			("AR Discounted", "Receivable", "Accounts Receivable"),
			("AR Unpaid", "Receivable", "Accounts Receivable"),
			("Short Term Loan", None, "Loans (Liabilities)"),
		):
			doc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": name,
					"parent_account": acc(parent),
					"company": US_COMPANY,
					"account_type": account_type,
				}
			).insert()
			accounts[name] = doc.name
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		discounting = frappe.get_doc(
			{
				"doctype": "Invoice Discounting",
				"company": US_COMPANY,
				"posting_date": "2026-03-05",
				"loan_start_date": "2026-03-05",
				"loan_period": 30,
				"bank_account": BANK,
				"bank_charges_account": acc("Bank Charges"),
				"short_term_loan": accounts["Short Term Loan"],
				"accounts_receivable_credit": accounts["AR Credit"],
				"accounts_receivable_discounted": accounts["AR Discounted"],
				"accounts_receivable_unpaid": accounts["AR Unpaid"],
				"invoices": [{"sales_invoice": invoice.name}],
			}
		)
		save(discounting, submit=True)
		disbursement = discounting.create_disbursement_entry()
		disbursement.posting_date = "2026-03-05"
		save(disbursement, submit=True)
		# Discounting moves the receivable to another account. It is not a settlement.
		self.assert_balances("2026-03-31", accrual={SALES: -100}, cash={SALES: 0})
		# ERPNext pays a discounted invoice with a Journal Entry on the discounted account.
		payment = frappe.get_doc(get_payment_entry_against_invoice("Sales Invoice", invoice.name))
		payment.update({"posting_date": "2026-04-10", "cheque_no": "P1", "cheque_date": "2026-04-10"})
		save(payment, submit=True)
		self.assert_balances("2026-04-30", from_date="2026-04-01", accrual={SALES: 0}, cash={SALES: -100})

	def test_cb24_unreconcile_and_cancel_of_payment(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		payment = pay(invoice, "2026-03-10")
		self.assert_balances("2026-03-31", cash={SALES: -100, UNAPPLIED: 0})

		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": US_COMPANY,
				"voucher_type": "Payment Entry",
				"voucher_no": payment.name,
			}
		)
		unreconcile.add_references()
		save(unreconcile, submit=True)
		# The payment is now unapplied: income on the unapplied account, not on the invoice lines.
		self.assert_balances("2026-03-31", accrual={DEBTORS: 0}, cash={SALES: 0, UNAPPLIED: -100})

		payment.reload()
		payment.cancel()
		self.assert_balances("2026-03-31", accrual={SALES: -100, DEBTORS: 100}, cash={SALES: 0, UNAPPLIED: 0})
		self.assertEqual(self.exception_reasons(), {})
