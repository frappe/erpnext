# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestBuyingSettings(ERPNextTestSuite):
	def test_unrelated_change_does_not_update_supplier_metadata(self):
		settings = frappe.get_single("Buying Settings")
		settings.allow_multiple_items = not settings.allow_multiple_items

		with patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series:
			settings.save()

		set_by_naming_series.assert_not_called()

	def test_supplier_metadata_updates_when_related_settings_change(self):
		settings = frappe.get_single("Buying Settings")
		settings.supp_master_name = (
			"Supplier Name" if settings.supp_master_name == "Naming Series" else "Naming Series"
		)

		with patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series:
			settings.save()

		set_by_naming_series.assert_called_once()
