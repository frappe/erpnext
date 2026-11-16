# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBuyingSettings(FrappeTestCase):
	def test_unchanged_save_keeps_site_cache(self):
		settings = frappe.get_single("Buying Settings")
		settings.supplier_group = None
		settings.save()

		frappe.cache.set_value("buying_settings_probe", 1)
		settings.save()

		self.assertEqual(frappe.cache.get_value("buying_settings_probe"), 1)
