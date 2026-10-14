# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_days, today

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.job_card_summary.job_card_summary import execute, get_chart_data
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
		job_card = self.job_cards[0].name
		frappe.db.set_value("Job Card", job_card, "status", "Work In Progress")
		rows = self.run_report(status="Work In Progress", work_order=[self.work_order.name])
		self.assertEqual([(row.name, row.status) for row in rows], [(job_card, "Work In Progress")])

	def test_chart_respects_job_card_permissions(self):
		user = create_user("job-card-summary@example.com", "Manufacturing User")
		workstation = frappe.get_doc(
			doctype="Workstation", workstation_name="_Test Summary Workstation"
		).insert()
		add_user_permission("Workstation", workstation.name, user.name)
		filters = frappe._dict(
			company="_Test Company",
			from_date=today(),
			to_date=today(),
			work_order=[self.work_order.name],
		)
		for expected_count in (0, 1):
			if expected_count:
				frappe.db.set_value("Job Card", self.job_cards[0].name, "workstation", workstation.name)
			with self.set_user(user.name):
				columns, rows, message, chart = execute(filters)
			self.assertEqual(len(rows), expected_count)
			self.assertEqual(
				sum(value or 0 for dataset in chart["data"]["datasets"] for value in dataset["values"]),
				expected_count,
			)
		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, execute, filters)

	def test_chart_includes_period_boundaries_and_empty_months(self):
		filters = frappe._dict(from_date="2026-01-01", to_date="2026-02-28")
		cards = [
			frappe._dict(posting_date="2026-01-01", status="Work In Progress"),
			frappe._dict(posting_date="2026-01-31", status="Completed"),
		]
		chart = get_chart_data(cards, filters)
		self.assertEqual([row["values"] for row in chart["data"]["datasets"]], [[1, 0], [1, 0]])

	def test_date_filter_excludes_out_of_range(self):
		# Job Card posting_date defaults to today; a past-only window should exclude them.
		rows = self.rows_for_work_order(
			self.run_report(from_date=add_days(today(), -10), to_date=add_days(today(), -5))
		)
		self.assertEqual(rows, [])
