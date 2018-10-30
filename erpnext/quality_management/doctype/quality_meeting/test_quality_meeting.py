# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityMeeting(unittest.TestCase):
	pass

	def test_quality_meeting(self):
		test_create_meeting = create_meeting()
		test_get_meeting = get_meeting()
		self.assertEquals(test_create_meeting.name, test_get_meeting.name)

def create_meeting():
	meeting = frappe.get_doc({
		"doctype": "Quality Meeting",
		"scope": "Company",
		"status": "Close",
		"date": ""+ frappe.utils.nowdate() +""
	})
	meeting_exist = frappe.get_list("Quality Meeting", filters={"date": ""+ meeting.date +""}, fields=["name"])
	if len(meeting_exist) == 0:
		meeting.insert()
		return meeting
	else:
		return meeting_exist[0]

def get_meeting():
	meeting = frappe.get_list("Quality Meeting")
	return meeting[0]