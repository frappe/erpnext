# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.report.bank_clearance_summary.bank_clearance_summary import execute
from erpnext.tests.utils import ERPNextTestSuite

BANK_ACCOUNT = "_Test Bank - _TC"


class TestBankClearanceSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"account": BANK_ACCOUNT,
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def find_row(self, data, payment_entry):
		for row in data:
			if row[1] == payment_entry:
				return row
		return None

	def test_uncleared_then_cleared_journal_entry(self):
		je = make_journal_entry(BANK_ACCOUNT, "Sales - _TC", 5000, submit=True, posting_date="2026-06-01")

		# Uncleared: the bank row appears with the debit amount and no clearance date
		row = self.find_row(self.run_report(), je.name)
		self.assertIsNotNone(row, "Journal Entry not listed in Bank Clearance Summary")
		self.assertEqual(row[0], "Journal Entry")
		self.assertEqual(frappe.utils.getdate(row[2]), frappe.utils.getdate("2026-06-01"))
		self.assertIsNone(row[4])  # clearance_date empty -> uncleared
		self.assertEqual(row[5], "Sales - _TC")  # against account
		self.assertEqual(row[6], 5000)  # debit - credit on the bank account

		# Cleared: set the clearance date on the Journal Entry and re-run
		frappe.db.set_value("Journal Entry", je.name, "clearance_date", "2026-06-05")

		row = self.find_row(self.run_report(), je.name)
		self.assertIsNotNone(row)
		self.assertEqual(frappe.utils.getdate(row[4]), frappe.utils.getdate("2026-06-05"))
		self.assertEqual(row[6], 5000)

	def test_date_filter_excludes_out_of_range_entries(self):
		je = make_journal_entry(BANK_ACCOUNT, "Sales - _TC", 3000, submit=True, posting_date="2026-06-10")

		# Within range: present
		self.assertIsNotNone(self.find_row(self.run_report(), je.name))

		# Window entirely after the posting date (from_date lower bound): excluded
		after = self.run_report(from_date="2026-07-01", to_date="2026-12-31")
		self.assertIsNone(self.find_row(after, je.name))

		# Window ending before the posting date (to_date upper bound): excluded
		before = self.run_report(from_date="2026-01-01", to_date="2026-06-09")
		self.assertIsNone(self.find_row(before, je.name))

	def test_payment_entry_amount_after_taxes(self):
		receipt = self.make_taxed_payment_entry(
			"Receive",
			1000,
			{"rate": 10, "add_deduct_tax": "Deduct"},
			party_type="Customer",
			party="_Test Customer",
			paid_from="Debtors - _TC",
		)
		payment = self.make_taxed_payment_entry("Pay", 1180, {"rate": 18, "included_in_paid_amount": 1})

		data = self.run_report()
		self.assertEqual(self.find_row(data, receipt.name)[6], 900)
		self.assertEqual(self.find_row(data, payment.name)[6], -1180)

	def make_taxed_payment_entry(self, payment_type: str, amount: float, tax: dict, **party):
		bank_field = "paid_to" if payment_type == "Receive" else "paid_from"
		party[bank_field] = BANK_ACCOUNT
		payment_entry = create_payment_entry(payment_type=payment_type, paid_amount=amount, **party)
		tax.setdefault("add_deduct_tax", "Add")
		payment_entry.append(
			"taxes",
			{
				"account_head": "_Test Account Service Tax - _TC",
				"charge_type": "On Paid Amount",
				"description": "Service Tax",
				**tax,
			},
		)
		payment_entry.save()
		payment_entry.submit()
		return payment_entry
