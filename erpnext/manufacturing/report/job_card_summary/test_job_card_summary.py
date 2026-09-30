# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, today

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.job_card_summary.job_card_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestJobCardSummary(ERPNextTestSuite):
	def setUp(self):
		# `_Test FG Item 2` has a default active BOM with operations, so submitting a
		# Work Order for it auto-creates Job Cards (one per operation).
		self.work_order = make_wo_order_test_record(item="_Test FG Item 2", qty=2)
		self.job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name},
			fields=["name", "operation", "workstation", "production_item", "status"],
		)

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 1),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def rows_for_work_order(self, rows):
		return [row for row in rows if row.get("work_order") == self.work_order.name]

	def test_job_cards_are_listed(self):
		self.assertTrue(self.job_cards, "Work Order did not produce any Job Cards")

		rows = self.rows_for_work_order(self.run_report())
		self.assertEqual(len(rows), len(self.job_cards))

		reported_names = {row.get("name") for row in rows}
		self.assertEqual(reported_names, {jc.name for jc in self.job_cards})

		# Fresh (unsubmitted) job cards are reported as Open, and each row carries the
		# operation / workstation / production item pulled from the Job Card.
		for jc in self.job_cards:
			row = next(row for row in rows if row.get("name") == jc.name)
			self.assertEqual(row.get("status"), "Open")
			self.assertEqual(row.get("operation"), jc.operation)
			self.assertEqual(row.get("workstation"), jc.workstation)
			self.assertEqual(row.get("production_item"), jc.production_item)

	def test_operation_filter_scopes_rows(self):
		self.assertTrue(self.job_cards, "Work Order did not produce any Job Cards")
		operation = self.job_cards[0].operation
		matching = {jc.name for jc in self.job_cards if jc.operation == operation}

		rows = self.rows_for_work_order(self.run_report(operation=operation))
		self.assertEqual({row.get("name") for row in rows}, matching)

	def test_status_filter(self):
		self.assertTrue(self.job_cards, "Work Order did not produce any Job Cards")

		# The status filter matches the Job Card's *stored* status, so derive the
		# expected set from that rather than assuming fresh cards are literally "Open".
		stored_status = self.job_cards[0].status
		expected = {jc.name for jc in self.job_cards if jc.status == stored_status}

		rows = self.rows_for_work_order(self.run_report(status=stored_status))
		self.assertEqual({row.get("name") for row in rows}, expected)
		# any non-completed card is displayed as "Open" regardless of its stored status
		for row in rows:
			self.assertEqual(row.get("status"), "Open")

		# None of the freshly created job cards are Completed yet.
		completed_rows = self.rows_for_work_order(self.run_report(status="Completed"))
		self.assertEqual(completed_rows, [])

	def test_date_filter_excludes_out_of_range(self):
		# Job Card posting_date defaults to today; a past-only window should exclude them.
		rows = self.rows_for_work_order(
			self.run_report(from_date=add_days(today(), -10), to_date=add_days(today(), -5))
		)
		self.assertEqual(rows, [])
