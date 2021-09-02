# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest


def create_records():
	pass

class TestPartySpecificItem(unittest.TestCase):
	def setUp(self):
		create_records()

	def tearDown(self):
		frappe.set_user("Administrator")
