# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import unittest

from frappe.desk import notifications
from frappe.test_runner import make_test_objects

class TestNotifications(unittest.TestCase):
	def setUp(self):
		test_records_company = [
			{
				"abbr": "_TC6",
				"company_name": "_Test Company 6",
				"country": "India",
				"default_currency": "INR",
				"doctype": "Company",
				"domain": "Manufacturing",
				"monthly_sales_target": 2000,
				"chart_of_accounts": "Standard"
			},
			{
				"abbr": "_TC7",
				"company_name": "_Test Company 7",
				"country": "United States",
				"default_currency": "USD",
				"doctype": "Company",
				"domain": "Retail",
				"monthly_sales_target": 10000,
				"total_monthly_sales": 1000,
				"chart_of_accounts": "Standard"
			},
		]

		test_records_customer = [
			{
				"customer_group": "All Customer Groups",
				"customer_name": "_Test Customer 20",
				"customer_type": "Individual",
				"doctype": "Customer",
				"territory": "All Territories"
			},
			{
				"customer_group": "All Customer Groups",
				"customer_name": "_Test Customer 21",
				"customer_type": "Individual",
				"doctype": "Customer",
				"territory": "All Territories"
			}
		]

		make_test_objects('Company', test_records=test_records_company, reset=True)
		make_test_objects('Customer', test_records=test_records_customer, reset=True)

	def test_get_notifications_for_targets(self):
		'''
			Test notification config entries for targets as percentages
		'''

		config = notifications.get_notification_config()
		doc_target_percents = notifications.get_notifications_for_targets(config, {})
		self.assertEquals(doc_target_percents['Company']['_Test Company 7'], 10)
		self.assertEquals(doc_target_percents['Company']['_Test Company 6'], 0)

	def test_get_user_progress_status(self):
		'''
			Test user progress status
		'''
		config = notifications.get_notification_config()
		user_progress_status = notifications.get_user_progress_status(config)
		self.assertEquals(user_progress_status['Company'], 1)
		self.assertEquals(user_progress_status['Customers'], 1)

