# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.support.report.issue_summary.issue_summary import execute


class TestIssueSummary(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

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
