# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestBuyingSettings(ERPNextTestSuite):
	def test_unchanged_save_keeps_site_cache(self):
		settings = frappe.get_single("Buying Settings")
		settings.supplier_group = None
		settings.save()

		frappe.cache.set_value("buying_settings_probe", 1)
		settings.save()

		self.assertEqual(frappe.cache.get_value("buying_settings_probe"), 1)
