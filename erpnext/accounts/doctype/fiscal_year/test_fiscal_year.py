# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, unittest
from frappe.utils import getdate

test_records = frappe.get_test_records('Fiscal Year')
test_ignore = ["Company"]
test_dependencies = ["Pay Period"]


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
		self.assertEquals(fy.year_end_date, '2001-03-31')

	def test_create_fiscal_year_with_pay_period(self):
		if frappe.db.exists("Fiscal Year", "_Test Fiscal Year 1907"):
			frappe.delete_doc("Fiscal Year", "_Test Fiscal Year 1907")

		year_start = "1907-01-07"
		year_end = "1908-01-06"
		year = "_Test Fiscal Year 1907"
		companies = [{
					"doctype": 'Fiscal Year Company',
					"company": '_Test Company'}]
		pay_periods = [
			{"doctype": "Fiscal Year Pay Period",
			 "pay_period": "_Test 1907 - Monthly"
			 }]


		fy = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year_start_date": year_start,
			"year": year,
			"year_end_date": year_end,
			"companies": companies,
			"pay_periods": pay_periods
		})

		fy.insert()
		self.assertEquals(fy.year_end_date, year_end)
		self.assertEquals(fy.year_start_date, year_start)
		self.assertEquals(fy.companies[0].company, companies[0]['company'])

		saved_fy = frappe.get_doc('Fiscal Year', fy.name)
		self.assertEquals(saved_fy.year_end_date, getdate(year_end))
		self.assertEquals(saved_fy.year_start_date, getdate(year_start))
		self.assertEquals(saved_fy.companies[0].company, companies[0]['company'])
		self.assertEquals(saved_fy.pay_periods[0].pay_period, pay_periods[0]['pay_period'])

	def test_create_fiscal_year_no_pay_period(self):
		if frappe.db.exists("Fiscal Year", "_Test Fiscal Year 1907"):
			frappe.delete_doc("Fiscal Year", "_Test Fiscal Year 1907")

		year_start = "1907-01-07"
		year_end = "1908-01-06"
		year = "_Test Fiscal Year 1907"
		companies = [{
					"doctype": 'Fiscal Year Company',
					"company": '_Test Company'}]


		fy = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year_start_date": year_start,
			"year": year,
			"year_end_date": year_end,
			"companies": companies,
		})

		fy.insert()
		self.assertEquals(fy.year_end_date, year_end)
		self.assertEquals(fy.year_start_date, year_start)
		self.assertEquals(fy.companies[0].company, companies[0]['company'])

		saved_fy = frappe.get_doc('Fiscal Year', fy.name)
		self.assertEquals(saved_fy.year_end_date, getdate(year_end))
		self.assertEquals(saved_fy.year_start_date, getdate(year_start))
		self.assertEquals(saved_fy.companies[0].company, companies[0]['company'])
