# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import nowtime, random_string

from erpnext.tests.utils import ERPNextTestSuite


class TestBulkTransactionLog(ERPNextTestSuite):
	def _make_log_doc(self, date):
		# "Bulk Transaction Log" is a virtual doctype named by date; build the doc
		# in-memory and drive load_from_db() directly to exercise the converted query.
		doc = frappe.new_doc("Bulk Transaction Log")
		doc.name = date
		return doc

	def _insert_detail(self, date, status="Success"):
		detail = frappe.get_doc(
			{
				"doctype": "Bulk Transaction Log Detail",
				"from_doctype": "Sales Order",
				"to_doctype": "Sales Invoice",
				"transaction_name": "_Test BTLD " + random_string(8),
				"date": date,
				"time": nowtime(),
				"transaction_status": status,
			}
		)
		# transaction_name is a Dynamic Link (options=from_doctype); the converted
		# query never reads it, so skip link validation rather than create real txns.
		detail.insert(ignore_permissions=True, ignore_links=True)
		return detail

	def test_load_raises_when_no_detail_rows(self):
		# A date with zero Bulk Transaction Log Detail rows must not resolve to a log.
		date = "2024-01-01"
		self.assertFalse(
			frappe.db.exists("Bulk Transaction Log Detail", {"date": date}),
			"precondition: no detail rows for this date",
		)

		doc = self._make_log_doc(date)
		self.assertRaises(frappe.DoesNotExistError, doc.load_from_db)

	def test_load_succeeds_and_aggregates_after_detail_inserted(self):
		date = "2024-02-02"

		# Initially absent -> load_from_db must raise.
		self.assertRaises(frappe.DoesNotExistError, self._make_log_doc(date).load_from_db)

		# Insert detail rows for this date: 2 succeeded, 1 failed.
		self._insert_detail(date, "Success")
		self._insert_detail(date, "Success")
		self._insert_detail(date, "Failed")

		# Now the exists() check passes and load_from_db() populates aggregates.
		doc = self._make_log_doc(date)
		doc.load_from_db()

		self.assertEqual(doc.date, date)
		self.assertEqual(doc.succeeded, 2)
		self.assertEqual(doc.failed, 1)
		self.assertEqual(doc.log_entries, 3)

	def test_load_isolated_per_date(self):
		# Detail rows on a different date must not satisfy the lookup for our date.
		other_date = "2024-03-03"
		self._insert_detail(other_date, "Success")

		target_date = "2024-04-04"
		self.assertFalse(
			frappe.db.exists("Bulk Transaction Log Detail", {"date": target_date}),
			"target date has no rows; rows on another date must not leak in",
		)
		self.assertRaises(frappe.DoesNotExistError, self._make_log_doc(target_date).load_from_db)
