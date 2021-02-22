# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import create_service_level_agreements_for_issues
from frappe.utils import now_datetime, get_datetime, flt
import datetime
from datetime import timedelta

class TestIssue(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabService Level Agreement`")
		frappe.db.sql("delete from `tabEmployee`")
		frappe.db.set_value("Support Settings", None, "track_service_level_agreement", 1)
		create_service_level_agreements_for_issues()

	def test_response_time_and_resolution_time_based_on_different_sla(self):
		creation = datetime.datetime(2019, 3, 4, 12, 0)

		# make issue with customer specific SLA
		customer = create_customer("_Test Customer", "__Test SLA Customer Group", "__Test SLA Territory")
		issue = make_issue(creation, "_Test Customer", 1)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 14, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 4, 15, 0))

		# make issue with customer_group specific SLA
		customer = create_customer("__Test Customer", "_Test SLA Customer Group", "__Test SLA Territory")
		issue = make_issue(creation, "__Test Customer", 2)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 14, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 4, 15, 0))


		# make issue with territory specific SLA
		customer = create_customer("___Test Customer", "__Test SLA Customer Group", "_Test SLA Territory")
		issue = make_issue(creation, "___Test Customer", 3)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 14, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 4, 15, 0))

		# make issue with default SLA
		issue = make_issue(creation=creation, index=4)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 16, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 4, 18, 0))

		# make issue with default SLA before working hours
		creation = datetime.datetime(2019, 3, 4, 7, 0)
		issue = make_issue(creation=creation, index=5)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 14, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 4, 16, 0))

		# make issue with default SLA after working hours
		creation = datetime.datetime(2019, 3, 4, 20, 0)
		issue = make_issue(creation, index=6)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 6, 14, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 6, 16, 0))

		# make issue with default SLA next day
		creation = datetime.datetime(2019, 3, 4, 14, 0)
		issue = make_issue(creation=creation, index=7)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 18, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 6, 12, 0))

		frappe.flags.current_time = datetime.datetime(2019, 3, 4, 15, 0)

		issue.status = 'Closed'
		issue.save()

		self.assertEqual(issue.agreement_status, 'Fulfilled')

	def test_issue_metrics(self):
		creation = datetime.datetime(2020, 3, 4, 4, 0)

		issue = make_issue(creation, index=1)
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = datetime.datetime(2020, 3, 4, 4, 15)
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		creation = datetime.datetime(2020, 3, 4, 5, 0)
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = datetime.datetime(2020, 3, 4, 5, 5)
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = datetime.datetime(2020, 3, 4, 5, 5)
		issue.reload()
		issue.status = 'Closed'
		issue.save()

		self.assertEqual(issue.avg_response_time, 600)
		self.assertEqual(issue.resolution_time, 3900)
		self.assertEqual(issue.user_resolution_time, 1200)

	def test_hold_time_on_replied(self):
		creation = datetime.datetime(2020, 3, 4, 4, 0)

		issue = make_issue(creation, index=1)
		create_communication(issue.name, "test@example.com", "Received", creation)

		creation = datetime.datetime(2020, 3, 4, 4, 15)
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = datetime.datetime(2020, 3, 4, 4, 15)
		issue.reload()
		issue.status = 'Replied'
		issue.save()

		self.assertEqual(issue.on_hold_since, frappe.flags.current_time)

		creation = datetime.datetime(2020, 3, 4, 5, 0)
		frappe.flags.current_time = datetime.datetime(2020, 3, 4, 5, 0)
		create_communication(issue.name, "test@example.com", "Received", creation)

		issue.reload()
		self.assertEqual(flt(issue.total_hold_time, 2), 2700)
		self.assertEqual(issue.resolution_by, datetime.datetime(2020, 3, 4, 16, 45))

		creation = datetime.datetime(2020, 3, 4, 5, 5)
		create_communication(issue.name, "test@admin.com", "Sent", creation)

		frappe.flags.current_time = datetime.datetime(2020, 3, 4, 5, 5)
		issue.reload()
		issue.status = 'Closed'
		issue.save()

		issue.reload()
		self.assertEqual(flt(issue.total_hold_time, 2), 2700)


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
	issue = frappe.get_doc({
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
	issue.save()
