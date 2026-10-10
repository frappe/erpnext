# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, add_to_date, getdate, now_datetime

from erpnext.support.doctype.issue.test_issue import create_customer
from erpnext.support.report.first_response_time_for_issues.first_response_time_for_issues import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestFirstResponseTimeForIssues(ERPNextTestSuite):
	def test_avg_first_response_time_grouped_by_creation_date(self):
		today = getdate()

		# Isolate today's group: any pre-existing Issue created today (from other
		# fixtures running in the same transaction) would pollute the average.
		# Rolled back automatically in tearDown.
		frappe.db.delete("Issue", {"creation": (">=", today)})

		# Seed exactly one Issue created today.
		response_time = 3600
		make_responded_issue(response_time, response_time)

		columns, data = execute(frappe._dict(from_date=add_days(today, -1), to_date=add_days(today, 1)))

		# Rows are tuples: (creation_date, avg_response_time) -- report uses .run() w/o as_dict.
		rows_for_today = [row for row in data if getdate(row[0]) == today]
		self.assertEqual(
			len(rows_for_today),
			1,
			f"expected exactly one grouped row for {today}, got {rows_for_today}",
		)

		creation_date, avg_response_time = rows_for_today[0]
		self.assertEqual(getdate(creation_date), today)
		self.assertEqual(float(avg_response_time), float(response_time))

	def test_average_uses_calendar_time_for_issues_with_and_without_sla(self):
		today = getdate()
		frappe.db.delete("Issue", {"creation": (">=", today)})

		# Without an SLA the stored value is calendar time; with one it is working time.
		make_responded_issue(first_response_time=7200, calendar_seconds=7200)
		make_responded_issue(first_response_time=7200, calendar_seconds=237600)

		_columns, data = execute(frappe._dict(from_date=today, to_date=today))
		self.assertEqual(float(data[0][1]), (7200 + 237600) / 2)

	def test_average_covers_only_permitted_issues_of_the_company(self):
		from frappe.permissions import add_user_permission

		today = getdate()
		frappe.db.delete("Issue", {"creation": (">=", today)})

		create_customer("__Test FRT Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		make_responded_issue(3600, 3600, customer="__Test FRT Customer")
		make_responded_issue(7200, 7200, customer="_Test Customer")

		user = "test-first-response-time@example.com"
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
		add_user_permission("Customer", "__Test FRT Customer", user)

		filters = frappe._dict(from_date=today, to_date=today)
		with self.set_user(user):
			self.assertEqual(float(execute(filters)[1][0][1]), 3600)
		self.assertEqual(float(execute(frappe._dict(filters, company="_Test Company"))[1][0][1]), 5400)
		self.assertEqual(execute(frappe._dict(filters, company="_Test Company 1"))[1], ())


def make_responded_issue(
	first_response_time: float, calendar_seconds: float, customer: str | None = None
) -> str:
	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"subject": "First Response Time Report Issue",
			"raised_by": "test_frt_report@example.com",
			"description": "First Response Time Report Issue",
			"company": "_Test Company",
			"customer": customer,
		}
	).insert(ignore_permissions=True)

	creation = now_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
	frappe.db.set_value(
		"Issue",
		issue.name,
		{
			"creation": creation,
			"first_responded_on": add_to_date(creation, seconds=calendar_seconds),
			"first_response_time": first_response_time,
		},
		update_modified=False,
	)
	return issue.name
