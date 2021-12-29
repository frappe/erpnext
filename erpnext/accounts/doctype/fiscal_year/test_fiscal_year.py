# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import now_datetime

from erpnext.accounts.doctype.fiscal_year.fiscal_year import FiscalYearIncorrectDate

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

		self.assertRaises(FiscalYearIncorrectDate, fy.insert)


def test_record_generator():
	test_records = [
		{
			"doctype": "Fiscal Year",
			"year": "_Test Short Fiscal Year 2011",
			"is_short_year": 1,
			"year_end_date": "2011-04-01",
			"year_start_date": "2011-12-31"
		}
	]

	start = 2012
	end = now_datetime().year + 5
	for year in range(start, end):
		test_records.append({
			"doctype": "Fiscal Year",
			"year": "_Test Fiscal Year {}".format(year),
			"year_start_date": "{}-01-01".format(year),
			"year_end_date": "{}-12-31".format(year)
		})

	return test_records

test_records = test_record_generator()
