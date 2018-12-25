# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.support_contract.test_support_contract import make_support_contract

test_records = frappe.get_test_records('Issue')

class TestIssue(unittest.TestCase):
	
	def test_issue(self):
		make_support_contract()
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
	})
	issue_exists = frappe.db.exists("Issue", "Test Support 2")
	if not issue_exists:
		issue.insert()
		return issue.name
	else:
		return issue_exists

def get_issue():
	issue = frappe.get_list("Issue", filters={"subject": "Test Support"}, limit=1)
	return issue[0].name
