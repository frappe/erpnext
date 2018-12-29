# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest, time
from frappe.utils.selenium_testdriver import TestDriver
from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity

class TestLostReason(unittest.TestCase):
	def setUp(self):
		self.driver = TestDriver()

	def test_opportunity_lost(self):
		doc = make_opportunity(with_items=0)
		doc.save()
		self.assertEqual(doc.status, "Open")

		self.driver.set_route('Form', 'Opportinuty', doc.name)
		time.sleep(2)

		lost = self.driver.find('.form-inner-toolbar')[1]
		lost.click()
		time.sleep(2)

		self.driver.set_text_editor('order_lost_reason', 'Test reason for detailed reason')

		self.driver.click_primary_action()
		self.assertEqual(doc.status, "Lost")
		self.assertEqual(doc.order_lost_reason, "Test reason for detailed reason")

	def tearDown(self):
		self.driver.close()


