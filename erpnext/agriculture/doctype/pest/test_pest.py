# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestPest(unittest.TestCase):
	def test_treatment_period(self):
		pest = frappe.get_doc('Pest', 'Aphids')
		self.assertEquals(pest.treatment_period, 3)