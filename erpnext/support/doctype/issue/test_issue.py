# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import create_service_level_agreements_for_issues
from frappe.utils import now_datetime, get_datetime
import datetime
from datetime import timedelta

class TestIssue(unittest.TestCase):
	def test_response_time_and_resolution_time_based_on_different_sla(self):
		frappe.db.set_value("Support Settings", None, "track_service_level_agreement", 1)
		create_service_level_agreements_for_issues()

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

		self.assertEqual(issue.agreement_fulfilled, 'Fulfilled')

def make_issue(creation=None, customer=None, index=0):

	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Service Level Agreement Issue {0}".format(index),
		"customer": customer,
		"raised_by": "test@example.com",
		"description": "Service Level Agreement Issue",
		"creation": creation,
		"service_level_agreement_creation": creation
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
