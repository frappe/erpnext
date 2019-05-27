# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestIssuePriority(unittest.TestCase):
	pass

def make_priorities():
	insert_priority("Low")
	insert_priority("Medium")
	insert_priority("High")

def insert_priority(name):
	if not frappe.db.exists("Issue Priority", name):
		frappe.get_doc({
			"doctype": "Issue Priority",
			"name": name
		}).insert(ignore_permissions=True)