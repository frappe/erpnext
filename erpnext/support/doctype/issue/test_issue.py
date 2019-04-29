# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import make_service_level_agreement
from frappe.utils import now_datetime
import datetime
from datetime import timedelta
from frappe.desk.form import assign_to

class TestIssue(unittest.TestCase):
	def test_assignment(self):
		frappe.db.set_value('Customer', '_Test Customer', 'account_manager', 'test1@example.com')
		doc = make_issue(customer='_Test Customer')
		self.assertEqual(assign_to.get(dict(doctype = doc.doctype, name = doc.name))[0].get('owner'), 'test1@example.com')


	def test_response_time_and_resolution_time_based_on_different_sla(self):
		make_service_level_agreement()

		creation = "2019-03-04 12:00:00"

		# make issue with customer specific SLA
		issue = make_issue(creation, '_Test Customer')

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 7, 18, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 9, 18, 0))

		# make issue with default SLA
		issue = make_issue(creation)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 16, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 4, 18, 0))

		creation = "2019-03-04 14:00:00"
		# make issue with default SLA next day
		issue = make_issue(creation)

		self.assertEquals(issue.response_by, datetime.datetime(2019, 3, 4, 18, 0))
		self.assertEquals(issue.resolution_by, datetime.datetime(2019, 3, 6, 12, 0))

		frappe.flags.current_time = datetime.datetime(2019, 3, 3, 12, 0)

		issue.status = 'Closed'
		issue.save()

		self.assertEqual(issue.agreement_status, 'Fulfilled')

		issue.status = 'Open'
		issue.save()

		frappe.flags.current_time = datetime.datetime(2019, 3, 5, 12, 0)

		issue.status = 'Closed'
		issue.save()

		self.assertEqual(issue.agreement_status, 'Failed')



def make_issue(creation=None, customer=None):

	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Issue 1",
		"customer": customer,
		"raised_by": "test@example.com",
		"creation": creation
	}).insert()

	return issue