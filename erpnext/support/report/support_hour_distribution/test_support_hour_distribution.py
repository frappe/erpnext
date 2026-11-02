import frappe
from frappe.utils import get_datetime

from erpnext.support.doctype.issue.test_issue import create_customer, make_issue
from erpnext.support.report.support_hour_distribution.support_hour_distribution import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestSupportHourDistribution(ERPNextTestSuite):
	def test_late_evening_issues_count_in_the_last_slot(self):
		for index, time in enumerate(["22:15:00", "23:30:00", "23:59:59"]):
			make_issue_at(f"{REPORT_DATE} {time}", index)

		row = get_report_row()
		self.assertEqual(row["9PM - 12AM"], 3)

	def test_issue_on_a_slot_boundary_counts_once(self):
		make_issue_at(f"{REPORT_DATE} 03:00:00", 1)
		make_issue_at(f"{REPORT_DATE} 00:00:00", 2)

		row = get_report_row()
		self.assertEqual(row["12AM - 3AM"], 1)
		self.assertEqual(row["3AM - 6AM"], 1)

	def test_counts_only_issues_the_user_may_read(self):
		from frappe.permissions import add_user_permission

		create_customer("__Test SHD Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		make_issue_at(f"{REPORT_DATE} 10:00:00", 1, customer="__Test SHD Customer")
		make_issue_at(f"{REPORT_DATE} 10:30:00", 2)

		user = "test-support-hour-distribution@example.com"
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
		add_user_permission("Customer", "__Test SHD Customer", user)

		with self.set_user(user):
			self.assertEqual(get_report_row()["9AM - 12PM"], 1)
		self.assertEqual(get_report_row(company="_Test Company")["9AM - 12PM"], 2)
		self.assertEqual(get_report_row(company="_Test Company 1")["9AM - 12PM"], 0)


REPORT_DATE = "2001-03-04"


def make_issue_at(creation: str, index: int, customer: str = "_Test Customer"):
	issue = make_issue(customer=customer, index=index)
	frappe.db.set_value("Issue", issue.name, "creation", get_datetime(creation), update_modified=False)


def get_report_row(**filters) -> dict:
	filters = frappe._dict(from_date=REPORT_DATE, to_date=REPORT_DATE, **filters)
	return execute(filters)[1][0]
