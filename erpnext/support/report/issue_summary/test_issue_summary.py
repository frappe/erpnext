# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.support.report.issue_summary.issue_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


def create_issue_type(issue_type):
	if not frappe.db.exists("Issue Type", issue_type):
		frappe.get_doc({"doctype": "Issue Type", "name": issue_type}).insert(ignore_permissions=True)


def create_issue_priority(priority):
	if not frappe.db.exists("Issue Priority", priority):
		frappe.get_doc({"doctype": "Issue Priority", "name": priority}).insert(ignore_permissions=True)


def create_customer(customer_name):
	if not frappe.db.exists("Customer", customer_name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
			}
		).insert(ignore_permissions=True)
	return customer_name


def create_user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	return email


def make_issue(
	subject,
	customer=None,
	issue_type=None,
	priority=None,
	status="Open",
	agreement_status=None,
	opening_date=None,
):
	"""Create an Issue directly, bypassing SLA machinery, with a known opening_date."""
	if issue_type:
		create_issue_type(issue_type)
	if priority:
		create_issue_priority(priority)

	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"subject": subject,
			"customer": customer,
			"issue_type": issue_type,
			"priority": priority,
			"status": status,
			"raised_by": "reporter@example.com",
			"description": subject,
			"opening_date": opening_date or nowdate(),
		}
	).insert(ignore_permissions=True)

	# status/opening_date can be reset by defaults on insert; force the values we test against
	frappe.db.set_value(
		"Issue",
		issue.name,
		{"status": status, "opening_date": opening_date or nowdate()},
		update_modified=False,
	)
	if agreement_status:
		frappe.db.set_value("Issue", issue.name, "agreement_status", agreement_status, update_modified=False)

	return frappe.get_doc("Issue", issue.name)


class TestIssueSummary(ERPNextTestSuite):
	def setUp(self):
		self.today = getdate(nowdate())
		self.from_date = add_days(self.today, -5)
		self.to_date = add_days(self.today, 5)

		self.customer_a = create_customer("_Test Issue Summary Customer A")
		self.customer_b = create_customer("_Test Issue Summary Customer B")
		self.assignee = create_user("issue_summary_assignee@example.com")

		# Customer A: 2 Bug / High issues (1 Open, 1 Closed)
		self.issue_a1 = make_issue(
			"ISmA1",
			customer=self.customer_a,
			issue_type="_Test Bug",
			priority="_Test High",
			status="Open",
			agreement_status="Resolution Due",
			opening_date=self.today,
		)
		self.issue_a2 = make_issue(
			"ISmA2",
			customer=self.customer_a,
			issue_type="_Test Bug",
			priority="_Test High",
			status="Closed",
			agreement_status="Fulfilled",
			opening_date=self.today,
		)
		# Customer B: 1 Question / Low issue (Resolved)
		self.issue_b1 = make_issue(
			"ISmB1",
			customer=self.customer_b,
			issue_type="_Test Question",
			priority="_Test Low",
			status="Resolved",
			agreement_status="Fulfilled",
			opening_date=self.today,
		)

		# Assign one issue so _assign JSON is populated for the "Assigned To" grouping
		from frappe.desk.form.assign_to import add as add_assignment

		add_assignment(
			{
				"doctype": "Issue",
				"name": self.issue_a1.name,
				"assign_to": [self.assignee],
			}
		)

	def base_filters(self, based_on):
		return frappe._dict(
			{
				"based_on": based_on,
				"from_date": self.from_date,
				"to_date": self.to_date,
			}
		)

	def get_rows_by_key(self, data, key):
		"""Return {entity_value: row} for the grouping key, sorted is irrelevant for a dict lookup."""
		return {row.get(key): row for row in data}

	def test_execute_returns_full_tuple(self):
		columns, data, message, chart, report_summary = execute(self.base_filters("Customer"))

		self.assertTrue(columns)
		self.assertIsInstance(data, list)
		self.assertIsNone(message)
		self.assertIn("data", chart)
		self.assertIsInstance(report_summary, list)

		# columns must include the grouping column plus every status + total
		fieldnames = [c["fieldname"] for c in columns]
		self.assertEqual(fieldnames[0], "customer")
		for status_field in ("open", "replied", "on_hold", "resolved", "closed", "total_issues"):
			self.assertIn(status_field, fieldnames)

	def test_based_on_customer_counts(self):
		columns, data, *_ = execute(self.base_filters("Customer"))
		rows = self.get_rows_by_key(data, "customer")

		self.assertIn(self.customer_a, rows)
		self.assertIn(self.customer_b, rows)

		row_a = rows[self.customer_a]
		self.assertEqual(row_a["total_issues"], 2)
		self.assertEqual(row_a["open"], 1)
		self.assertEqual(row_a["closed"], 1)
		self.assertEqual(row_a["replied"], 0)
		self.assertEqual(row_a["resolved"], 0)

		row_b = rows[self.customer_b]
		self.assertEqual(row_b["total_issues"], 1)
		self.assertEqual(row_b["resolved"], 1)
		self.assertEqual(row_b["open"], 0)

	def test_based_on_customer_sla_status_counts(self):
		columns, data, *_ = execute(self.base_filters("Customer"))
		rows = self.get_rows_by_key(data, "customer")

		# Customer A: 1 Resolution Due + 1 Fulfilled
		row_a = rows[self.customer_a]
		self.assertEqual(row_a["resolution_due"], 1)
		self.assertEqual(row_a["fulfilled"], 1)
		self.assertEqual(row_a["failed"], 0)

		# Customer B: 1 Fulfilled
		row_b = rows[self.customer_b]
		self.assertEqual(row_b["fulfilled"], 1)

	def test_based_on_issue_type(self):
		columns, data, *_ = execute(self.base_filters("Issue Type"))
		self.assertEqual(columns[0]["fieldname"], "issue_type")

		rows = self.get_rows_by_key(data, "issue_type")
		self.assertIn("_Test Bug", rows)
		self.assertIn("_Test Question", rows)

		self.assertEqual(rows["_Test Bug"]["total_issues"], 2)
		self.assertEqual(rows["_Test Bug"]["open"], 1)
		self.assertEqual(rows["_Test Bug"]["closed"], 1)
		self.assertEqual(rows["_Test Question"]["total_issues"], 1)
		self.assertEqual(rows["_Test Question"]["resolved"], 1)

	def test_based_on_priority(self):
		columns, data, *_ = execute(self.base_filters("Issue Priority"))
		self.assertEqual(columns[0]["fieldname"], "priority")

		rows = self.get_rows_by_key(data, "priority")
		self.assertIn("_Test High", rows)
		self.assertIn("_Test Low", rows)

		self.assertEqual(rows["_Test High"]["total_issues"], 2)
		self.assertEqual(rows["_Test Low"]["total_issues"], 1)
		self.assertEqual(rows["_Test Low"]["resolved"], 1)

	def test_based_on_assigned_to_fans_out_per_assignee(self):
		columns, data, *_ = execute(self.base_filters("Assigned To"))
		self.assertEqual(columns[0]["fieldname"], "user")

		rows = self.get_rows_by_key(data, "user")
		# Only the one assigned issue contributes; it was assigned to self.assignee and is Open
		self.assertIn(self.assignee, rows)
		row = rows[self.assignee]
		self.assertEqual(row["total_issues"], 1)
		self.assertEqual(row["open"], 1)

	def test_report_summary_totals(self):
		columns, data, message, chart, report_summary = execute(self.base_filters("Customer"))

		summary_by_label = {entry["label"]: entry["value"] for entry in report_summary}
		# Across both customers: 1 Open, 1 Closed, 1 Resolved
		self.assertEqual(summary_by_label["Open"], 1)
		self.assertEqual(summary_by_label["Closed"], 1)
		self.assertEqual(summary_by_label["Resolved"], 1)
		self.assertEqual(summary_by_label["Replied"], 0)
		self.assertEqual(summary_by_label["On Hold"], 0)

	def test_chart_labels_match_rows(self):
		columns, data, message, chart, report_summary = execute(self.base_filters("Customer"))

		labels = sorted(chart["data"]["labels"])
		row_customers = sorted(row["customer"] for row in data)
		self.assertEqual(labels, row_customers)

		dataset_names = {ds["name"] for ds in chart["data"]["datasets"]}
		self.assertEqual(dataset_names, {"Open", "Replied", "On Hold", "Resolved", "Closed"})

	def test_date_range_excludes_all_issues(self):
		filters = self.base_filters("Customer")
		filters.from_date = add_days(self.today, -60)
		filters.to_date = add_days(self.today, -50)

		columns, data, message, chart, report_summary = execute(filters)

		self.assertTrue(columns)  # columns are still built
		self.assertEqual(data, [])  # no rows
		self.assertEqual(chart["data"]["labels"], [])
		# report summary still returns the five labelled entries, all zero
		for entry in report_summary:
			self.assertEqual(entry["value"], 0)

	def test_status_filter_narrows_results(self):
		filters = self.base_filters("Customer")
		filters.status = "Open"

		columns, data, *_ = execute(filters)
		rows = self.get_rows_by_key(data, "customer")

		# Only Customer A has an Open issue in window
		self.assertIn(self.customer_a, rows)
		self.assertNotIn(self.customer_b, rows)
		self.assertEqual(rows[self.customer_a]["total_issues"], 1)
		self.assertEqual(rows[self.customer_a]["open"], 1)

	def test_customer_filter(self):
		filters = self.base_filters("Customer")
		filters.customer = self.customer_b

		columns, data, *_ = execute(filters)
		rows = self.get_rows_by_key(data, "customer")

		self.assertIn(self.customer_b, rows)
		self.assertNotIn(self.customer_a, rows)
		self.assertEqual(rows[self.customer_b]["total_issues"], 1)
