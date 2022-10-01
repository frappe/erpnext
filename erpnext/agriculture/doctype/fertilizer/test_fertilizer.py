# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe


class TestFertilizer(unittest.TestCase):
	def test_fertilizer_creation(self):
		self.assertEqual(frappe.db.exists("Fertilizer", "Urea"), "Urea")
