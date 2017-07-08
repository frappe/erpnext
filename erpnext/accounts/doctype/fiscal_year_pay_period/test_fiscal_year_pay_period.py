# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from six.moves import range

test_records = frappe.get_test_records('Fiscal Year Pay Period')
from frappe.utils import getdate

test_dependencies = ["Fiscal Year", "Company"]


class TestFiscalYearPayPeriod(unittest.TestCase):
	def test_create_fiscal_year_pay_period(self):
		fypp_record = test_records[0]
		# print fypp_record

		if frappe.db.exists('Fiscal Year Pay Period', fypp_record['payroll_period_name']):
			frappe.delete_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])

		fy = frappe.get_doc(fypp_record)
		fy.insert()

		saved_fy = frappe.get_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])
		self.assertEqual(saved_fy.payment_frequency, fypp_record['payment_frequency'])
		self.assertEqual(saved_fy.pay_period_start_date, getdate(fypp_record['pay_period_start_date']))
		self.assertEqual(saved_fy.payroll_period_name, fypp_record['payroll_period_name'])
		self.assertEqual(saved_fy.pay_period_end_date, getdate(fypp_record['pay_period_end_date']))
		for i in range(len(saved_fy.dates)):
			self.assertEqual(
				saved_fy.dates[i].start_date,
				getdate(fypp_record['dates'][i]['start_date'])
			)
			self.assertEqual(
				saved_fy.dates[i].end_date,
				getdate(fypp_record['dates'][i]['end_date'])
			)


# 	def test_create_fiscal_year_with_pay_period(self):
# 		print test_records
# 		if frappe.db.exists("Fiscal Year", "_Test Fiscal Year 2017"):
# 			frappe.delete_doc("Fiscal Year", "_Test Fiscal Year 2017")
#
# 		year_start = "2017-01-07"
# 		year_end = "2018-01-06"
# 		year = "_Test Fiscal Year 2017"
# 		companies = [{
# 					"doctype": 'Fiscal Year Company',
# 					"company": '_Test Company'}]
#
#
# 		fy = frappe.get_doc({
# 			"doctype": "Fiscal Year",
# 			"year_start_date": year_start,
# 			"year": year,
# 			"year_end_date": year_end,
# 			"companies": companies
# 		})
#
# 		overlapping_fy_coy = fix_overlaps_get_initial_coy(fy)
#
# 		fy.insert()
# 		self.assertEquals(fy.year_end_date, year_end)
# 		self.assertEquals(fy.year_start_date, year_start)
# 		self.assertEquals(fy.companies[0].company, companies[0]['company'])
#
# 		saved_fy = frappe.get_doc('Fiscal Year', fy.name)
# 		self.assertEquals(saved_fy.year_end_date, getdate(year_end))
# 		self.assertEquals(saved_fy.year_start_date, getdate(year_start))
# 		self.assertEquals(saved_fy.companies[0].company, companies[0]['company'])
#
# 		# reset things
# 		saved_fy.delete()
# 		if overlapping_fy_coy:
# 			reset_fiscal_year_company(overlapping_fy_coy)
#
#
# def fix_overlaps_get_initial_coy(fiscal_year):
# 	"""
# 	For use when creating a Fiscal Year that would overlap with another Fiscal Year.
# 	Returns the Fiscal Year that was adjusted if available.
#
# 	**This will only work properly if the current fiscal year templates (1 Jan - 31 Dec
# 	with no company set) remains.**
# 	"""
# 	existing_fy = get_existing_fiscal_years(fiscal_year.year_start_date, fiscal_year.year_end_date, fiscal_year.year)
#
# 	company = frappe.db.sql_list(
# 		"""select company from `tabFiscal Year Company`where parent=%s""",
# 		existing_fy[0].name
# 	)
#
# 	overlapping_fiscal_year = None
#
# 	if not company:
# 		# Let's use `_Test Company 1` temporarily
# 		overlapping_fiscal_year = frappe.get_doc('Fiscal Year', existing_fy[0].name)
# 		coy = frappe.get_doc(
# 			{"doctype": 'Fiscal Year Company', "company": "_Test Company 1"}
# 		)
# 		overlapping_fiscal_year.set("companies", [coy])
# 		overlapping_fiscal_year.save()
#
# 	return overlapping_fiscal_year
#
#
# def reset_fiscal_year_company(fiscal_year):
# 	fiscal_year.set("companies", [])
# 	fiscal_year.save()
#
#
#
# def get_existing_fiscal_years(year_start_date, year_end_date, fy_name):
# 	existing_fiscal_years = frappe.db.sql(
# 		"""select name from `tabFiscal Year`
# 			where (
# 				(%(year_start_date)s between year_start_date and year_end_date)
# 				or (%(year_end_date)s between year_start_date and year_end_date)
# 				or (year_start_date between %(year_start_date)s and %(year_end_date)s)
# 				or (year_end_date between %(year_start_date)s and %(year_end_date)s)
# 			) and name!=%(name)s
# 		""",
# 		{
# 			"year_start_date": year_start_date,
# 			"year_end_date": year_end_date,
# 			"name": fy_name or "No Name"
# 		},
# 		as_dict=True)
#
# 	return existing_fiscal_years

