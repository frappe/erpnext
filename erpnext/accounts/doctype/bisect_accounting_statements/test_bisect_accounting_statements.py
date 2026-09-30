# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime

import frappe
from frappe.utils import getdate

from erpnext.tests.utils import ERPNextTestSuite


class TestBisectAccountingStatements(ERPNextTestSuite):
	"""The tool bisects a date range into a tree of Bisect Nodes down to single days.
	These cover the date validation and that the bisection cleanly partitions the range."""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Bisect Nodes")

	def _leaf_days(self):
		leaves = frappe.get_all(
			"Bisect Nodes",
			filters={"left_child": ["is", "not set"]},
			fields=["period_from_date", "period_to_date"],
		)
		# every leaf spans a single day
		for leaf in leaves:
			self.assertEqual(getdate(leaf.period_from_date), getdate(leaf.period_to_date))
		return sorted(getdate(leaf.period_from_date) for leaf in leaves)

	def test_validate_dates_rejects_reversed_range(self):
		doc = frappe.new_doc("Bisect Accounting Statements")
		doc.from_date = "2026-01-08"
		doc.to_date = "2026-01-01"
		self.assertRaises(frappe.ValidationError, doc.validate)

	def test_bfs_partitions_range_into_single_days(self):
		doc = frappe.new_doc("Bisect Accounting Statements")
		doc.bfs(datetime.datetime(2026, 1, 1), datetime.datetime(2026, 1, 8))

		# the 8-day span Jan 1..Jan 8 becomes exactly 8 contiguous single-day leaves
		self.assertEqual(self._leaf_days(), [getdate(f"2026-01-0{n}") for n in range(1, 9)])

	def test_dfs_produces_the_same_partition_as_bfs(self):
		doc = frappe.new_doc("Bisect Accounting Statements")
		doc.dfs(datetime.datetime(2026, 1, 1), datetime.datetime(2026, 1, 8))
		self.assertEqual(self._leaf_days(), [getdate(f"2026-01-0{n}") for n in range(1, 9)])
