# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Phase 7: the Journal Entry field cash_basis_treatment removes a "mixed settlement" exception."""

import frappe

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import CUSTOMER, acc
from erpnext.accounts.cash_basis.tests.vouchers import BANK, line, make_journal_entry, make_sales_invoice

SALES = acc("Sales")
DEBTORS = acc("Debtors")
TAX = acc("ST 6%")
WRITE_OFF = acc("Write Off")


class TestCashBasisJournalTreatment(CashBasisTestCase):
	def settle(self, invoice, amount, other_rows):
		return make_journal_entry(
			"2026-04-10",
			[
				{
					"account": DEBTORS,
					"credit": amount,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
				*other_rows,
			],
		)

	def set_treatment(self, journal, treatment):
		# The user sets the field on the submitted entry. The ledger does not change.
		gl_before = frappe.get_all(
			"GL Entry", filters={"voucher_no": journal.name}, fields=["account", "debit", "credit"]
		)
		journal.reload()
		journal.cash_basis_treatment = treatment
		journal.save()
		gl_after = frappe.get_all(
			"GL Entry", filters={"voucher_no": journal.name}, fields=["account", "debit", "credit"]
		)
		self.assertEqual(gl_before, gl_after)

	def test_write_off_with_tax_reversal_as_non_cash_adjustment(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		journal = self.settle(
			invoice, 110, [{"account": WRITE_OFF, "debit": 100}, {"account": TAX, "debit": 10}]
		)
		# Automatic: a P&L row and a balance sheet row, so an exception, treated as cash.
		self.assertEqual(self.exception_reasons(), {journal.name: "mixed settlement"})
		self.assert_balances("2026-04-30", cash={SALES: -100, WRITE_OFF: 100})
		self.set_treatment(journal, "Non-cash Adjustment")
		self.assertEqual(self.exception_reasons(), {})
		# No cash: no income, and the write-off of the income is removed. The tax reversal stays.
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: -100, WRITE_OFF: 100, TAX: 0, DEBTORS: 0},
			cash={SALES: 0, WRITE_OFF: 0, TAX: 0, DEBTORS: 0},
		)
		self.assert_invariants("2026-04-30")

	def test_payment_with_a_write_off_as_cash_settlement(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		journal = self.settle(
			invoice, 100, [{"account": BANK, "debit": 90}, {"account": WRITE_OFF, "debit": 10}]
		)
		self.assertEqual(self.exception_reasons(), {journal.name: "mixed settlement"})
		self.set_treatment(journal, "Cash Settlement")
		self.assertEqual(self.exception_reasons(), {})
		# All of the invoice is settled as cash. The write-off row stays as posted.
		self.assert_balances(
			"2026-04-30",
			accrual={SALES: -100, WRITE_OFF: 10},
			cash={SALES: -100, WRITE_OFF: 10, DEBTORS: 0},
		)
		self.assert_invariants("2026-04-30", fully_paid=True)

	def test_default_is_automatic(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		journal = self.settle(invoice, 100, [{"account": BANK, "debit": 100}])
		self.assertEqual(journal.cash_basis_treatment, "Automatic")
		self.assert_balances("2026-04-30", cash={SALES: -100, DEBTORS: 0})

	def test_non_cash_adjustment_with_a_bank_row_is_refused(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		journal = self.settle(
			invoice, 100, [{"account": BANK, "debit": 90}, {"account": WRITE_OFF, "debit": 10}]
		)
		journal.reload()
		journal.cash_basis_treatment = "Non-cash Adjustment"
		self.assertRaisesRegex(frappe.ValidationError, "Bank or Cash row", journal.save)
		# An entry that has the value from before the check keeps the automatic class.
		frappe.db.set_value("Journal Entry", journal.name, "cash_basis_treatment", "Non-cash Adjustment")
		self.assertEqual(self.exception_reasons(), {journal.name: "mixed settlement"})
		self.assert_balances("2026-04-30", cash={SALES: -100, WRITE_OFF: 10})

	def test_change_in_a_frozen_period_is_refused(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		journal = self.settle(
			invoice, 110, [{"account": WRITE_OFF, "debit": 100}, {"account": TAX, "debit": 10}]
		)
		frappe.db.set_value("Company", journal.company, "accounts_frozen_till_date", "2026-04-30")
		journal.reload()
		journal.cash_basis_treatment = "Non-cash Adjustment"
		self.assertRaisesRegex(frappe.ValidationError, "not authorized", journal.save)
		self.assertEqual(
			frappe.db.get_value("Journal Entry", journal.name, "cash_basis_treatment"), "Automatic"
		)

	def test_journal_entry_with_only_party_rows_stays_automatic(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		journal = self.settle(
			invoice, 100, [{"account": DEBTORS, "debit": 100, "party_type": "Customer", "party": CUSTOMER}]
		)
		journal.reload()
		for treatment in ("Cash Settlement", "Non-cash Adjustment"):
			journal.cash_basis_treatment = treatment
			self.assertRaisesRegex(frappe.ValidationError, "only party rows", journal.save)
			journal.reload()
		# An entry with the value from before the check keeps rule 4: a link, not cash.
		frappe.db.set_value("Journal Entry", journal.name, "cash_basis_treatment", "Cash Settlement")
		self.assert_balances("2026-04-30", cash={SALES: 0})

	def test_draft_with_a_bank_row_is_refused(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)])
		journal = make_journal_entry(
			"2026-04-10",
			[
				{
					"account": DEBTORS,
					"credit": 100,
					"party_type": "Customer",
					"party": CUSTOMER,
					"reference_type": "Sales Invoice",
					"reference_name": invoice.name,
				},
				{"account": BANK, "debit": 100},
			],
			submit=False,
		)
		journal.cash_basis_treatment = "Non-cash Adjustment"
		self.assertRaisesRegex(frappe.ValidationError, "Bank or Cash row", journal.save)

	def test_frozen_entries_role_may_change_the_treatment(self):
		invoice = make_sales_invoice("2026-03-01", [line(100)], taxes=[(TAX, 10)])
		journal = self.settle(
			invoice, 110, [{"account": WRITE_OFF, "debit": 100}, {"account": TAX, "debit": 10}]
		)
		frappe.db.set_value(
			"Company",
			journal.company,
			{
				"accounts_frozen_till_date": "2026-04-30",
				"role_allowed_for_frozen_entries": "Accounts Manager",
			},
		)
		user = "test-cash-basis-frozen@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Cash Basis Frozen",
					"roles": [{"role": "Accounts User"}, {"role": "Accounts Manager"}],
				}
			).insert()
		with self.set_user(user):
			journal.reload()
			journal.cash_basis_treatment = "Non-cash Adjustment"
			journal.save()
		self.assertEqual(
			frappe.db.get_value("Journal Entry", journal.name, "cash_basis_treatment"), "Non-cash Adjustment"
		)
