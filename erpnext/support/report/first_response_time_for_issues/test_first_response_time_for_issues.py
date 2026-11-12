# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, getdate, now_datetime

from erpnext.support.report.first_response_time_for_issues.first_response_time_for_issues import (
	execute,
)


class TestFirstResponseTimeForIssues(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_average_uses_calendar_time_for_issues_with_and_without_sla(self):
		today = getdate()
		frappe.db.delete("Issue", {"creation": (">=", today)})

		# Without an SLA the stored value is calendar time; with one it is working time.
		make_responded_issue(first_response_time=7200, calendar_seconds=7200)
		make_responded_issue(first_response_time=7200, calendar_seconds=237600)

		_columns, data = execute(frappe._dict(from_date=today, to_date=today))
		self.assertEqual(float(data[0][1]), (7200 + 237600) / 2)

	def test_average_ignores_fractional_seconds_on_every_database(self):
		today = getdate()
		frappe.db.delete("Issue", {"creation": (">=", today)})

		# Each timestamp is cut to whole seconds: 3601.2 - 0.7 counts as 3601 - 0
		make_responded_issue(3600, 3600.5, creation_microsecond=700000)

		_columns, data = execute(frappe._dict(from_date=today, to_date=today))
		self.assertEqual(float(data[0][1]), 3601)


def make_responded_issue(
	first_response_time: float, calendar_seconds: float, creation_microsecond: int = 0
) -> str:
	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"subject": "First Response Time Report Issue",
			"raised_by": "test_frt_report@example.com",
			"description": "First Response Time Report Issue",
			"company": "_Test Company",
		}
	).insert(ignore_permissions=True)

	creation = now_datetime().replace(hour=0, minute=0, second=0, microsecond=creation_microsecond)
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
