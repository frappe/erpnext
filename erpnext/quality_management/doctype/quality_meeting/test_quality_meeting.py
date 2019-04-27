# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityMeeting(unittest.TestCase):
	def test_quality_meeting(self):
		test_create_meeting = create_meeting()
		test_get_meeting = get_meeting()
		self.assertEquals(test_create_meeting, test_get_meeting)

def create_meeting():
	meeting = frappe.get_doc({
		"doctype": "Quality Meeting",
		"date": frappe.utils.today(),
		"status": "Open"
	})
	meeting_exist = frappe.db.get_value("Quality Meeting", {"date": frappe.utils.today()}, "name")
	if not meeting_exist:
		meeting.insert()
		return meeting.name
	else:
		return meeting_exist

def get_meeting():
	return frappe.db.get_value("Quality Meeting", {"date": frappe.utils.today()}, "name")