import frappe
from frappe.desk.form.assign_to import add as add_assignment
from frappe.utils import add_months, getdate

from erpnext.support.doctype.issue.test_issue import create_customer, make_issue
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import (
	create_service_level_agreements_for_issues,
)
from erpnext.support.report.issue_analytics.issue_analytics import execute
from erpnext.tests.utils import ERPNextTestSuite

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class TestIssueAnalytics(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Support Settings", "track_service_level_agreement", 1)

		current_month_date = getdate()
		last_month_date = add_months(current_month_date, -1)
		self.current_month = str(months[current_month_date.month - 1]).lower()
		self.last_month = str(months[last_month_date.month - 1]).lower()
		if current_month_date.year != last_month_date.year:
			self.current_month += "_" + str(current_month_date.year)
			self.last_month += "_" + str(last_month_date.year)

	def test_issue_analytics(self):
		create_service_level_agreements_for_issues()
		create_issue_types()
		create_records()

		self.compare_result_for_customer()
		self.compare_result_for_issue_type()
		self.compare_result_for_issue_priority()
		self.compare_result_for_assignment()

	def compare_result_for_customer(self):
		filters = {
			"company": "_Test Company",
			"based_on": "Customer",
			"from_date": add_months(getdate(), -1),
			"to_date": getdate(),
			"range": "Monthly",
		}

		report = execute(filters)

		expected_data = [
			{"customer": "__Test Customer 2", self.last_month: 1.0, self.current_month: 0.0, "total": 1.0},
			{"customer": "__Test Customer 1", self.last_month: 0.0, self.current_month: 1.0, "total": 1.0},
			{"customer": "__Test Customer", self.last_month: 1.0, self.current_month: 1.0, "total": 2.0},
		]

		self.assertEqual(expected_data, report[1])  # rows
		self.assertEqual(len(report[0]), 4)  # cols

	def compare_result_for_issue_type(self):
		filters = {
			"company": "_Test Company",
			"based_on": "Issue Type",
			"from_date": add_months(getdate(), -1),
			"to_date": getdate(),
			"range": "Monthly",
		}

		report = execute(filters)

		expected_data = [
			{"issue_type": "Discomfort", self.last_month: 1.0, self.current_month: 0.0, "total": 1.0},
			{"issue_type": "Service Request", self.last_month: 0.0, self.current_month: 1.0, "total": 1.0},
			{"issue_type": "Bug", self.last_month: 1.0, self.current_month: 1.0, "total": 2.0},
		]

		self.assertEqual(expected_data, report[1])  # rows
		self.assertEqual(len(report[0]), 4)  # cols

	def compare_result_for_issue_priority(self):
		filters = {
			"company": "_Test Company",
			"based_on": "Issue Priority",
			"from_date": add_months(getdate(), -1),
			"to_date": getdate(),
			"range": "Monthly",
		}

		report = execute(filters)

		expected_data = [
			{"priority": "Medium", self.last_month: 1.0, self.current_month: 1.0, "total": 2.0},
			{"priority": "Low", self.last_month: 1.0, self.current_month: 0.0, "total": 1.0},
			{"priority": "High", self.last_month: 0.0, self.current_month: 1.0, "total": 1.0},
		]

		self.assertEqual(expected_data, report[1])  # rows
		self.assertEqual(len(report[0]), 4)  # cols

	def compare_result_for_assignment(self):
		filters = {
			"company": "_Test Company",
			"based_on": "Assigned To",
			"from_date": add_months(getdate(), -1),
			"to_date": getdate(),
			"range": "Monthly",
		}

		report = execute(filters)

		expected_data = [
			{"user": "test@example.com", self.last_month: 1.0, self.current_month: 1.0, "total": 2.0},
			{"user": "test1@example.com", self.last_month: 2.0, self.current_month: 1.0, "total": 3.0},
		]

		self.assertEqual(expected_data, report[1])  # rows
		self.assertEqual(len(report[0]), 4)  # cols

	def test_issue_count_over_a_long_weekly_range(self):
		create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		make_issue(getdate("2027-02-15"), "__Test Customer", 1)

		self.assertEqual(self.get_total("2026-01-01", "2027-03-31", "Weekly"), 1)

	def test_weekly_issue_count_across_year_end(self):
		create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		make_issue(getdate("2025-12-30"), "__Test Customer", 1)
		make_issue(getdate("2026-01-14"), "__Test Customer", 2)

		self.assertEqual(self.get_total("2025-12-01", "2026-01-31", "Weekly"), 2)

	def test_quarterly_issue_count_from_mid_quarter(self):
		create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		for index, opening_date in enumerate(["2026-05-20", "2026-08-10", "2026-11-10"]):
			make_issue(getdate(opening_date), "__Test Customer", index)

		self.assertEqual(self.get_total("2026-05-15", "2026-12-31", "Quarterly"), 3)

	def get_total(self, from_date, to_date, period_range):
		filters = {
			"company": "_Test Company",
			"based_on": "Customer",
			"customer": "__Test Customer",
			"from_date": from_date,
			"to_date": to_date,
			"range": period_range,
		}
		rows = execute(filters)[1]
		return sum(row["total"] for row in rows)


def create_issue_types():
	for entry in ["Bug", "Service Request", "Discomfort"]:
		if not frappe.db.exists("Issue Type", entry):
			frappe.get_doc({"doctype": "Issue Type", "__newname": entry}).insert()


def create_records():
	create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
	create_customer("__Test Customer 1", "_Test SLA Customer Group", "__Test SLA Territory")
	create_customer("__Test Customer 2", "_Test SLA Customer Group", "__Test SLA Territory")

	current_month_date = getdate()
	last_month_date = add_months(current_month_date, -1)

	issue = make_issue(current_month_date, "__Test Customer", 2, "High", "Bug")
	add_assignment({"assign_to": ["test@example.com"], "doctype": "Issue", "name": issue.name})

	issue = make_issue(last_month_date, "__Test Customer", 2, "Low", "Bug")
	add_assignment({"assign_to": ["test1@example.com"], "doctype": "Issue", "name": issue.name})

	issue = make_issue(current_month_date, "__Test Customer 1", 2, "Medium", "Service Request")
	add_assignment({"assign_to": ["test1@example.com"], "doctype": "Issue", "name": issue.name})

	issue = make_issue(last_month_date, "__Test Customer 2", 2, "Medium", "Discomfort")
	add_assignment(
		{"assign_to": ["test@example.com", "test1@example.com"], "doctype": "Issue", "name": issue.name}
	)
