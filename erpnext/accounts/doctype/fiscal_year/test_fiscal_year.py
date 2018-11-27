# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, unittest

test_records = frappe.get_test_records('Fiscal Year')
test_ignore = ["Company"]

class TestFiscalYear(unittest.TestCase):
	def test_extra_year(self):
		if frappe.db.exists("Fiscal Year", "_Test Fiscal Year 2000"):
			frappe.delete_doc("Fiscal Year", "_Test Fiscal Year 2000")
		fy = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year": "_Test Fiscal Year 2000",
			"year_end_date": "2002-12-31",
			"year_start_date": "2000-04-01"
		})
		fy.insert()
		self.assertEqual(fy.year_end_date, '2001-03-31')

