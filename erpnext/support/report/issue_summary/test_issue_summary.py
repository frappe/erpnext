# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import add_days, today

from erpnext.support.report.issue_summary.issue_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestIssueSummary(ERPNextTestSuite):
	def test_count_grouped_by_issue_priority(self):
		# Unique Issue Priority so this group is isolated from any pre-existing data.
		priority = "__Test Issue Summary Priority"
		if not frappe.db.exists("Issue Priority", priority):
			frappe.get_doc({"doctype": "Issue Priority", "name": priority}).insert()

		opening_date = today()
		for subject in ("__Test Issue Summary A", "__Test Issue Summary B"):
			frappe.get_doc(
				{
					"doctype": "Issue",
					"subject": subject,
					"priority": priority,
					"status": "Open",
					"opening_date": opening_date,
				}
			).insert()

		filters = frappe._dict(
			{
				"based_on": "Issue Priority",
				"from_date": add_days(opening_date, -1),
				"to_date": add_days(opening_date, 1),
			}
		)

		columns, data, _msg, _chart, _summary = execute(filters)

		# get_rows() emits one row per group keyed on "priority" for based_on == "Issue Priority".
		seeded_row = next((row for row in data if row.get("priority") == priority), None)
		self.assertIsNotNone(
			seeded_row,
			f"expected a summary row for priority {priority!r}, got {[r.get('priority') for r in data]}",
		)

		# Two seeded Open issues -> total_issues == 2 and the "open" status bucket == 2.
		self.assertEqual(seeded_row["total_issues"], 2)
		self.assertEqual(seeded_row["open"], 2)

	def test_assignee_averages_skip_issues_without_the_metric(self):
		user = "test-issue-summary-agent@example.com"
		make_issue("__Test Issue Summary Answered", _assign=json.dumps([user]), first_response_time=3600)
		make_issue("__Test Issue Summary Waiting", _assign=json.dumps([user]))

		row = get_report_row("Assigned To", "user", user)
		self.assertEqual(row["total_issues"], 2)
		self.assertEqual(row["avg_first_response_time"], 3600)


def make_issue(subject: str, **values) -> str:
	"""Insert an open Issue opened today and set `values` on it directly."""
	issue = frappe.get_doc({"doctype": "Issue", "subject": subject, "opening_date": today()}).insert()
	if values:
		frappe.db.set_value("Issue", issue.name, values)
	return issue.name


def get_report_row(based_on: str, key: str, value: str, **filters) -> dict | None:
	filters = frappe._dict(
		based_on=based_on, from_date=add_days(today(), -1), to_date=add_days(today(), 1), **filters
	)
	data = execute(filters)[1]
	return next((row for row in data if row.get(key) == value), None)
