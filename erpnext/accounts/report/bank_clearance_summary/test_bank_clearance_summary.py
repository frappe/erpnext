# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
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
