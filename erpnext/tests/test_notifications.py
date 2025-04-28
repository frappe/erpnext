# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
<<<<<<< HEAD
=======


>>>>>>> 7c4cf3e834 (Favicon.svg)
import unittest

import frappe
from frappe.desk import notifications
<<<<<<< HEAD
from frappe.tests import IntegrationTestCase


class TestNotifications(IntegrationTestCase):
=======


class TestNotifications(unittest.TestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	def test_get_notifications_for_targets(self):
		"""
		Test notification config entries for targets as percentages
		"""

		company = frappe.get_all("Company")[0]
		frappe.db.set_value("Company", company.name, "monthly_sales_target", 10000)
		frappe.db.set_value("Company", company.name, "total_monthly_sales", 1000)

		config = notifications.get_notification_config()
		doc_target_percents = notifications.get_notifications_for_targets(config, {})

		self.assertEqual(doc_target_percents["Company"][company.name], 10)

		frappe.db.set_value("Company", company.name, "monthly_sales_target", 2000)
		frappe.db.set_value("Company", company.name, "total_monthly_sales", 0)

		config = notifications.get_notification_config()
		doc_target_percents = notifications.get_notifications_for_targets(config, {})

		self.assertEqual(doc_target_percents["Company"][company.name], 0)
