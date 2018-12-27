# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import make_service_level_agreement

class TestIssue(unittest.TestCase):

	def test_issue(self):
		make_service_level_agreement()
		test_make_issue = make_issue()
		test_get_issue = get_issue()
		self.assertEquals(test_make_issue, test_get_issue)

def make_issue():
	issue = frappe.get_doc({
		"doctype": "Issue",
		"name": "_Test Issue 1",
		"subject": "Test Support",
		"raised_by": "test@example.com",
		"customer": "_Test Customer"
	}).insert()
	return issue.name

def get_issue():
	issue = frappe.get_list("Issue", filters={"subject": "Test Support"}, limit=1)
	return issue[0].name