# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from six.moves import range
from erpnext.accounts.doctype.fiscal_year_pay_period.fiscal_year_pay_period import get_pay_period_dates, \
	dates_interval_valid, _validate_payment_frequency, _validate_dates

test_records = frappe.get_test_records('Fiscal Year Pay Period')
from frappe.utils import getdate

test_dependencies = ["Fiscal Year", "Company"]


class TestFiscalYearPayPeriod(unittest.TestCase):
	def test_create_fiscal_year_pay_period(self):
		fypp_record = test_records[0]

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

	def test_create_fiscal_year_pay_period_bad_dates(self):
		fypp_record = test_records[4]

		if frappe.db.exists('Fiscal Year Pay Period', fypp_record['payroll_period_name']):
			frappe.delete_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])

		if frappe.db.exists('Fiscal Year Pay Period', '_Test 1 Monthly'):
			frappe.delete_doc('Fiscal Year Pay Period', '_Test 1 Monthly')

		fy = frappe.get_doc(fypp_record)
		fy.pay_period_start_date = '2017-01-07'
		fy.pay_period_end_date = '2017-01-01'
		self.assertRaises(frappe.ValidationError, fy.insert)

		fy.pay_period_start_date = '2017-01-01'
		fy.pay_period_end_date = '2017-12-01'
		fy.payment_frequency = 'Monthly'
		fy.payroll_period_name = '_Test 1 Monthly'
		self.assertRaises(frappe.ValidationError, fy.insert)

		fy.pay_period_end_date = '2017-12-31'
		fy.insert()

	def test_create_fiscal_year_pay_period_wrong_dates_monthly(self):
		fypp_record = test_records[1]

		if frappe.db.exists('Fiscal Year Pay Period', fypp_record['payroll_period_name']):
			frappe.delete_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])

		fy = frappe.get_doc(fypp_record)
		fy.pay_period_start_date = '2017-01-01'
		fy.pay_period_end_date = '2017-12-01'
		self.assertRaises(frappe.ValidationError, fy.insert)

	def test_create_fiscal_year_pay_period_wrong_dates_fortnightly(self):
		fypp_record = test_records[2]

		if frappe.db.exists('Fiscal Year Pay Period', fypp_record['payroll_period_name']):
			frappe.delete_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])

		fy = frappe.get_doc(fypp_record)
		fy.pay_period_end_date = '2017-01-31'
		self.assertRaises(frappe.ValidationError, fy.insert)

	def test_create_fiscal_year_pay_period_wrong_dates_weekly(self):
		fypp_record = test_records[3]

		if frappe.db.exists('Fiscal Year Pay Period', fypp_record['payroll_period_name']):
			frappe.delete_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])

		fy = frappe.get_doc(fypp_record)
		fy.pay_period_end_date = '2017-01-06'
		self.assertRaises(frappe.ValidationError, fy.insert)

	def test_fypp_payment_frequency(self):
		fypp_record = test_records[0]

		if frappe.db.exists('Fiscal Year Pay Period', fypp_record['payroll_period_name']):
			frappe.delete_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])

		fy = frappe.get_doc(fypp_record)
		fy.payment_frequency = 'Fail'
		self.assertRaises(frappe.ValidationError, fy.insert)

		fy.payment_frequency = 'Monthly'
		fy.insert()

		saved_fy = frappe.get_doc('Fiscal Year Pay Period', fypp_record['payroll_period_name'])
		self.assertEqual(saved_fy.payment_frequency, fy.payment_frequency)

	def test_get_pay_period_dates_daily(self):
		pay_periods1 = [
			{'start_date': '2017-07-03', 'end_date': '2017-07-03'},
			{'start_date': '2017-07-04', 'end_date': '2017-07-04'},
			{'start_date': '2017-07-05', 'end_date': '2017-07-05'},
			{'start_date': '2017-07-06', 'end_date': '2017-07-06'},
			{'start_date': '2017-07-07', 'end_date': '2017-07-07'},
			{'start_date': '2017-07-08', 'end_date': '2017-07-08'},
			{'start_date': '2017-07-09', 'end_date': '2017-07-09'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-07-03', '2017-07-09', 'Daily'),
			pay_periods1
		)

	def test_get_pay_period_dates_bimonthly(self):
		pay_periods1 = [
			{'start_date': '2017-01-01', 'end_date': '2017-02-28'},
			{'start_date': '2017-03-01', 'end_date': '2017-04-30'},
			{'start_date': '2017-05-01', 'end_date': '2017-06-30'},
			{'start_date': '2017-07-01', 'end_date': '2017-08-31'},
			{'start_date': '2017-09-01', 'end_date': '2017-10-31'},
			{'start_date': '2017-11-01', 'end_date': '2017-12-31'}
		]

		self.assertEqual(
			get_pay_period_dates('2017-01-01', '2017-12-31', 'Bimonthly'),
			pay_periods1
		)

	def test_get_pay_period_dates_weekly(self):
		pay_periods1 = [
			{'start_date': '2017-07-03', 'end_date': '2017-07-09'},
			{'start_date': '2017-07-10', 'end_date': '2017-07-16'},
			{'start_date': '2017-07-17', 'end_date': '2017-07-23'},
			{'start_date': '2017-07-24', 'end_date': '2017-07-30'},
			{'start_date': '2017-07-31', 'end_date': '2017-08-06'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-07-03', '2017-08-06', 'Weekly'),
			pay_periods1
		)

	def test_get_pay_period_dates_fortnightly(self):
		pay_periods1 = [
			{'start_date': '2017-01-01', 'end_date': '2017-01-14'},
			{'start_date': '2017-01-15', 'end_date': '2017-01-28'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-01-01', '2017-01-28', 'Fortnightly'),
			pay_periods1
		)

		pay_periods2 = [
			{'start_date': '2017-01-01', 'end_date': '2017-01-14'},
			{'start_date': '2017-01-15', 'end_date': '2017-01-28'},
			{'start_date': '2017-01-29', 'end_date': '2017-02-11'},
			{'start_date': '2017-02-12', 'end_date': '2017-02-25'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-01-01', '2017-02-25', 'Fortnightly'),
			pay_periods2
		)

	def test_get_pay_period_dates_monthly(self):
		pay_periods1 = [
			{'start_date': '2017-01-01', 'end_date': '2017-01-31'},
			{'start_date': '2017-02-01', 'end_date': '2017-02-28'},
			{'start_date': '2017-03-01', 'end_date': '2017-03-31'},
			{'start_date': '2017-04-01', 'end_date': '2017-04-30'},
			{'start_date': '2017-05-01', 'end_date': '2017-05-31'},
			{'start_date': '2017-06-01', 'end_date': '2017-06-30'},
			{'start_date': '2017-07-01', 'end_date': '2017-07-31'},
			{'start_date': '2017-08-01', 'end_date': '2017-08-31'},
			{'start_date': '2017-09-01', 'end_date': '2017-09-30'},
			{'start_date': '2017-10-01', 'end_date': '2017-10-31'},
			{'start_date': '2017-11-01', 'end_date': '2017-11-30'},
			{'start_date': '2017-12-01', 'end_date': '2017-12-31'}
		]
		self.assertEqual(
			get_pay_period_dates('2017-01-01', '2017-12-31', 'Monthly'),
			pay_periods1
		)

		pay_periods2 = [
			{'start_date': '2017-01-07', 'end_date': '2017-02-06'},
			{'start_date': '2017-02-07', 'end_date': '2017-03-06'},
			{'start_date': '2017-03-07', 'end_date': '2017-04-06'},
			{'start_date': '2017-04-07', 'end_date': '2017-05-06'},
			{'start_date': '2017-05-07', 'end_date': '2017-06-06'},
			{'start_date': '2017-06-07', 'end_date': '2017-07-06'},
			{'start_date': '2017-07-07', 'end_date': '2017-08-06'},
			{'start_date': '2017-08-07', 'end_date': '2017-09-06'},
			{'start_date': '2017-09-07', 'end_date': '2017-10-06'},
			{'start_date': '2017-10-07', 'end_date': '2017-11-06'},
			{'start_date': '2017-11-07', 'end_date': '2017-12-06'},
			{'start_date': '2017-12-07', 'end_date': '2018-01-06'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-01-07', '2018-01-06', 'Monthly'),
			pay_periods2
		)

		pay_periods3 = [
			{'start_date': '2017-01-07', 'end_date': '2017-02-06'},
			{'start_date': '2017-02-07', 'end_date': '2017-03-06'},
			{'start_date': '2017-03-07', 'end_date': '2017-04-06'},
			{'start_date': '2017-04-07', 'end_date': '2017-05-06'},
			{'start_date': '2017-05-07', 'end_date': '2017-06-06'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-01-07', '2017-06-06', 'Monthly'),
			pay_periods3
		)

		self.assertRaises(frappe.ValidationError, get_pay_period_dates, '2017-01-07', '2017-06-11', 'Monthly')
		self.assertRaises(frappe.ValidationError, get_pay_period_dates, '2017-01-07', '2018-01-01', 'Monthly')

	def test_get_pay_period_dates_irregular_date(self):
		pay_periods = [
			{'start_date': '2017-01-07', 'end_date': '2017-02-06'},
			{'start_date': '2017-02-07', 'end_date': '2017-03-06'},
			{'start_date': '2017-03-07', 'end_date': '2017-04-06'},
			{'start_date': '2017-04-07', 'end_date': '2017-05-06'},
			{'start_date': '2017-05-07', 'end_date': '2017-06-06'},
		]

		self.assertEqual(
			get_pay_period_dates('2017-01-07', '2017-06-06', 'Monthly'),
			pay_periods
		)

		self.assertRaises(frappe.ValidationError, get_pay_period_dates, '2017-01-07', '2017-06-11', 'Monthly')

	def test_date_is_regular(self):
		self.assertTrue(dates_interval_valid(getdate('2017-01-01'), getdate('2017-01-14'), 'Fortnightly'))
		self.assertFalse(dates_interval_valid(getdate('2017-01-01'),getdate('2017-01-15'), 'Fortnightly'))
		self.assertTrue(dates_interval_valid(getdate('2017-01-07'), getdate('2017-02-06'), 'Monthly'))
		self.assertFalse(dates_interval_valid(getdate('2017-01-07'), getdate('2017-02-15'), 'Monthly'))
		self.assertTrue(dates_interval_valid(getdate('2017-01-07'), getdate('2017-03-06'), 'Bimonthly'))
		self.assertFalse(dates_interval_valid(getdate('2017-01-07'), getdate('2017-02-15'), 'Bimonthly'))
		self.assertFalse(dates_interval_valid(getdate('2017-01-07'), getdate('2017-03-15'), 'Bimonthly'))
		self.assertTrue(dates_interval_valid(getdate('2017-01-07'), getdate('2017-01-13'), 'Weekly'))
		self.assertFalse(dates_interval_valid(getdate('2017-01-07'), getdate('2017-01-22'), 'Weekly'))
		self.assertTrue(dates_interval_valid(getdate('2017-03-06'), getdate('2017-03-06'), 'Daily'))
		self.assertTrue(dates_interval_valid(getdate('2017-03-06'), getdate('2017-03-07'), 'Daily'))

	def test_validate_payment_frequency(self):
		self.assertRaises(frappe.ValidationError, _validate_payment_frequency, 'fail')

	def test_validate_dates(self):
		self.assertRaises(frappe.ValidationError, _validate_dates, '2017-12-01', '2017-01-01')
		self.assertRaises(frappe.ValidationError, _validate_dates, '2018-01-01', '2017-12-31')
		self.assertEqual(_validate_dates('2017-12-01', '2017-12-01'), None)
		self.assertEqual(_validate_dates('2017-01-01', '2017-12-01'), None)

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

