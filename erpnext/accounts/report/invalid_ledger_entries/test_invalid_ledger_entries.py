# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.invalid_ledger_entries.invalid_ledger_entries import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestInvalidLedgerEntries(ERPNextTestSuite):
	"""Tests for the Invalid Ledger Entries integrity report.

	The report flags vouchers that still have *active* ledger entries
	(GL Entry with is_cancelled=0 or Payment Ledger Entry with delinked=0)
	in the given period, but whose source voucher document is no longer
	submitted (docstatus != 1). Such orphaned ledgers indicate corruption.
	"""

	def setUp(self):
		self.company = "_Test Company"
		self.debit_account = "_Test Bank - _TC"
		self.credit_account = "_Test Cash - _TC"
		self.from_date = "2026-01-01"
		self.to_date = "2026-12-31"
		self.posting_date = "2026-06-01"

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": self.company,
				"from_date": self.from_date,
				"to_date": self.to_date,
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def make_submitted_jv(self):
		return make_journal_entry(
			self.debit_account,
			self.credit_account,
			amount=500,
			posting_date=self.posting_date,
			company=self.company,
			submit=True,
		)

	def test_healthy_voucher_not_flagged(self):
		"""A normal balanced, submitted Journal Entry must NOT be flagged."""
		jv = self.make_submitted_jv()

		# It genuinely posted active GL entries, so it is in scope of the scan.
		self.assertTrue(
			frappe.db.exists(
				"GL Entry",
				{"voucher_no": jv.name, "is_cancelled": 0, "company": self.company},
			)
		)

		flagged = {row.get("voucher_no") for row in self.run_report()}
		self.assertNotIn(jv.name, flagged)

	def test_orphaned_gl_entries_flagged(self):
		"""A voucher whose document was set non-submitted while its GL entries
		remain active (is_cancelled=0) must be flagged as invalid."""
		jv = self.make_submitted_jv()

		# Corrupt the state: mark the source document as cancelled (docstatus=2)
		# without cancelling/removing its GL Entries. This is the exact orphaned
		# ledger condition the report detects.
		frappe.db.set_value("Journal Entry", jv.name, "docstatus", 2, update_modified=False)

		data = self.run_report()

		matching = [
			row
			for row in data
			if row.get("voucher_no") == jv.name and row.get("voucher_type") == "Journal Entry"
		]
		self.assertEqual(len(matching), 1, "Orphaned voucher should be flagged exactly once")
		self.assertEqual(matching[0]["voucher_type"], "Journal Entry")
		self.assertEqual(matching[0]["voucher_no"], jv.name)

	def test_voucher_no_filter_scopes_scan(self):
		"""The voucher_no filter must restrict the scan to that voucher only."""
		orphan = self.make_submitted_jv()
		other = self.make_submitted_jv()
		frappe.db.set_value("Journal Entry", orphan.name, "docstatus", 2, update_modified=False)
		frappe.db.set_value("Journal Entry", other.name, "docstatus", 2, update_modified=False)

		flagged = {row.get("voucher_no") for row in self.run_report(voucher_no=orphan.name)}
		self.assertIn(orphan.name, flagged)
		self.assertNotIn(other.name, flagged)

	def test_account_filter_scopes_scan(self):
		"""The account filter (a MultiSelectList, so a list) must restrict the
		scan to vouchers touching one of the given accounts."""
		orphan = self.make_submitted_jv()
		frappe.db.set_value("Journal Entry", orphan.name, "docstatus", 2, update_modified=False)

		# Filtering on an account the voucher touches -> flagged.
		flagged = {row.get("voucher_no") for row in self.run_report(account=[self.debit_account])}
		self.assertIn(orphan.name, flagged)

		# Filtering on an unrelated account -> not in scope.
		unrelated = "Creditors - _TC"
		flagged = {row.get("voucher_no") for row in self.run_report(account=[unrelated])}
		self.assertNotIn(orphan.name, flagged)

	def test_account_filter_accepts_a_scalar(self):
		"""A scalar (non-list) account filter must not crash the query."""
		orphan = self.make_submitted_jv()
		frappe.db.set_value("Journal Entry", orphan.name, "docstatus", 2, update_modified=False)

		flagged = {row.get("voucher_no") for row in self.run_report(account=self.debit_account)}
		self.assertIn(orphan.name, flagged)

	def test_period_filter_excludes_out_of_range(self):
		"""Vouchers posted outside the from/to window must not be scanned."""
		orphan = self.make_submitted_jv()
		frappe.db.set_value("Journal Entry", orphan.name, "docstatus", 2, update_modified=False)

		flagged = {
			row.get("voucher_no") for row in self.run_report(from_date="2025-01-01", to_date="2025-12-31")
		}
		self.assertNotIn(orphan.name, flagged)

	def test_cancelled_gl_entries_not_flagged(self):
		"""If the ledger entries are properly cancelled (is_cancelled=1), the
		voucher is out of scope even when its document is non-submitted."""
		jv = self.make_submitted_jv()

		gle = qb.DocType("GL Entry")
		qb.update(gle).set(gle.is_cancelled, 1).where(gle.voucher_no == jv.name).run()
		frappe.db.set_value("Journal Entry", jv.name, "docstatus", 2, update_modified=False)

		flagged = {row.get("voucher_no") for row in self.run_report()}
		self.assertNotIn(jv.name, flagged)

	def test_missing_filters_raises(self):
		"""validate_filters must guard mandatory inputs."""
		self.assertRaises(frappe.ValidationError, execute, None)

		bad = frappe._dict({"from_date": self.from_date, "to_date": self.to_date})
		self.assertRaises(frappe.ValidationError, execute, bad)

		reversed_dates = frappe._dict(
			{"company": self.company, "from_date": self.to_date, "to_date": self.from_date}
		)
		self.assertRaises(frappe.ValidationError, execute, reversed_dates)
