# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSellingSettings(ERPNextTestSuite):
	def test_defaults_populated(self):
		# Setup default values are not populated on migrate, this test checks
		# if setup was completed correctly
		default = frappe.db.get_single_value("Selling Settings", "maintain_same_rate_action")
		self.assertEqual("Stop", default)

	def test_unchanged_save_keeps_site_cache(self):
		settings = frappe.get_single("Selling Settings")
		settings.customer_group = None
		settings.save()

		frappe.cache.set_value("selling_settings_probe", 1)
		settings.save()

		self.assertEqual(frappe.cache.get_value("selling_settings_probe"), 1)

	def test_boolean_check_value_is_stored_as_1(self):
		settings = frappe.get_single("Selling Settings")
		settings.editable_price_list_rate = True
		settings.save()

		self.assertEqual(frappe.db.get_default("editable_price_list_rate"), "1")
