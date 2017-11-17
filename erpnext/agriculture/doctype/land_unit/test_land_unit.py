# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestLandUnit(unittest.TestCase):
	def test_texture_selection(self):
		self.assertEquals(frappe.db.exists('Land Unit', 'Basil Farm'), 'Basil Farm')