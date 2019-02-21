# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import make_service_level_agreement
from frappe.utils import now_datetime
from datetime import timedelta

class TestIssue(unittest.TestCase):

	def test_issue(self):
		make_service_level_agreement()
		issue_name = frappe.utils.random_string(6)
		test_make_issue = make_issue(issue_name)
		test_get_issue = get_issue(issue_name)
		self.assertEquals(test_make_issue.name, test_get_issue.name)
		self.assertEquals(test_make_issue.response_by.date(), now_datetime().date()+timedelta(days=1))
		self.assertEquals(test_make_issue.resolution_by.date(), now_datetime().date()+timedelta(days=5))

def make_issue(issue_name):
	issue = frappe.get_doc({
		"doctype": "Issue",
		"name": issue_name,
		"subject": issue_name,
		"raised_by": "test@example.com",
		"customer": "_Test Customer"
	}).insert()
	return issue

def get_issue(issue_name):
	issues = frappe.get_list("Issue", filters={"subject": issue_name}, limit=1)
	issue = frappe.get_doc("Issue", issues[0].name)
	return issue