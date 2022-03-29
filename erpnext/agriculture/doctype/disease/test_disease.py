# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe


class TestDisease(unittest.TestCase):
	def test_treatment_period(self):
		disease = frappe.get_doc("Disease", "Aphids")
		self.assertEqual(disease.treatment_period, 3)
