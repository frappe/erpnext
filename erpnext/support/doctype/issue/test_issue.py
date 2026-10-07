# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import flt, get_datetime

from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import (
	create_service_level_agreements_for_issues,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSetUp(ERPNextTestSuite):
	def setUp(self):
		frappe.db.delete("Service Level Agreement")
		frappe.db.delete("Service Level Priority")
		frappe.db.delete("SLA Fulfilled On Status")
		frappe.db.delete("Pause SLA On Status")
		frappe.db.delete("Service Day")
		frappe.db.set_single_value("Support Settings", "track_service_level_agreement", 1)
		create_service_level_agreements_for_issues()


class TestIssue(TestSetUp):
	def test_response_time_and_resolution_time_based_on_different_sla(self):
		creation = get_datetime("2019-03-04 12:00")

		# make issue with customer specific SLA
		issue = make_issue(creation, "_Test Customer", 1)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-04 15:00"))

		# make issue with customer_group specific SLA
		create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		issue = make_issue(creation, "__Test Customer", 2)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-04 15:00"))

		# make issue with territory specific SLA
		create_customer("___Test Customer", "__Test SLA Customer Group", "_Test SLA Territory")
		issue = make_issue(creation, "___Test Customer", 3)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-04 15:00"))

		# make issue with default SLA
		issue = make_issue(creation=creation, index=4)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 16:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-04 18:00"))

		# make issue with default SLA before working hours
		creation = get_datetime("2019-03-04 7:00")
		issue = make_issue(creation=creation, index=5)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-04 16:00"))

		# make issue with default SLA after working hours
		creation = get_datetime("2019-03-04 20:00")
		issue = make_issue(creation, index=6)

		self.assertEqual(issue.response_by, get_datetime("2019-03-06 14:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-06 16:00"))

		# make issue with default SLA next day
		creation = get_datetime("2019-03-04 14:00")
		issue = make_issue(creation=creation, index=7)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 18:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2019-03-06 12:00"))

		frappe.flags.current_time = get_datetime("2019-03-04 15:00")
		issue.reload()
		issue.status = "Closed"
		issue.save()

		self.assertEqual(issue.agreement_status, "Fulfilled")

	def test_hold_time_on_replied(self):
		creation = get_datetime("2020-03-04 4:00")

		issue = make_issue(creation, index=1)
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = get_datetime("2020-03-04 4:15")
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = get_datetime("2020-03-04 4:15")
		issue.reload()
		issue.status = "Replied"
		issue.save()

		self.assertEqual(issue.on_hold_since, frappe.flags.current_time)
		self.assertFalse(issue.sla_resolution_by)

		creation = get_datetime("2020-03-04 5:00")
		frappe.flags.current_time = get_datetime("2020-03-04 5:00")
		create_communication(issue.name, "test@example.com", "Received", creation)

		issue.reload()
		self.assertEqual(flt(issue.total_hold_time, 2), 2700)
		self.assertEqual(issue.sla_resolution_by, get_datetime("2020-03-04 16:45"))

		creation = get_datetime("2020-03-04 5:05")
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = get_datetime("2020-03-04 5:05")
		issue.reload()
		issue.status = "Closed"
		issue.save()

		issue.reload()
		self.assertEqual(flt(issue.total_hold_time, 2), 2700)

	def test_issue_close_after_on_hold(self):
		frappe.flags.current_time = get_datetime("2021-11-01 19:00")

		issue = make_issue(frappe.flags.current_time, index=1)
		create_communication(issue.name, "test@example.com", "Received", frappe.flags.current_time)

		# send a reply within SLA
		frappe.flags.current_time = get_datetime("2021-11-02 11:00")
		create_communication(issue.name, "test@admin.com", "Sent", frappe.flags.current_time)

		issue.reload()
		issue.status = "Replied"
		issue.save()

		self.assertEqual(issue.on_hold_since, frappe.flags.current_time)

		# close the issue after being on hold for 20 days
		frappe.flags.current_time = get_datetime("2021-11-22 01:00")
		issue.status = "Closed"
		issue.save()

		self.assertEqual(issue.sla_resolution_by, get_datetime("2021-11-22 06:00:00"))
		self.assertEqual(issue.sla_resolution_date, get_datetime("2021-11-22 01:00:00"))
		self.assertEqual(issue.agreement_status, "Fulfilled")

	def test_issue_open_after_closed(self):
		# Created on -> 1 pm, Response Time -> 4 hrs, Resolution Time -> 6 hrs
		frappe.flags.current_time = get_datetime("2021-11-01 13:00")
		issue = make_issue(
			frappe.flags.current_time, index=1, issue_type="Critical"
		)  # Applies 24hr working time SLA
		create_communication(issue.name, "test@example.com", "Received", frappe.flags.current_time)
		self.assertEqual(issue.agreement_status, "First Response Due")
		self.assertEqual(issue.response_by, get_datetime("2021-11-01 17:00"))
		self.assertEqual(issue.sla_resolution_by, get_datetime("2021-11-01 19:00"))

		# Replied on → 2 pm
		frappe.flags.current_time = get_datetime("2021-11-01 14:00")
		create_communication(issue.name, "test@admin.com", "Sent", frappe.flags.current_time)
		issue.reload()
		issue.status = "Replied"
		issue.save()
		self.assertEqual(issue.agreement_status, "Resolution Due")
		self.assertEqual(issue.on_hold_since, frappe.flags.current_time)
		self.assertEqual(issue.first_responded_on, frappe.flags.current_time)

		# Customer Replied → 3 pm
		frappe.flags.current_time = get_datetime("2021-11-01 15:00")
		create_communication(issue.name, "test@example.com", "Received", frappe.flags.current_time)
		issue.reload()
		self.assertEqual(issue.status, "Open")
		# Hold Time + 1 Hrs
		self.assertEqual(issue.total_hold_time, 3600)
		# Resolution By should increase by one hrs
		self.assertEqual(issue.sla_resolution_by, get_datetime("2021-11-01 20:00"))

		# Replied on → 4 pm, Open → 1 hr, Resolution Due → 8 pm
		frappe.flags.current_time = get_datetime("2021-11-01 16:00")
		create_communication(issue.name, "test@admin.com", "Sent", frappe.flags.current_time)
		issue.reload()
		issue.status = "Replied"
		issue.save()
		self.assertEqual(issue.agreement_status, "Resolution Due")

		# Customer Closed → 10 pm
		frappe.flags.current_time = get_datetime("2021-11-01 22:00")
		issue.status = "Closed"
		issue.save()
		# Hold Time + 6 Hrs
		self.assertEqual(issue.total_hold_time, 3600 + 21600)
		# Resolution By should increase by 6 hrs
		self.assertEqual(issue.sla_resolution_by, get_datetime("2021-11-02 02:00"))
		self.assertEqual(issue.agreement_status, "Fulfilled")
		self.assertEqual(issue.sla_resolution_date, frappe.flags.current_time)

		# Customer Open → 3 am i.e after resolution by is crossed
		frappe.flags.current_time = get_datetime("2021-11-02 03:00")
		create_communication(issue.name, "test@example.com", "Received", frappe.flags.current_time)
		issue.reload()
		# Since issue was Resolved, Resolution By should be increased by 5 hrs (3am - 10pm)
		self.assertEqual(issue.total_hold_time, 3600 + 21600 + 18000)
		# Resolution By should increase by 5 hrs
		self.assertEqual(issue.sla_resolution_by, get_datetime("2021-11-02 07:00"))
		self.assertEqual(issue.agreement_status, "Resolution Due")
		self.assertFalse(issue.sla_resolution_date)

		# We Closed → 4 am, SLA should be Fulfilled
		frappe.flags.current_time = get_datetime("2021-11-02 04:00")
		issue.status = "Closed"
		issue.save()
		self.assertEqual(issue.sla_resolution_by, get_datetime("2021-11-02 07:00"))
		self.assertEqual(issue.agreement_status, "Fulfilled")
		self.assertEqual(issue.sla_resolution_date, frappe.flags.current_time)

	def test_recording_of_assignment_on_first_reponse_failure(self):
		from frappe.desk.form.assign_to import add as add_assignment

		frappe.flags.current_time = get_datetime("2021-11-01 19:00")

		issue = make_issue(frappe.flags.current_time, index=1)
		create_user("test@admin.com")
		create_communication(issue.name, "test@example.com", "Received", frappe.flags.current_time)
		add_assignment({"doctype": issue.doctype, "name": issue.name, "assign_to": ["test@admin.com"]})
		issue.reload()

		# send a reply failing response SLA
		frappe.flags.current_time = get_datetime("2021-11-02 15:00")
		create_communication(issue.name, "test@admin.com", "Sent", frappe.flags.current_time)

		# assert if a new timeline item has been added
		# to record the assignment
		comment = frappe.db.exists(
			"Comment",
			{
				"reference_doctype": "Issue",
				"reference_name": issue.name,
				"comment_type": "Assigned",
				"content": _("First Response SLA Failed by {}").format("test"),
			},
		)
		self.assertTrue(comment)

	def test_agreement_status_on_response(self):
		frappe.flags.current_time = get_datetime("2021-11-01 19:00")

		issue = make_issue(frappe.flags.current_time, index=1)
		create_communication(issue.name, "test@example.com", "Received", frappe.flags.current_time)
		self.assertEqual(issue.status, "Open")

		# send a reply within response SLA
		frappe.flags.current_time = get_datetime("2021-11-02 11:00")
		create_communication(issue.name, "test@admin.com", "Sent", frappe.flags.current_time)

		issue.reload()
		self.assertEqual(issue.first_responded_on, frappe.flags.current_time)
		self.assertEqual(issue.agreement_status, "Resolution Due")


class TestFirstResponseTime(TestSetUp):
	# working hours used in all cases: Mon-Fri, 10am to 6pm
	# all dates are in the mm-dd-yyyy format

	# issue creation and first response are on the same day
	def test_first_response_time_case1(self):
		"""
		Test frt when issue creation and first response are during working hours on the same day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 11:00"), get_datetime("06-28-2021 12:00")
		)
		self.assertEqual(issue.first_response_time, 3600.0)

	def test_first_response_time_case2(self):
		"""
		Test frt when issue creation was during working hours, but first response is sent after working hours on the same day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("06-28-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case3(self):
		"""
		Test frt when issue creation was before working hours but first response is sent during working hours on the same day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("06-28-2021 12:00")
		)
		self.assertEqual(issue.first_response_time, 7200.0)

	def test_first_response_time_case4(self):
		"""
		Test frt when both issue creation and first response were after working hours on the same day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 19:00"), get_datetime("06-28-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 1.0)

	def test_first_response_time_case5(self):
		"""
		Test frt when both issue creation and first response are on the same day, but it's not a work day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-27-2021 10:00"), get_datetime("06-27-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 1.0)

	# issue creation and first response are on consecutive days
	def test_first_response_time_case6(self):
		"""
		Test frt when the issue was created before working hours and the first response is also sent before working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("06-29-2021 6:00")
		)
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case7(self):
		"""
		Test frt when the issue was created before working hours and the first response is sent during working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("06-29-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 32400.0)

	def test_first_response_time_case8(self):
		"""
		Test frt when the issue was created before working hours and the first response is sent after working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("06-29-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 57600.0)

	def test_first_response_time_case9(self):
		"""
		Test frt when the issue was created before working hours and the first response is sent on the next day, which is not a work day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-25-2021 6:00"), get_datetime("06-26-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case10(self):
		"""
		Test frt when the issue was created during working hours and the first response is sent before working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("06-29-2021 6:00")
		)
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case11(self):
		"""
		Test frt when the issue was created during working hours and the first response is also sent during working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("06-29-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 25200.0)

	def test_first_response_time_case12(self):
		"""
		Test frt when the issue was created during working hours and the first response is sent after working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("06-29-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 50400.0)

	def test_first_response_time_case13(self):
		"""
		Test frt when the issue was created during working hours and the first response is sent on the next day, which is not a work day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-25-2021 12:00"), get_datetime("06-26-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case14(self):
		"""
		Test frt when the issue was created after working hours and the first response is sent before working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 20:00"), get_datetime("06-29-2021 6:00")
		)
		self.assertEqual(issue.first_response_time, 1.0)

	def test_first_response_time_case15(self):
		"""
		Test frt when the issue was created after working hours and the first response is sent during working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 20:00"), get_datetime("06-29-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 3600.0)

	def test_first_response_time_case16(self):
		"""
		Test frt when the issue was created after working hours and the first response is also sent after working hours, but on the next day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 20:00"), get_datetime("06-29-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case17(self):
		"""
		Test frt when the issue was created after working hours and the first response is sent on the next day, which is not a work day.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-25-2021 20:00"), get_datetime("06-26-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 1.0)

	# issue creation and first response are a few days apart
	def test_first_response_time_case18(self):
		"""
		Test frt when the issue was created before working hours and the first response is also sent before working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("07-01-2021 6:00")
		)
		self.assertEqual(issue.first_response_time, 86400.0)

	def test_first_response_time_case19(self):
		"""
		Test frt when the issue was created before working hours and the first response is sent during working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("07-01-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 90000.0)

	def test_first_response_time_case20(self):
		"""
		Test frt when the issue was created before working hours and the first response is sent after working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 6:00"), get_datetime("07-01-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 115200.0)

	def test_first_response_time_case21(self):
		"""
		Test frt when the issue was created before working hours and the first response is sent after a few days, on a holiday.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-25-2021 6:00"), get_datetime("06-27-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case22(self):
		"""
		Test frt when the issue was created during working hours and the first response is sent before working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("07-01-2021 6:00")
		)
		self.assertEqual(issue.first_response_time, 79200.0)

	def test_first_response_time_case23(self):
		"""
		Test frt when the issue was created during working hours and the first response is also sent during working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("07-01-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 82800.0)

	def test_first_response_time_case24(self):
		"""
		Test frt when the issue was created during working hours and the first response is sent after working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 12:00"), get_datetime("07-01-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 108000.0)

	def test_first_response_time_case25(self):
		"""
		Test frt when the issue was created during working hours and the first response is sent after a few days, on a holiday.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-25-2021 12:00"), get_datetime("06-27-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case26(self):
		"""
		Test frt when the issue was created after working hours and the first response is sent before working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 20:00"), get_datetime("07-01-2021 6:00")
		)
		self.assertEqual(issue.first_response_time, 57600.0)

	def test_first_response_time_case27(self):
		"""
		Test frt when the issue was created after working hours and the first response is sent during working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 20:00"), get_datetime("07-01-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 61200.0)

	def test_first_response_time_case28(self):
		"""
		Test frt when the issue was created after working hours and the first response is also sent after working hours, but after a few days.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-28-2021 20:00"), get_datetime("07-01-2021 20:00")
		)
		self.assertEqual(issue.first_response_time, 86400.0)

	def test_first_response_time_case29(self):
		"""
		Test frt when the issue was created after working hours and the first response is sent after a few days, on a holiday.
		"""
		issue = create_issue_and_communication(
			get_datetime("06-25-2021 20:00"), get_datetime("06-27-2021 11:00")
		)
		self.assertEqual(issue.first_response_time, 1.0)

	def _get_no_perm_user(self):
		email = "test_no_issue_perm@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.new_doc("User")
			user.email = email
			user.first_name = "No Perm"
			user.send_welcome_email = 0
			user.insert(ignore_permissions=True)
		return email

	def test_set_status_requires_write_permission(self):
		from erpnext.support.doctype.issue.issue import set_status

		issue = frappe.new_doc("Issue")
		issue.subject = "_Test Permission Issue"
		issue.insert(ignore_permissions=True)
		frappe.set_user(self._get_no_perm_user())
		self.assertRaises(frappe.PermissionError, set_status, issue.name, "Closed")
		frappe.set_user("Administrator")

	def test_set_multiple_status_requires_write_permission(self):
		import json

		from erpnext.support.doctype.issue.issue import set_multiple_status

		issue = frappe.new_doc("Issue")
		issue.subject = "_Test Permission Issue"
		issue.insert(ignore_permissions=True)
		frappe.set_user(self._get_no_perm_user())
		self.assertRaises(frappe.PermissionError, set_multiple_status, json.dumps([issue.name]), "Closed")
		frappe.set_user("Administrator")


def create_issue_and_communication(issue_creation, first_responded_on):
	issue = make_issue(issue_creation, index=1)
	sender = create_user("test@admin.com")
	frappe.flags.current_time = first_responded_on
	create_communication(issue.name, sender.email, "Sent", first_responded_on)
	issue.reload()

	return issue


def make_issue(creation=None, customer=None, index=0, priority=None, issue_type=None):
	if issue_type and not frappe.db.exists("Issue Type", issue_type):
		doc = frappe.new_doc("Issue Type")
		doc.name = issue_type
		doc.insert()

	issue = frappe.get_doc(
		{
			"doctype": "Issue",
			"subject": f"Service Level Agreement Issue {index}",
			"customer": customer,
			"raised_by": "test@example.com",
			"description": "Service Level Agreement Issue",
			"issue_type": issue_type,
			"priority": priority,
			"creation": creation,
			"opening_date": creation,
			"service_level_agreement_creation": creation,
			"company": "_Test Company",
		}
	).insert(ignore_permissions=True)

	return issue


def create_customer(name, customer_group, territory):
	create_customer_group(customer_group)
	create_territory(territory)

	if not frappe.db.exists("Customer", {"customer_name": name}):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": customer_group,
				"territory": territory,
			}
		).insert(ignore_permissions=True)


def create_customer_group(customer_group):
	if not frappe.db.exists("Customer Group", {"customer_group_name": customer_group}):
		frappe.get_doc({"doctype": "Customer Group", "customer_group_name": customer_group}).insert(
			ignore_permissions=True
		)


def create_territory(territory):
	if not frappe.db.exists("Territory", {"territory_name": territory}):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": territory,
			}
		).insert(ignore_permissions=True)


def create_communication(reference_name, sender, sent_or_received, creation):
	communication = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": sent_or_received,
			"email_status": "Open",
			"subject": "Test Issue",
			"sender": sender,
			"content": "Test",
			"status": "Linked",
			"reference_doctype": "Issue",
			"creation": creation,
			"reference_name": reference_name,
		}
	)
	communication.save()


class TestSplitIssue(ERPNextTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Support Settings", "track_service_level_agreement", 0)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def make_issue(self, subject):
		issue = frappe.get_doc(
			{
				"doctype": "Issue",
				"subject": subject,
				"raised_by": "split-test@example.com",
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		# split_issue() deepcopies self, so it has to start from a document loaded off the
		# database the way the desk caller hands it one, not from the freshly inserted object
		return frappe.get_doc("Issue", issue.name)

	def make_communication(self, subject, communication_date, reference=None, link_to=None, creation=None):
		"""A Communication attached to an Issue by reference, by Timeline Link, or by both."""
		communication = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": "Received",
				"subject": subject,
				"content": subject,
				"sender": "split-test@example.com",
				"status": "Linked",
				"communication_date": get_datetime(communication_date) if communication_date else None,
				"reference_doctype": "Issue" if reference else None,
				"reference_name": reference,
			}
		).insert(ignore_permissions=True)

		if link_to:
			communication.add_link("Issue", link_to, autosave=True)

		if not communication_date:
			# the field defaults to Now whenever it is unset, so leaving it genuinely empty --
			# as an import or an API caller can -- means blanking it after the insert
			frappe.db.set_value(
				"Communication", communication.name, "communication_date", None, update_modified=False
			)
			communication.reload()

		if creation:
			# insert() always stamps creation with the current time, so a test that needs it to
			# disagree with communication_date has to write it afterwards
			frappe.db.set_value(
				"Communication",
				communication.name,
				"creation",
				get_datetime(creation),
				update_modified=False,
			)
			communication.reload()

		return communication

	def linked_issues(self, communication):
		return [
			link.link_name
			for link in frappe.get_doc("Communication", communication).timeline_links
			if link.link_doctype == "Issue"
		]

	def test_split_moves_referenced_communications_from_the_split_point(self):
		issue = self.make_issue("Split source")
		first = self.make_communication("First", "2024-01-01 10:00:00", reference=issue.name)
		second = self.make_communication("Second", "2024-01-01 11:00:00", reference=issue.name)
		third = self.make_communication("Third", "2024-01-01 12:00:00", reference=issue.name)

		split = issue.split_issue(subject="Split target", communication_id=second.name)

		self.assertEqual(frappe.db.get_value("Communication", first.name, "reference_name"), issue.name)
		self.assertEqual(frappe.db.get_value("Communication", second.name, "reference_name"), split)
		self.assertEqual(frappe.db.get_value("Communication", third.name, "reference_name"), split)
		self.assertEqual(frappe.db.get_value("Issue", split, "issue_split_from"), issue.name)

	def test_split_follows_the_timeline_order_not_the_insertion_order(self):
		"""The split point is read off the timeline, which is ordered by communication_date.

		A pulled email is created when it is fetched, so creation can run the other way.
		"""
		issue = self.make_issue("Split source")
		first = self.make_communication(
			"Sent first, fetched last", "2024-01-01 10:00:00", reference=issue.name, creation="2024-06-03"
		)
		second = self.make_communication(
			"Sent second", "2024-01-01 11:00:00", reference=issue.name, creation="2024-06-02"
		)
		third = self.make_communication(
			"Sent last, fetched first", "2024-01-01 12:00:00", reference=issue.name, creation="2024-06-01"
		)

		split = issue.split_issue(subject="Split target", communication_id=second.name)

		self.assertEqual(frappe.db.get_value("Communication", first.name, "reference_name"), issue.name)
		self.assertEqual(frappe.db.get_value("Communication", second.name, "reference_name"), split)
		self.assertEqual(frappe.db.get_value("Communication", third.name, "reference_name"), split)

	def test_split_treats_an_undated_communication_as_the_bottom_of_the_timeline(self):
		"""communication_date is not mandatory, and an undated item sits below every split point."""
		# Split from a dated item: the undated one is below the split point, so it stays behind.
		issue = self.make_issue("Split source")
		undated = self.make_communication("Undated", None, reference=issue.name)
		first = self.make_communication("First", "2024-01-01 10:00:00", reference=issue.name)
		second = self.make_communication("Second", "2024-01-01 11:00:00", reference=issue.name)

		split = issue.split_issue(subject="Split target", communication_id=first.name)

		self.assertEqual(frappe.db.get_value("Communication", undated.name, "reference_name"), issue.name)
		self.assertEqual(frappe.db.get_value("Communication", first.name, "reference_name"), split)
		self.assertEqual(frappe.db.get_value("Communication", second.name, "reference_name"), split)

		# Split from the undated item itself: a null split point drops the date filter, so the
		# whole timeline above it -- which is everything -- moves.
		source = self.make_issue("Undated split source")
		from_undated = self.make_communication("Undated", None, reference=source.name)
		dated = self.make_communication("Dated", "2024-01-01 10:00:00", reference=source.name)

		whole = source.split_issue(subject="Split target", communication_id=from_undated.name)

		self.assertEqual(frappe.db.get_value("Communication", from_undated.name, "reference_name"), whole)
		self.assertEqual(frappe.db.get_value("Communication", dated.name, "reference_name"), whole)

	def test_split_moves_timeline_linked_communications(self):
		"""A Communication on the timeline only through a Timeline Link moves with the split."""
		issue = self.make_issue("Split source")
		referenced = self.make_communication("Referenced", "2024-01-01 10:00:00", reference=issue.name)
		linked = self.make_communication("Linked only", "2024-01-01 11:00:00", link_to=issue.name)

		split = issue.split_issue(subject="Split target", communication_id=referenced.name)

		self.assertEqual(frappe.db.get_value("Communication", referenced.name, "reference_name"), split)
		self.assertEqual(self.linked_issues(linked.name), [split])

	def test_split_from_a_timeline_linked_communication(self):
		"""The Split button is offered on link-only timeline items, so they are valid split points."""
		issue = self.make_issue("Split source")
		linked = self.make_communication("Linked only", "2024-01-01 10:00:00", link_to=issue.name)
		later = self.make_communication("Later", "2024-01-01 11:00:00", reference=issue.name)

		split = issue.split_issue(subject="Split target", communication_id=linked.name)

		self.assertEqual(self.linked_issues(linked.name), [split])
		self.assertEqual(frappe.db.get_value("Communication", later.name, "reference_name"), split)

	def test_split_leaves_the_reference_of_a_linked_communication_alone(self):
		"""Moving a Timeline Link must not rewrite a reference that belongs to another Issue."""
		issue = self.make_issue("Split source")
		other = self.make_issue("Unrelated issue")
		shared = self.make_communication(
			"Shared", "2024-01-01 10:00:00", reference=other.name, link_to=issue.name
		)

		split = issue.split_issue(subject="Split target", communication_id=shared.name)

		self.assertEqual(self.linked_issues(shared.name), [split])
		self.assertEqual(frappe.db.get_value("Communication", shared.name, "reference_name"), other.name)

	def test_split_rejects_a_communication_from_another_issue(self):
		issue = self.make_issue("Split source")
		self.make_communication("Own", "2024-01-01 10:00:00", reference=issue.name)

		other = self.make_issue("Other issue")
		theirs = self.make_communication("Theirs", "2024-01-01 09:00:00", reference=other.name)
		also_theirs = self.make_communication("Also theirs", "2024-01-01 10:30:00", reference=other.name)

		self.assertRaises(frappe.PermissionError, issue.split_issue, "Split target", theirs.name)

		self.assertEqual(frappe.db.get_value("Communication", theirs.name, "reference_name"), other.name)
		self.assertEqual(frappe.db.get_value("Communication", also_theirs.name, "reference_name"), other.name)

	def test_split_rejects_a_communication_that_is_not_on_the_timeline(self):
		issue = self.make_issue("Split source")
		unattached = self.make_communication("Unattached", "2024-01-01 10:00:00")

		self.assertRaises(frappe.PermissionError, issue.split_issue, "Split target", unattached.name)

	def test_split_requires_write_permission_on_the_issue(self):
		issue = self.make_issue("Split source")
		own = self.make_communication("Own", "2024-01-01 10:00:00", reference=issue.name)

		frappe.set_user(create_user("split-no-roles@example.com").email)

		self.assertRaises(
			frappe.PermissionError, frappe.get_doc("Issue", issue.name).split_issue, "Split target", own.name
		)
