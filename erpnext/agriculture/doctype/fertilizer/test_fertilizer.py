# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestFertilizer(unittest.TestCase):
	def test_fertilizer_creation(self):
		self.assertEqual(frappe.db.exists('Fertilizer', 'Urea'), 'Urea')