# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import get_time_str


class TestStockRepostingSettings(unittest.TestCase):

	def test_minimum_time_slot(self):

		def _compare_time(a, b):
			self.assertEqual(get_time_str(a), get_time_str(b))

		# same day
		srs = frappe.get_doc("Stock Reposting Settings")
		srs.limit_reposting_timeslot = 1

		srs.start_time = "12:00:00"
		srs.end_time = "13:00:00"
		srs.validate()
		_compare_time(srs.end_time, "22:00:00")

		# next day
		srs.start_time = "20:00:00"
		srs.end_time = "04:00:00"
		srs.validate()
		_compare_time(srs.end_time, "06:00:00")

		# extra time
		srs.start_time = "20:00:00"
		srs.end_time = "10:00:00"
		srs.validate()
		_compare_time(srs.end_time, "10:00:00")
