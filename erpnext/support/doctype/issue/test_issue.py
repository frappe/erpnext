# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import datetime
import unittest

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import flt, get_datetime

from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import (
	create_service_level_agreements_for_issues,
)


class TestSetUp(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabService Level Agreement`")
		frappe.db.sql("delete from `tabService Level Priority`")
		frappe.db.sql("delete from `tabSLA Fulfilled On Status`")
		frappe.db.sql("delete from `tabPause SLA On Status`")
		frappe.db.sql("delete from `tabService Day`")
		frappe.db.set_value("Support Settings", None, "track_service_level_agreement", 1)
		create_service_level_agreements_for_issues()

class TestIssue(TestSetUp):
	def test_response_time_and_resolution_time_based_on_different_sla(self):
		creation = get_datetime("2019-03-04 12:00")

		# make issue with customer specific SLA
		customer = create_customer("_Test Customer", "__Test SLA Customer Group", "__Test SLA Territory")
		issue = make_issue(creation, "_Test Customer", 1)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-04 15:00"))

		# make issue with customer_group specific SLA
		customer = create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		issue = make_issue(creation, "__Test Customer", 2)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-04 15:00"))


		# make issue with territory specific SLA
		customer = create_customer("___Test Customer", "__Test SLA Customer Group", "_Test SLA Territory")
		issue = make_issue(creation, "___Test Customer", 3)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-04 15:00"))

		# make issue with default SLA
		issue = make_issue(creation=creation, index=4)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 16:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-04 18:00"))

		# make issue with default SLA before working hours
		creation = get_datetime("2019-03-04 7:00")
		issue = make_issue(creation=creation, index=5)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 14:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-04 16:00"))

		# make issue with default SLA after working hours
		creation = get_datetime("2019-03-04 20:00")
		issue = make_issue(creation, index=6)

		self.assertEqual(issue.response_by, get_datetime("2019-03-06 14:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-06 16:00"))

		# make issue with default SLA next day
		creation = get_datetime("2019-03-04 14:00")
		issue = make_issue(creation=creation, index=7)

		self.assertEqual(issue.response_by, get_datetime("2019-03-04 18:00"))
		self.assertEqual(issue.resolution_by, get_datetime("2019-03-06 12:00"))

		frappe.flags.current_time = get_datetime("2019-03-04 15:00")
		issue.reload()
		issue.status = 'Closed'
		issue.save()

		self.assertEqual(issue.agreement_status, 'Fulfilled')

	def test_issue_metrics(self):
		creation = get_datetime("2020-03-04 4:00")

		issue = make_issue(creation, index=1)
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = get_datetime("2020-03-04 4:15")
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		creation = get_datetime("2020-03-04 5:00")
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = get_datetime("2020-03-04 5:05")
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = get_datetime("2020-03-04 5:05")
		issue.reload()
		issue.status = 'Closed'
		issue.save()

		self.assertEqual(issue.avg_response_time, 600)
		self.assertEqual(issue.resolution_time, 3900)
		self.assertEqual(issue.user_resolution_time, 1200)

	def test_hold_time_on_replied(self):
		creation = get_datetime("2020-03-04 4:00")

		issue = make_issue(creation, index=1)
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = get_datetime("2020-03-04 4:15")
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = get_datetime("2020-03-04 4:15")
		issue.reload()
		issue.status = 'Replied'
		issue.save()

		self.assertEqual(issue.on_hold_since, frappe.flags.current_time)

		creation = get_datetime("2020-03-04 5:00")
		frappe.flags.current_time = get_datetime("2020-03-04 5:00")
		create_communication(issue.name, "test@example.com", "Received", creation)

		issue.reload()
		self.assertEqual(flt(issue.total_hold_time, 2), 2700)
		self.assertEqual(issue.resolution_by, get_datetime("2020-03-04 16:45"))

		creation = get_datetime("2020-03-04 5:05")
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = get_datetime("2020-03-04 5:05")
		issue.reload()
		issue.status = 'Closed'
		issue.save()

		issue.reload()
		self.assertEqual(flt(issue.total_hold_time, 2), 2700)

class TestFirstResponseTime(TestSetUp):
	# working hours used in all cases: Mon-Fri, 10am to 6pm
	# all dates are in the mm-dd-yyyy format

	# issue creation and first response are on the same day
	def test_first_response_time_case1(self):
		"""
			Test frt when issue creation and first response are during working hours on the same day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 11:00"), get_datetime("06-28-2021 12:00"))
		self.assertEqual(issue.first_response_time, 3600.0)

	def test_first_response_time_case2(self):
		"""
			Test frt when issue creation was during working hours, but first response is sent after working hours on the same day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("06-28-2021 20:00"))
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case3(self):
		"""
			Test frt when issue creation was before working hours but first response is sent during working hours on the same day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("06-28-2021 12:00"))
		self.assertEqual(issue.first_response_time, 7200.0)

	def test_first_response_time_case4(self):
		"""
			Test frt when both issue creation and first response were after working hours on the same day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 19:00"), get_datetime("06-28-2021 20:00"))
		self.assertEqual(issue.first_response_time, 1.0)

	def test_first_response_time_case5(self):
		"""
			Test frt when both issue creation and first response are on the same day, but it's not a work day.
		"""
		issue = create_issue_and_communication(get_datetime("06-27-2021 10:00"), get_datetime("06-27-2021 11:00"))
		self.assertEqual(issue.first_response_time, 1.0)

	# issue creation and first response are on consecutive days
	def test_first_response_time_case6(self):
		"""
			Test frt when the issue was created before working hours and the first response is also sent before working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("06-29-2021 6:00"))
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case7(self):
		"""
			Test frt when the issue was created before working hours and the first response is sent during working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("06-29-2021 11:00"))
		self.assertEqual(issue.first_response_time, 32400.0)

	def test_first_response_time_case8(self):
		"""
			Test frt when the issue was created before working hours and the first response is sent after working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("06-29-2021 20:00"))
		self.assertEqual(issue.first_response_time, 57600.0)

	def test_first_response_time_case9(self):
		"""
			Test frt when the issue was created before working hours and the first response is sent on the next day, which is not a work day.
		"""
		issue = create_issue_and_communication(get_datetime("06-25-2021 6:00"), get_datetime("06-26-2021 11:00"))
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case10(self):
		"""
			Test frt when the issue was created during working hours and the first response is sent before working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("06-29-2021 6:00"))
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case11(self):
		"""
			Test frt when the issue was created during working hours and the first response is also sent during working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("06-29-2021 11:00"))
		self.assertEqual(issue.first_response_time, 25200.0)

	def test_first_response_time_case12(self):
		"""
			Test frt when the issue was created during working hours and the first response is sent after working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("06-29-2021 20:00"))
		self.assertEqual(issue.first_response_time, 50400.0)

	def test_first_response_time_case13(self):
		"""
			Test frt when the issue was created during working hours and the first response is sent on the next day, which is not a work day.
		"""
		issue = create_issue_and_communication(get_datetime("06-25-2021 12:00"), get_datetime("06-26-2021 11:00"))
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case14(self):
		"""
			Test frt when the issue was created after working hours and the first response is sent before working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 20:00"), get_datetime("06-29-2021 6:00"))
		self.assertEqual(issue.first_response_time, 1.0)

	def test_first_response_time_case15(self):
		"""
			Test frt when the issue was created after working hours and the first response is sent during working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 20:00"), get_datetime("06-29-2021 11:00"))
		self.assertEqual(issue.first_response_time, 3600.0)

	def test_first_response_time_case16(self):
		"""
			Test frt when the issue was created after working hours and the first response is also sent after working hours, but on the next day.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 20:00"), get_datetime("06-29-2021 20:00"))
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case17(self):
		"""
			Test frt when the issue was created after working hours and the first response is sent on the next day, which is not a work day.
		"""
		issue = create_issue_and_communication(get_datetime("06-25-2021 20:00"), get_datetime("06-26-2021 11:00"))
		self.assertEqual(issue.first_response_time, 1.0)

	# issue creation and first response are a few days apart
	def test_first_response_time_case18(self):
		"""
			Test frt when the issue was created before working hours and the first response is also sent before working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("07-01-2021 6:00"))
		self.assertEqual(issue.first_response_time, 86400.0)

	def test_first_response_time_case19(self):
		"""
			Test frt when the issue was created before working hours and the first response is sent during working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("07-01-2021 11:00"))
		self.assertEqual(issue.first_response_time, 90000.0)

	def test_first_response_time_case20(self):
		"""
			Test frt when the issue was created before working hours and the first response is sent after working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 6:00"), get_datetime("07-01-2021 20:00"))
		self.assertEqual(issue.first_response_time, 115200.0)

	def test_first_response_time_case21(self):
		"""
			Test frt when the issue was created before working hours and the first response is sent after a few days, on a holiday.
		"""
		issue = create_issue_and_communication(get_datetime("06-25-2021 6:00"), get_datetime("06-27-2021 11:00"))
		self.assertEqual(issue.first_response_time, 28800.0)

	def test_first_response_time_case22(self):
		"""
			Test frt when the issue was created during working hours and the first response is sent before working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("07-01-2021 6:00"))
		self.assertEqual(issue.first_response_time, 79200.0)

	def test_first_response_time_case23(self):
		"""
			Test frt when the issue was created during working hours and the first response is also sent during working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("07-01-2021 11:00"))
		self.assertEqual(issue.first_response_time, 82800.0)

	def test_first_response_time_case24(self):
		"""
			Test frt when the issue was created during working hours and the first response is sent after working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 12:00"), get_datetime("07-01-2021 20:00"))
		self.assertEqual(issue.first_response_time, 108000.0)

	def test_first_response_time_case25(self):
		"""
			Test frt when the issue was created during working hours and the first response is sent after a few days, on a holiday.
		"""
		issue = create_issue_and_communication(get_datetime("06-25-2021 12:00"), get_datetime("06-27-2021 11:00"))
		self.assertEqual(issue.first_response_time, 21600.0)

	def test_first_response_time_case26(self):
		"""
			Test frt when the issue was created after working hours and the first response is sent before working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 20:00"), get_datetime("07-01-2021 6:00"))
		self.assertEqual(issue.first_response_time, 57600.0)

	def test_first_response_time_case27(self):
		"""
			Test frt when the issue was created after working hours and the first response is sent during working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 20:00"), get_datetime("07-01-2021 11:00"))
		self.assertEqual(issue.first_response_time, 61200.0)

	def test_first_response_time_case28(self):
		"""
			Test frt when the issue was created after working hours and the first response is also sent after working hours, but after a few days.
		"""
		issue = create_issue_and_communication(get_datetime("06-28-2021 20:00"), get_datetime("07-01-2021 20:00"))
		self.assertEqual(issue.first_response_time, 86400.0)

	def test_first_response_time_case29(self):
		"""
			Test frt when the issue was created after working hours and the first response is sent after a few days, on a holiday.
		"""
		issue = create_issue_and_communication(get_datetime("06-25-2021 20:00"), get_datetime("06-27-2021 11:00"))
		self.assertEqual(issue.first_response_time, 1.0)

def create_issue_and_communication(issue_creation, first_responded_on):
	issue = make_issue(issue_creation, index=1)
	sender = create_user("test@admin.com")
	create_communication(issue.name, sender.email, "Sent", first_responded_on)
	issue.reload()

	return issue

def make_issue(creation=None, customer=None, index=0, priority=None, issue_type=None):
	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Service Level Agreement Issue {0}".format(index),
		"customer": customer,
		"raised_by": "test@example.com",
		"description": "Service Level Agreement Issue",
		"issue_type": issue_type,
		"priority": priority,
		"creation": creation,
		"opening_date": creation,
		"service_level_agreement_creation": creation,
		"company": "_Test Company"
	}).insert(ignore_permissions=True)

	return issue


def create_customer(name, customer_group, territory):

	create_customer_group(customer_group)
	create_territory(territory)

	if not frappe.db.exists("Customer", {"customer_name": name}):
		frappe.get_doc({
			"doctype": "Customer",
			"customer_name": name,
			"customer_group": customer_group,
			"territory": territory
		}).insert(ignore_permissions=True)


def create_customer_group(customer_group):

	if not frappe.db.exists("Customer Group", {"customer_group_name": customer_group}):
		frappe.get_doc({
			"doctype": "Customer Group",
			"customer_group_name": customer_group
		}).insert(ignore_permissions=True)


def create_territory(territory):

	if not frappe.db.exists("Territory", {"territory_name": territory}):
		frappe.get_doc({
			"doctype": "Territory",
			"territory_name": territory,
		}).insert(ignore_permissions=True)


def create_communication(reference_name, sender, sent_or_received, creation):
	communication = frappe.get_doc({
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
		"reference_name": reference_name
	})
	communication.save()
