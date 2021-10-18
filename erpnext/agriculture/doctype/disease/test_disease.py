# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


class TestDisease(unittest.TestCase):
	def test_treatment_period(self):
		disease = frappe.get_doc('Disease', 'Aphids')
		self.assertEqual(disease.treatment_period, 3)
