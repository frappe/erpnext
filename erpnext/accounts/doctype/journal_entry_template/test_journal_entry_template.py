# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest

from .journal_entry_template import get_naming_series

class TestJournalEntryTemplate(unittest.TestCase):
	def test_get_naming_series_TC_ACC_324(self):
		naming_series = get_naming_series().split("\n") or []
		if not naming_series or  len(naming_series) < 1:
			with self.assertRaises(frappe.ValidationError, msg="Naming Series is not set for Journal Entry"):
				pass  
