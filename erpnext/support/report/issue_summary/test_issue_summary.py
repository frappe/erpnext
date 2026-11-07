# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.support.doctype.issue.test_issue import create_customer
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

	def test_counts_only_issues_the_user_may_read(self):
		from frappe.permissions import add_user_permission

		issue_type = "__Test Issue Summary Type"
		if not frappe.db.exists("Issue Type", issue_type):
			frappe.get_doc({"doctype": "Issue Type", "name": issue_type}).insert()
		for customer in ("__Test Issue Summary Customer", "__Test Issue Summary Customer 1"):
			create_customer(customer, "_Test SLA Customer Group", "__Test SLA Territory")
			make_issue(f"__Test Issue Summary {customer}", customer=customer, issue_type=issue_type)

		user = "test-issue-summary-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Support",
					"send_welcome_email": 0,
					"roles": [{"role": "Support Team"}],
				}
			).insert(ignore_permissions=True)
		add_user_permission("Customer", "__Test Issue Summary Customer", user)

		with self.set_user(user):
			row = get_report_row("Issue Type", "issue_type", issue_type)
		self.assertEqual(row["total_issues"], 1)


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
