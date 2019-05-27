# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.quality_management.doctype.quality_review.test_quality_review import create_review

class TestQualityMeeting(unittest.TestCase):
	def test_quality_meeting(self):
		create_review()
		test_create_meeting = create_meeting()
		test_get_meeting = get_meeting()
		self.assertEquals(test_create_meeting, test_get_meeting)

def create_meeting():
	meeting = frappe.get_doc({
		"doctype": "Quality Meeting",
		"status": "Open",
		"date": frappe.utils.nowdate(),
		"agenda": [
			{
				"agenda": "Test Agenda"
			}
		],
		"minutes": [
			{
				"document_type": "Quality Review",
				"document_name": frappe.db.exists("Quality Review", {"goal": "GOAL-_Test Quality Goal"}),
				"minute": "Test Minute"
			}
		]
	})
	meeting_exist = frappe.db.exists("Quality Meeting", {"date": frappe.utils.nowdate(), "status": "Open"})

	if not meeting_exist:
		meeting.insert()
		return meeting.name
	else:
		return meeting_exist

def get_meeting():
	meeting = frappe.db.exists("Quality Meeting", {"date": frappe.utils.nowdate(), "status": "Open"})
	return meeting