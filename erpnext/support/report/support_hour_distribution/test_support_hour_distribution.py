import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from erpnext.support.doctype.issue.test_issue import make_issue
from erpnext.support.report.support_hour_distribution.support_hour_distribution import execute


class TestSupportHourDistribution(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_late_evening_issues_count_in_the_last_slot(self):
		for index, time in enumerate(["22:15:00", "23:30:00", "23:59:59"]):
			make_issue_at(f"{REPORT_DATE} {time}", index)

		row = get_report_row()
		self.assertEqual(row["9PM - 12AM"], 3)


REPORT_DATE = "2001-03-04"


def make_issue_at(creation: str, index: int):
	issue = make_issue(customer="_Test Customer", index=index)
	frappe.db.set_value("Issue", issue.name, "creation", get_datetime(creation), update_modified=False)


def get_report_row() -> dict:
	filters = frappe._dict(from_date=REPORT_DATE, to_date=REPORT_DATE)
	return execute(filters)[1][0]
