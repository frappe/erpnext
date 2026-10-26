# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.voucher_wise_balance.voucher_wise_balance import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestVoucherWiseBalance(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def find_row(self, data, voucher_no):
		for row in data:
			if row.get("voucher_no") == voucher_no:
				return row
		return None

	def test_balanced_voucher_not_flagged(self):
		jv = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)

		data = self.run_report()
		self.assertIsNone(
			self.find_row(data, jv.name),
			msg="A balanced voucher (debit == credit) must not be flagged.",
		)

	def test_imbalanced_voucher_flagged(self):
		jv = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)

		# Tamper one GL Entry: drop the debit side so debit != credit for this voucher.
		gle_name = frappe.db.get_value(
			"GL Entry",
			{"voucher_no": jv.name, "is_cancelled": 0, "debit": [">", 0]},
			"name",
		)
		self.assertIsNotNone(gle_name, msg="Expected a debit GL Entry for the journal entry.")
		frappe.db.set_value("GL Entry", gle_name, {"debit": 400, "debit_in_account_currency": 400})

		data = self.run_report()
		row = self.find_row(data, jv.name)
		self.assertIsNotNone(row, msg="An imbalanced voucher must be flagged by the report.")

		self.assertEqual(row.get("voucher_type"), "Journal Entry")
		self.assertEqual(row.get("credit"), 1000)
		self.assertEqual(row.get("debit"), 400)
		self.assertNotEqual(
			row.get("debit"), row.get("credit"), msg="Flagged rows must have debit != credit."
		)

	def test_company_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict(from_date="2026-01-01"))

	def test_same_named_vouchers_of_different_types_reported_separately(self):
		jv = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)
		other = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)
		gle = frappe.qb.DocType("GL Entry")
		frappe.qb.update(gle).set(gle.voucher_type, "Sales Invoice").set(gle.voucher_no, jv.name).where(
			gle.voucher_no == other.name
		).run()
		frappe.db.set_value(
			"GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name, "debit": [">", 0]},
			"debit",
			1500,
		)
		frappe.db.set_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": jv.name, "credit": [">", 0]},
			"credit",
			1500,
		)

		rows = {
			(row.voucher_type, row.debit, row.credit)
			for row in self.run_report()
			if row.voucher_no == jv.name
		}
		self.assertEqual(rows, {("Journal Entry", 1500, 1000), ("Sales Invoice", 1000, 1500)})

	def test_balanced_vouchers_are_not_fetched(self):
		balanced = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)
		unbalanced = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)
		frappe.db.set_value("GL Entry", {"voucher_no": unbalanced.name, "debit": [">", 0]}, "debit", 400)

		fetched = []
		run_sql = frappe.db.sql

		def capture_rows(*args, **kwargs):
			rows = run_sql(*args, **kwargs)
			fetched.extend(row.get("voucher_no") for row in rows if isinstance(row, dict))
			return rows

		with patch.object(frappe.db, "sql", side_effect=capture_rows):
			data = self.run_report()

		self.assertNotIn(balanced.name, fetched)
		self.assertIn(unbalanced.name, fetched)
		self.assertEqual({row.voucher_no for row in data}, set(fetched))
