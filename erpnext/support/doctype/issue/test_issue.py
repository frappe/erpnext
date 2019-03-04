# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import make_service_level_agreement
from frappe.utils import now_datetime
import datetime
from datetime import timedelta

class TestIssue(unittest.TestCase):

	def test_issue(self):
		make_service_level_agreement()

		creation = now_datetime()
		creation_time = datetime.datetime.combine(creation.date(), datetime.time(12, 0, 0))

		issue = make_issue_with_SLA(creation_time)
		test_get_issue = get_issue(issue.name)
		print(test_get_issue)
		self.assertEquals(issue.response_by.date(), now_datetime().date()+timedelta(days=3))
		self.assertEquals(issue.resolution_by.date(), now_datetime().date()+timedelta(days=5))

		creation_time = datetime.datetime.combine(creation.date(), datetime.time(12, 0, 0))
		issue = make_issue_with_default_SLA_same_day(creation_time)
		test_get_issue = get_issue(issue.name)
		print(test_get_issue)
		self.assertEquals(issue.response_by.date(), now_datetime().date())
		self.assertEquals(issue.resolution_by.date(), now_datetime().date())

		creation_time = datetime.datetime.combine(creation.date(), datetime.time(5, 0, 0))
		issue = make_issue_with_default_SLA_next_day(creation_time)
		test_get_issue = get_issue(issue.name)
		print(test_get_issue)
		self.assertEquals(issue.response_by.date(), now_datetime().date()+timedelta(days=2))
		self.assertEquals(issue.resolution_by.date(), now_datetime().date()+timedelta(days=2))

def make_issue_with_SLA(creation):

	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Issue 1",
		"raised_by": "test@example.com",
		"customer": "_Test Customer",
		"creation": creation
	}).insert()

	return issue

def make_issue_with_default_SLA_same_day(creation):

	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Issue 2",
		"raised_by": "test@example.com",
		"creation": creation
	}).insert()

	return issue

def make_issue_with_default_SLA_next_day(creation):

	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": "Issue 3",
		"raised_by": "test@example.com",
		"creation": creation
	}).insert()

	return issue

def get_issue(name):
	issue = frappe.get_list("Issue", fields={'name', 'response_by', 'resolution_by'}, filters={'name': name},limit=1)
	return issue[0]